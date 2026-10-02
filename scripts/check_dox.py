"""
Kontrola spójności kaskady DOX — cztery klasy usterek, które w audycie 2026-08-27
znalazły się w repo jednocześnie i żadna nie dała o sobie znać sama.

Uruchamiaj ręcznie oraz w rutynie `cleanup`:

    uv run python scripts/check_dox.py

Kod wyjścia 1, gdy jest choć jeden ERROR. WARN-y nie przewracają przebiegu — opisują stan
świadomie zostawiony (dziś: duplikat frameworka DOX między repo a katalogiem rodzica,
przedmiot otwartej decyzji).
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Kolejność wymagana przez framework DOX (rodzic `00_aid4u/AGENTS.md`, sekcja Child Doc
# Shape). Nie każdy plik musi mieć komplet — liczy się, żeby obecne szły we właściwej
# kolejności i żeby korzenie poddrzew miały Purpose.
DOX_SECTIONS = [
    "Purpose",
    "Ownership",
    "Local Contracts",
    "Work Guidance",
    "Verification",
    "Child DOX Index",
]

# `AGENTS.md` per epizod opisują pułapki jednego zadania, nie granicę architektoniczną —
# wymuszanie na nich pełnego szkieletu dałoby pięć pustych nagłówków na plik.
SECTION_EXEMPT = re.compile(r"^tasks/s\d\de\d\d_|^tasks/s\d\d/|^\.issues/")

# Ścieżki wymieniane w dokumentacji jako przykłady/wzorce, nie jako istniejące pliki.
PATH_PLACEHOLDER = re.compile(r"[<>{}*?]|sXXeYY|s\d\deXX|\bsXX\b|XXXX|RRRR|\bNN\b|…|\.\.\.")

# Tokeny ze slashem, które slashem nie oznaczają katalogu: hosty, wywołania w kodzie,
# nazwy gałęzi gita i identyfikatory modeli (`dostawca/model`).
NOT_A_PATH = re.compile(
    r"""["'()]|^[\w.-]+\.(com|org|dev|app|io|pl)(/|$)"""
    r"""|^(feat|fix|chore|docs|refactor|build|test)/"""
    r"""|^(google|openai|anthropic|meta-llama|deepseek|x-ai|qwen|mistralai)/"""
    r"""|^(type|area|src|gate)/"""  # etykiety Linear, nie katalogi
    r"""|^[A-Z]"""  # `Strategy/Adapter`, `Args:/Returns:` — nazwy własne
)

# Zdanie, które MÓWI, że czegoś nie ma, siłą rzeczy podaje nieistniejącą ścieżkę. Bez tego
# wyjątku każde uczciwe „ten plik nigdy nie powstał" produkowałoby własny błąd.
DELIBERATE_ABSENCE = re.compile(
    r"nie istnie|nie ma pliku|nigdy nie powsta|nie powsta|kiedyś powstanie|usunięt|"
    r"przeniesion|removed|no longer exists|there is no|nie jest zainstalowan|"
    r"nie są zainstalowan|brak w |martw",
    re.I,
)

# Artefakty czasu wykonania — istnieją tylko w trakcie przebiegu, poza gitem.
RUNTIME_PATHS = (".run/", ".cache/", ".claude/state/")

# Minimalna długość bloku uznawanego za duplikat treści, w liniach.
DUPLICATE_BLOCK_LINES = 20

# Duplikat świadomie zostawiony do rozstrzygnięcia — raportowany jako WARN, nie ERROR.
KNOWN_DUPLICATES = {("../AGENTS.md", "AGENTS.md")}


@dataclass
class Finding:
    """Pojedyncze znalezisko: `severity` decyduje o kodzie wyjścia, reszta o czytelności."""

    severity: str
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.severity:5} {self.where}: {self.message}"


def contract_files() -> list[Path]:
    """Pliki objęte kontrolą: cała kaskada `AGENTS.md` w repo plus dokumenty `strategy/`."""
    # `CLAUDE.md` to wszędzie dowiązanie do siostrzanego `AGENTS.md` — czytane dwa razy
    # dałoby każdy finding podwójnie i fałszywy „duplikat bloku".
    agents = sorted(
        p for p in REPO.rglob("AGENTS.md") if ".venv" not in p.parts and not p.is_symlink()
    )
    strategy = sorted(p for p in (REPO / "strategy").rglob("*.md") if not p.is_symlink())
    return agents + [p for p in strategy if p not in agents]


def rel(path: Path) -> str:
    """Ścieżka względem korzenia repo — czytelna w raporcie i stabilna między maszynami."""
    path = path.resolve()
    for base, prefix in ((REPO, ""), (REPO.parent, "../")):
        try:
            return prefix + str(path.relative_to(base))
        except ValueError:
            continue
    return str(path)


