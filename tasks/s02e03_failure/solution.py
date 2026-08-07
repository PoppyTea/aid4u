"""
S02E03 — failure

Kompresuje log awarii elektrowni (2137 surowych linii, potwierdzone live
2026-08-07) do wersji <1500 tokenów, iterując z hubem po feedbacku o
brakujących/niejasnych podzespołach.

Pipeline jest w większości deterministyczny — dedup po opisie i filtr
[INFO] robi czysty Python (distill()), nie LLM. Po realnym sprawdzeniu
danych: 2137 linii → 90 unikalnych opisów → 55 nie-INFO (7 podzespołów).
To już mały, gotowy zestaw (~1870 tokenów), więc LLM dostaje go od razu w
całości do samej kompresji opisów — bez potrzeby architektury z osobnym
narzędziem do przeszukiwania logu czy subagentem, jak sugerował pierwotny
plan w AGENTS.md przed zobaczeniem realnych danych.

Nazwa zadania w hubie: failure
"""

from __future__ import annotations

import re

import httpx
import logfire
import tiktoken
from pydantic import BaseModel

from core.llm import LLMClient, LLMMessage
from core.tasks import BaseTask, task
from tasks.s02e03_failure.prompts import SYSTEM_COMPRESS, build_compress_user_prompt

_TARGET_TOKEN_BUDGET = 1400  # margines poniżej twardego limitu huba
_HUB_TOKEN_LIMIT = 1500  # twardy, WYŁĄCZNY limit — 1500/1500 = odrzucenie (potwierdzone live)
_MIN_TOKENS_PER_ENTRY = 6  # nie schodzić poniżej tego nawet przy bardzo małym budżecie
_MAX_VERIFY_ATTEMPTS = 8

_LINE_RE = re.compile(
    r"^\[(?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d{2}:\d{2}):\d{2}\] \[(?P<level>\w+)\] (?P<desc>.*)$"
)
_COMPONENT_RE = re.compile(r"\b[A-Z]{3,}\d*\b")
_SEVERITY = {"CRIT": 3, "ERRO": 2, "WARN": 1, "INFO": 0}
_ENCODING = tiktoken.get_encoding("o200k_base")


# ─── Czyste funkcje (łatwe do testowania jednostkowego) ──────────────────────


def parse_log(raw: bytes) -> list[dict]:
    """Parsuje surowe linie logu do listy {date, time, level, desc}. Linie
    niepasujące do formatu są pomijane (log ostrzeżenie, nie wyjątek — format
    logu nie jest pod naszą kontrolą)."""
    text = raw.decode("utf-8", errors="replace")
    events = []
    skipped = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = _LINE_RE.match(line)
        if not match:
            skipped += 1
            continue
        events.append(match.groupdict())
    if skipped:
        logfire.warning(f"s02e03: pominięto {skipped} linii niepasujących do formatu logu")
    return events


def _components_in(text: str) -> frozenset[str]:
    return frozenset(_COMPONENT_RE.findall(text))


def distill(events: list[dict]) -> list[dict]:
    """
    Dedup po opisie (niezależnie od timestampu) + odrzucenie zdarzeń, których
    najwyższy zaobserwowany poziom to INFO — to szum, nigdy nie jest tym czego
    brakuje wg feedbacku z huba (potwierdzone w doc/community_notes.md).

    Zwraca listę {date, time, level, orig_desc, desc, components, pinned}
    posortowaną chronologicznie. `desc` startuje jako kopia `orig_desc` —
    kompresja LLM nadpisuje tylko `desc`, `orig_desc` zostaje jako fallback do
    przywrócenia pełnej treści, gdy feedback wskaże zgubiony podzespół. Wpisy
    przywrócone tak (`pinned=True`) są potem pomijane przy dalszej kompresji —
    inaczej kolejna runda "skróć wszystko mocniej" cofnęłaby przywrócenie.
    """
    by_desc: dict[str, dict] = {}
    for e in events:
        desc = e["desc"].strip()
        entry = by_desc.get(desc)
        if entry is None:
            by_desc[desc] = {
                "date": e["date"],
                "time": e["time"],
                "level": e["level"],
                "orig_desc": desc,
                "desc": desc,
                "components": _components_in(desc),
                "pinned": False,
            }
        elif _SEVERITY[e["level"]] > _SEVERITY[entry["level"]]:
            entry["level"] = e["level"]

    distilled = [e for e in by_desc.values() if e["level"] != "INFO"]
    distilled.sort(key=lambda e: (e["date"], e["time"]))
    return distilled


