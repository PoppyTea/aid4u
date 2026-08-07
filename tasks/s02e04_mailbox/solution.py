"""
S02E04 — mailbox

Przeszukuje żywą skrzynkę mailową operatora przez API zmail (task="mailbox"), szukając
maila od informatora "Wiktora" (proton.me) i wyciągając trzy wartości: date, password,
confirmation_code (format SEC- + 32 znaki = 36 znaków łącznie).

Protokół zmail jest odkrywany na żywo przez agenta (akcja "help"), nie zahardkodowany —
patrz `doc/community_notes.md` dla akcji potwierdzonych przez społeczność kursu (help,
getInbox, search) jako punkt startowy, nie jako gwarancja.

Architektura: `LLMClient.run_agent_loop()` (ten sam mechanizm co `s01e02_findhim`) z dwoma
generycznymi narzędziami (`zmail_action` — dowolne wywołanie API, `submit_answer` — wysyłka
do huba) i jednym narzędziem do świadomego czekania (`wait_seconds`) na potrzeby żywej,
mutowalnej skrzynki. Limity (throttle, budżet oczekiwania, twardy limit iteracji) są
wymuszone w kodzie `tool_executor`, nie zostawione decyzji modelu — zapobiega to zarówno
młóceniu żywego API, jak i nieskończonej/kosztownej pętli.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable

import httpx

from core.hub import HubClient
from core.llm import LLMClient, LLMMessage
from core.llm.types import Tool
from core.tasks import BaseTask, task
from tasks.s02e04_mailbox.prompts import SYSTEM_AGENT_MAILBOX, USER_AGENT_MAILBOX_KICKOFF

ZMAIL_API_PATH = "/api/zmail"
HUB_TASK_NAME = "mailbox"

_MAX_ITERATIONS = 25
_ZMAIL_MIN_INTERVAL_S = 1.0
_WAIT_MIN_S = 5
_WAIT_MAX_S = 60
_WAIT_BUDGET_TOTAL_S = 300.0

_CONFIRMATION_CODE_PREFIX = "SEC-"
_CONFIRMATION_CODE_LENGTH = 36


# ─── Narzędzia — definicje dla LLMClient.run_agent_loop ──────────────────────

ZMAIL_ACTION_TOOL = Tool(
    name="zmail_action",
    description=(
        "Wywołuje dowolną akcję API zmail (POST /api/zmail). ZAWSZE zacznij od "
        "action='help', żeby poznać dostępne akcje i ich parametry — protokół nie jest "
        "tu z góry znany. `params` to płaski słownik parametrów danej akcji (np. "
        "{'query': 'from:proton.me'} dla wyszukiwania, {'id': '...'} dla odczytu "
        "pojedynczej wiadomości)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Nazwa akcji zmail odkryta przez help, np. 'help', 'getInbox', 'search'.",
            },
            "params": {
                "type": "object",
                "description": "Dodatkowe parametry akcji. Puste {} jeśli akcja ich nie wymaga.",
                "additionalProperties": True,
            },
        },
        "required": ["action"],
    },
)

SUBMIT_ANSWER_TOOL = Tool(
    name="submit_answer",
    description=(
        "Wysyła znalezione wartości do huba (POST /verify, task='mailbox'). Wywołuj gdy "
        "masz choć jedną wartość — hub odpowie czy WSZYSTKIE trzy są poprawne naraz "
        "(wtedy dostajesz flagę) czy trzeba szukać dalej. Dla wartości, których jeszcze "
        "nie znalazłeś, użyj pustego stringa — nie zgaduj."
    ),
    parameters={
        "type": "object",
        "properties": {
            "password": {"type": "string", "description": "Hasło do systemu pracowniczego."},
            "date": {"type": "string", "description": "Data planowanego ataku, format YYYY-MM-DD."},
            "confirmation_code": {
                "type": "string",
                "description": "Kod potwierdzenia: prefiks SEC- + 32 znaki = 36 znaków łącznie.",
            },
        },
        "required": ["password", "date", "confirmation_code"],
    },
)

WAIT_TOOL = Tool(
    name="wait_seconds",
    description=(
        f"Czeka podaną liczbę sekund ({_WAIT_MIN_S}-{_WAIT_MAX_S}, poza zakresem zostanie "
        "przycięte) zanim spróbujesz ponownie — skrzynka jest aktywna, nowe wiadomości mogą "
        "wpłynąć w trakcie pracy. Użyj gdy przeszukałeś dostępne wiadomości a czegoś nadal "
        f"brakuje. Łączny budżet oczekiwania na to uruchomienie jest ograniczony do "
        f"{int(_WAIT_BUDGET_TOTAL_S)}s — po wyczerpaniu narzędzie przestanie czekać."
    ),
    parameters={
        "type": "object",
        "properties": {
            "seconds": {
                "type": "integer",
                "description": f"Ile sekund czekać ({_WAIT_MIN_S}-{_WAIT_MAX_S}).",
            },
        },
        "required": ["seconds"],
    },
)

MAILBOX_TOOLS = [ZMAIL_ACTION_TOOL, SUBMIT_ANSWER_TOOL, WAIT_TOOL]


def _is_valid_confirmation_code(code: str) -> bool:
    """Sprawdza format kodu (SEC- + 32 znaki = 36 łącznie) bez wywołania sieciowego."""
    return code.startswith(_CONFIRMATION_CODE_PREFIX) and len(code) == _CONFIRMATION_CODE_LENGTH


def build_tool_executor(
    hub: HubClient, *, dry_run: bool
) -> tuple[Callable[[str, dict[str, Any]], str], dict[str, Any]]:
    """
    Zamyka `hub`/`dry_run` w closure i trzyma mutowalny stan między wywołaniami narzędzi
    w jednej pętli agentowej:
    - `last_submission` — ostatnie argumenty przekazane do submit_answer, żeby solve()
      miało co zwrócić jako fallback dla automatycznego finalnego submit w BaseTask.run().
    - `flag` — flaga złapana przez submit_answer wewnątrz pętli, jeśli się udało wcześniej.

    Throttle na zmail_action i budżet wait_seconds są WYMUSZONE tutaj w kodzie, nie zależą
    od tego czy model "zdecyduje się" grzecznie czekać — zapobiega to młóceniu żywego API
    (post_api() w HubClient, w odróżnieniu od submit(), nie ma dziś żadnej wbudowanej
    odporności/throttlingu na 429) niezależnie od zachowania modelu.
    """
    state: dict[str, Any] = {"last_submission": None, "flag": None}
    last_zmail_call_at = 0.0
    wait_budget_remaining = _WAIT_BUDGET_TOTAL_S

    def zmail_action(action: str, params: dict | None = None) -> str:
        """Throttlowany POST /api/zmail; 4xx wraca jako feedback dla agenta zamiast wyjątku."""
        nonlocal last_zmail_call_at
        elapsed = time.monotonic() - last_zmail_call_at
        if elapsed < _ZMAIL_MIN_INTERVAL_S:
            time.sleep(_ZMAIL_MIN_INTERVAL_S - elapsed)
        last_zmail_call_at = time.monotonic()

        try:
            response = hub.post_api(ZMAIL_API_PATH, {"action": action, **(params or {})})
        except httpx.HTTPStatusError as exc:
            # 4xx z zmail zwykle niesie realny powód (zła akcja/parametr) — pokaż go
            # agentowi zamiast dać mu tylko generyczny "ERROR: Tool execution failed"
            # z run_agent_loop, żeby mógł się poprawić zamiast zgadywać w ciemno.
            if exc.response.status_code >= 500:
                raise
            try:
                body: Any = exc.response.json()
            except ValueError:
                body = exc.response.text
            return json.dumps(
                {"ok": False, "http_status": exc.response.status_code, "error": body},
                ensure_ascii=False,
            )
        return json.dumps(response, ensure_ascii=False)

    def submit_answer(password: str, date: str, confirmation_code: str) -> str:
        """Waliduje kod lokalnie, potem POST /verify (albo dry-run stub); zapisuje flagę do stanu."""
        state["last_submission"] = {
            "password": password,
            "date": date,
            "confirmation_code": confirmation_code,
        }

        if not _is_valid_confirmation_code(confirmation_code):
            return json.dumps(
                {
                    "ok": False,
                    "message": (
                        f"Lokalna walidacja (bez wysyłki do huba): confirmation_code musi "
                        f"zaczynać się od '{_CONFIRMATION_CODE_PREFIX}' i mieć "
                        f"{_CONFIRMATION_CODE_LENGTH} znaków łącznie, masz "
                        f"{len(confirmation_code)}."
                    ),
                },
                ensure_ascii=False,
            )

        if dry_run:
            return json.dumps(
                {"ok": True, "dry_run": True, "would_submit": state["last_submission"]},
                ensure_ascii=False,
            )

        response = hub.submit(HUB_TASK_NAME, state["last_submission"])
        flag = hub.get_flag(response)
        if flag:
            state["flag"] = flag
        return json.dumps(response, ensure_ascii=False)

    def wait_seconds(seconds: int) -> str:
        """Czeka `seconds` (przycięte do zakresu) sekund, odliczając ze skumulowanego budżetu."""
        nonlocal wait_budget_remaining
        clamped = max(_WAIT_MIN_S, min(_WAIT_MAX_S, int(seconds)))
        if clamped > wait_budget_remaining:
            return json.dumps(
                {
                    "ok": False,
                    "message": "Budżet oczekiwania na to uruchomienie jest wyczerpany — kontynuuj bez czekania.",
                },
                ensure_ascii=False,
            )
        time.sleep(clamped)
        wait_budget_remaining -= clamped
        return json.dumps(
            {"ok": True, "waited_s": clamped, "budget_remaining_s": round(wait_budget_remaining, 1)},
            ensure_ascii=False,
        )

    def tool_executor(name: str, args: dict[str, Any]) -> str:
        """Dispatcher przekazywany do LLMClient.run_agent_loop — routuje po nazwie narzędzia."""
        if name == "zmail_action":
            return zmail_action(args["action"], args.get("params"))
        if name == "submit_answer":
            return submit_answer(args["password"], args["date"], args["confirmation_code"])
        if name == "wait_seconds":
            return wait_seconds(args["seconds"])
        raise ValueError(f"Unknown tool: {name}")

    return tool_executor, state


# ─── Task ─────────────────────────────────────────────────────────────────────


@task("s02e04", hub_name="mailbox")
class MailboxTask(BaseTask):
    """Agentowe przeszukanie żywej skrzynki zmail — function calling, bez statycznych danych wejściowych."""

    def solve(self, data: Any) -> dict:
        """Uruchamia agenta na żywej skrzynce zmail i zwraca ostatnią próbę submit_answer."""
        executor, state = build_tool_executor(self.hub, dry_run=self.dry_run)
        messages = [LLMMessage.user(USER_AGENT_MAILBOX_KICKOFF)]

        self.llm.run_agent_loop(
            messages,
            MAILBOX_TOOLS,
            executor,
            system=SYSTEM_AGENT_MAILBOX,
            max_iterations=_MAX_ITERATIONS,
        )

        if state["last_submission"] is None:
            raise RuntimeError(
                "Agent nie wywołał ani razu submit_answer w ciągu "
                f"{_MAX_ITERATIONS} iteracji — brak odpowiedzi do wysłania."
            )

        return state["last_submission"]