def check_paths(files: list[Path]) -> list[Finding]:
    """
    Każda ścieżka względna w backtikach musi istnieć.

    Rozstrzygana kolejno względem katalogu dokumentu, każdego katalogu wyżej i korzenia
    repo — repo używa wszystkich trzech konwencji naraz i każda jest czytelna dla
    człowieka, więc kontrola nie ma prawa wymuszać jednej.

    Świadomie POZA zakresem: tokeny zaczynające się od `/` (to endpointy HTTP i ścieżki na
    zdalnych maszynach, nie pliki repo) oraz gołe nazwy plików bez katalogu — `__init__.py`
    czy `food4cities.json` bez ścieżki nie wskazują jednego miejsca i sprawdzanie ich dawało
    wyłącznie fałszywe alarmy.
    """
    findings: list[Finding] = []
    pattern = re.compile(r"`([^`\n]+)`")
    for f in files:
        roots = [
            f.parent,
            *[p for p in f.parents if REPO in p.parents or p == REPO],
            REPO,
            REPO.parent,
        ]
        lines = f.read_text().splitlines()
        for lineno, line in enumerate(lines, 1):
            # Okno ±1 linii: zdanie „ten plik nigdy nie powstał" bywa złamane po ścieżce.
            if any(DELIBERATE_ABSENCE.search(x) for x in lines[max(0, lineno - 2) : lineno + 1]):
                continue
            for raw in pattern.findall(line):
                token = raw.strip()
                if token.startswith(RUNTIME_PATHS):
                    continue
                if "/" not in token.rstrip("/"):
                    continue
                if token.startswith(("/", "http", "@", "~")) or " " in token:
                    continue
                if PATH_PLACEHOLDER.search(token) or NOT_A_PATH.search(token):
                    continue
                # `core/hub/cache.py:45-65` wskazuje plik plus zakres linii — sprawdzamy plik.
                # `plik.py:45-65` i `plik.py::TestKlasa` wskazują plik plus miejsce w nim.
                token = re.sub(r"(::.*|:\d+([,-]\d+)*)$", "", token).rstrip("/")
                if any((root / token).exists() for root in roots):
                    continue
                findings.append(
                    Finding("ERROR", f"{rel(f)}:{lineno}", f"ścieżka nie istnieje: `{raw}`")
                )
    return findings


def check_index(files: list[Path]) -> list[Finding]:
    """
    Child DOX Index musi zgadzać się z dyskiem **w obie strony**: każdy wpis wskazuje coś,
    co istnieje, i każdy podkatalog z własnym `AGENTS.md` jest wymieniony. Druga strona
    jest ważniejsza — to ona wyłapuje katalogi, o których agent nigdy się nie dowie.
    """
    findings: list[Finding] = []
    for f in files:
        if f.name != "AGENTS.md":
            continue
        text = f.read_text()
        if "## Child DOX Index" not in text:
            continue
        index = text.split("## Child DOX Index", 1)[1]
        listed = {m.strip("/").removeprefix("./") for m in re.findall(r"`([^`\n]+?)/?`", index)}
        for child in sorted(f.parent.iterdir()):
            if not child.is_dir() or child.name.startswith((".", "__")):
                continue
            if not (child / "AGENTS.md").exists():
                continue
            if child.name not in listed:
                findings.append(
                    Finding(
                        "ERROR",
                        rel(f),
                        f"Child DOX Index pomija `{child.name}/`, które ma własny AGENTS.md",
                    )
                )
    return findings


def check_sections(files: list[Path]) -> list[Finding]:
    """Obecne sekcje DOX muszą iść w kolejności ze wzorca; brak sekcji nie jest błędem."""
    findings: list[Finding] = []
    for f in files:
        if f.name != "AGENTS.md" or SECTION_EXEMPT.match(rel(f)):
            continue
        headings = [h.strip() for h in re.findall(r"^## (.+)$", f.read_text(), re.M)]
        present = [h for h in headings if h in DOX_SECTIONS]
        order = [DOX_SECTIONS.index(h) for h in present]
        if order != sorted(order):
            findings.append(Finding("ERROR", rel(f), f"sekcje DOX w złej kolejności: {present}"))
        if "Purpose" not in headings:
            findings.append(Finding("ERROR", rel(f), "brak sekcji `## Purpose`"))
    return findings


def check_duplicates(files: list[Path]) -> list[Finding]:
    """
    Żadne dwa pliki kontraktowe nie powtarzają bloku ≥20 linii. Duplikat znaczy, że jedna
    kopia będzie aktualizowana, a druga po cichu zacznie kłamać — i nie ma jak zgadnąć,
    która jest prawdziwa.
    """
    findings: list[Finding] = []
    scope = files + [REPO.parent / "AGENTS.md"]
    blocks: dict[str, list[str]] = defaultdict(list)
    for f in scope:
        if not f.exists():
            continue
        lines = [ln.strip() for ln in f.read_text().splitlines()]
        substantive = [i for i, ln in enumerate(lines) if ln]
        for start in range(len(substantive) - DUPLICATE_BLOCK_LINES + 1):
            window = substantive[start : start + DUPLICATE_BLOCK_LINES]
            blocks["\n".join(lines[i] for i in window)].append(rel(f))
    seen: set[tuple[str, str]] = set()
    for owners in blocks.values():
        uniq = sorted(set(owners))
        if len(uniq) < 2:
            continue
        pair = (uniq[0], uniq[1])
        if pair in seen:
            continue
        seen.add(pair)
        severity = "WARN" if pair in KNOWN_DUPLICATES else "ERROR"
        note = " (znany, czeka na decyzję)" if severity == "WARN" else ""
        findings.append(
            Finding(
                severity,
                pair[0],
                f"blok ≥{DUPLICATE_BLOCK_LINES} linii powtórzony w {pair[1]}{note}",
            )
        )
    return findings


def main() -> int:
    """Uruchamia cztery kontrole, drukuje findingi i zwraca 1, jeśli jest choć jeden ERROR."""
    files = contract_files()
    findings = (
        check_paths(files) + check_index(files) + check_sections(files) + check_duplicates(files)
    )
    for f in sorted(findings, key=lambda x: (x.severity, x.where)):
        print(f)
    errors = sum(1 for f in findings if f.severity == "ERROR")
    warns = len(findings) - errors
    print(f"\n{len(files)} plików kontraktowych · {errors} ERROR · {warns} WARN")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