def render_line(e: dict) -> str:
    return f"[{e['date']} {e['time']}] [{e['level']}] {e['desc']}"


def render_log(events: list[dict]) -> str:
    return "\n".join(render_line(e) for e in events)


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


# ─── Kompresja opisów przez LLM ───────────────────────────────────────────────


class CompressedEntry(BaseModel):
    index: int
    text: str


class CompressionResponse(BaseModel):
    entries: list[CompressedEntry]


def _compress_via_llm(
    llm: LLMClient, events: list[dict], *, target_tokens_per_entry: int
) -> dict[int, str]:
    """Kompresuje zawsze z `orig_desc` (nie z poprzedniej, już skróconej wersji) —
    ponowna kompresja tekstu który już jest skrócony ma malejące efekty, patrz
    docstring FailureTask._compress_to_budget(). Pomija wpisy `pinned`
    (przywrócone po feedbacku o zgubionym podzespole — nie mają być
    kompresowane ponownie)."""
    payload = [
        {"index": i, "level": e["level"], "text": e["orig_desc"]}
        for i, e in enumerate(events)
        if not e["pinned"]
    ]
    prompt = build_compress_user_prompt(payload, target_tokens_per_entry=target_tokens_per_entry)
    response = llm.structured([LLMMessage.user(prompt)], CompressionResponse, system=SYSTEM_COMPRESS)
    return {entry.index: entry.text.strip() for entry in response.entries if entry.text.strip()}


def _apply_compression(events: list[dict], compressed: dict[int, str]) -> list[dict]:
    """Podmienia `desc` tylko gdy nowy tekst nadal zawiera WSZYSTKIE oryginalne
    identyfikatory podzespołów — inaczej zostawia poprzednią wersję (zapobiega
    najczęstszej przyczynie feedbacku 'unable to determine what happened to
    device X', patrz doc/community_notes.md)."""
    for i, e in enumerate(events):
        if e["pinned"]:
            continue
        new_desc = compressed.get(i)
        if new_desc and e["components"] <= _components_in(new_desc):
            e["desc"] = new_desc
    return events


def _restore_component(events: list[dict], component: str) -> list[dict]:
    """Przywraca pełny oryginalny opis dla wszystkich zdarzeń danego podzespołu
    i chroni je (`pinned`) przed nadpisaniem w kolejnych rundach kompresji."""
    for e in events:
        if component in e["components"]:
            e["desc"] = e["orig_desc"]
            e["pinned"] = True
    return events


def _hard_trim(events: list[dict], total_budget: int) -> list[dict]:
    """Deterministyczne, ostateczne zabezpieczenie budżetu tokenów — tnie
    `desc` na poziomie tokenów tiktoken, gdy kompresja LLM mimo instrukcji
    nie zmieściła się w celu. Nie dotyka wpisów `pinned`. Komponenty zwykle
    stoją na początku zdania (patrz przykłady w doc/community_notes.md), więc
    przycinanie od końca w pierwszej kolejności traci opis skutku, nie
    identyfikator podzespołu."""
    unpinned = [e for e in events if not e["pinned"]]
    if not unpinned:
        return events

    per_line_budget = max(_MIN_TOKENS_PER_ENTRY + 6, total_budget // len(events))
    for e in unpinned:
        prefix = f"[{e['date']} {e['time']}] [{e['level']}] "
        desc_budget = max(3, per_line_budget - count_tokens(prefix))
        desc_tokens = _ENCODING.encode(e["desc"])
        if len(desc_tokens) > desc_budget:
            e["desc"] = _ENCODING.decode(desc_tokens[:desc_budget]).rstrip()
    return events


def _looks_like_token_overflow(message: str) -> bool:
    lowered = message.lower()
    return "token" in lowered or "context window" in lowered


# ─── Task ─────────────────────────────────────────────────────────────────────


@task("s02e03", hub_name="failure")
class FailureTask(BaseTask):
    def fetch_data(self) -> bytes:
        return self.cache.get_or_fetch(
            "failure.log",
            lambda: self.hub.get_data("failure.log"),
        )

    def solve(self, data: bytes) -> dict:
        events = distill(parse_log(data))
        if not events:
            raise ValueError("Brak istotnych zdarzeń po dedup+filtrze [INFO] — sprawdź parser/dane")

        events = self._compress_to_budget(events)
        answer = {"logs": render_log(events)}

        if self.dry_run:
            return answer

        known_components = sorted({c for e in events for c in e["components"]})
        message = ""

        for attempt in range(1, _MAX_VERIFY_ATTEMPTS + 1):
            response = self._verify(answer)
            flag = self.hub.get_flag(response)
            if flag:
                logfire.info(f"s02e03 zaakceptowane po {attempt} próbach")
                return answer

            message = str(response.get("message", ""))
            logfire.info("s02e03 feedback", attempt=attempt, message=message)

            missing = next((c for c in known_components if c in message), None)
            if missing:
                events = _restore_component(events, missing)
            elif _looks_like_token_overflow(message):
                events = self._compress_to_budget(events, force=True)
            else:
                logfire.warning("s02e03: nierozpoznany feedback huba", message=message)

            answer = {"logs": render_log(events)}

        raise RuntimeError(f"s02e03: brak flagi po {_MAX_VERIFY_ATTEMPTS} próbach — ostatni feedback: {message}")

    def _verify(self, answer: dict) -> dict:
        """
        POST /verify dla tego zadania zwraca HTTP 400 (nie 200) gdy odpowiedź
        jest jeszcze niekompletna — to normalny krok iteracji, nie błąd.
        HubClient.submit() rzuca httpx.HTTPStatusError na 400 (raise_for_status),
        więc tu łapiemy go i traktujemy ciało JSON jak zwykłą odpowiedź z
        feedbackiem. Potwierdzone live 2026-08-07: {"code": -960, "message": "..."}.
        """
        try:
            return self.hub.submit(self._hub_task_name, answer)
        except httpx.HTTPStatusError as exc:
            return exc.response.json()

    def _compress_to_budget(self, events: list[dict], *, force: bool = False) -> list[dict]:
        """
        Jedna runda kompresji LLM z jawnym budżetem tokenów/wpis, plus
        deterministyczne przycięcie (`_hard_trim`) jako gwarancja, nie
        sugestia. Empirycznie (2026-08-07, Haiku) nawet 5 kolejnych rund z
        coraz ostrzejszym hasłem "skróć mocniej" zbiegały bardzo wolno
        (~1870 → 1590 → 1511 tokenów, wciąż nad twardym limitem 1500) — LLM
        nie ma wiarygodnej introspekcji co do liczby tokenów własnego
        wyjścia. Nie ma sensu płacić za więcej rund w nadziei na trafienie;
        twarde przycięcie na końcu gwarantuje zgodność z budżetem zawsze.
        """
        text = render_log(events)
        if not force and count_tokens(text) <= _TARGET_TOKEN_BUDGET:
            return events

        unpinned = max(sum(1 for e in events if not e["pinned"]), 1)
        # `force` = hub sam zgłosił przekroczenie mimo że nasz licznik tokenów
        # (o200k_base) mówił co innego — zejdź poniżej budżetu z zapasem na
        # rozjazd tokenizerów, zamiast celować dokładnie w tę samą granicę.
        effective_budget = round(_TARGET_TOKEN_BUDGET * 0.85) if force else _TARGET_TOKEN_BUDGET
        per_entry = max(_MIN_TOKENS_PER_ENTRY, effective_budget // unpinned)

        compressed = _compress_via_llm(self.llm, events, target_tokens_per_entry=per_entry)
        events = _apply_compression(events, compressed)

        tokens = count_tokens(render_log(events))
        if tokens <= effective_budget:
            return events

        logfire.warning(f"s02e03: LLM nie zmieścił się w budżecie ({tokens} tokenów) — twarde przycięcie")
        return _hard_trim(events, effective_budget)
