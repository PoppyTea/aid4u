"""
S03E02 `firmware` — uruchomienie sterownika chłodzenia na zdalnej VM.

**Zero LLM.** Treść zadania i intel społeczności sugerują pętlę agentową, ale po sondzie
`help` okazało się, że przestrzeń problemu jest mała i w pełni deterministyczna: trzy
linie do poprawienia w `settings.ini`, jeden plik blokady do skasowania, jedno hasło
leżące w niezablokowanym pliku. Pętla agentowa dokładałaby koszt i niedeterminizm, żeby
model odkrył to, co już wiadomo — a to właśnie ten epizod ma udokumentowany rozrzut
kosztu ×140 ($0.05 wobec $7.20 za NIEUDANĄ próbę).

Osłony zbudowane przed tym epizodem i tak pracują: każde polecenie idzie przez bramkę
(`shell.py`), `HubClient` dławi ruch na `/api/*`, a błędy API wracają jako opisowy tekst
zamiast wyjątku wywalającego przebieg.

Kształt rozwiązania (ustalony sondą, nie zgadnięty):
1. `settings.ini` ma trzy usterki — zakomentowany `SAFETY_CHECK`, włączony `test_mode`,
   wyłączone chłodzenie.
2. `cooler-is-blocked.lock` blokuje start; binarka sama prosi o jego usunięcie.
3. Hasło (`admin1`) leży w `/home/operator/notes/pass.txt`. Miejsca oczywiste — `.env`,
   `storage.cfg`, `logs/` — są w `.gitignore`, więc ich dotknięcie kończy się banem.
"""

from __future__ import annotations

# ─── Observability jako pierwsze ─────────────────────────────────────────────
from core.observability.setup import setup_observability

setup_observability()

# ─── Właściwe importy po setup obserwabilności ───────────────────────────────
import re

from rich.console import Console

from core.tasks import DRY_RUN_UNSAFE, BaseTask, task
from tasks.s03e02_firmware.shell import BINARY, SETTINGS, ShellTool, remove_lock

_console = Console()

CODE_RE = re.compile(r"ECCS-[0-9a-f]{40}")
PASSWORD_FILE = "/home/operator/notes/pass.txt"

# Docelowa treść linii `settings.ini`, indeksowana od 1 (tak adresuje `editline`).
# Numery są sprawdzane przed zapisem — patrz `_fix_settings()`.
REQUIRED_LINES = {
    2: "SAFETY_CHECK=pass",
    6: "enabled=false",
    10: "enabled=true",
}


def read_password(shell: ShellTool) -> str:
    """Czyta hasło z jedynego miejsca, którego `.gitignore` nie wyklucza."""
    return shell.run(f"cat {PASSWORD_FILE}").strip()


def _fix_settings(shell: ShellTool) -> None:
    """
    Doprowadza `settings.ini` do stanu, w którym binarka wystartuje.

    Każda linia jest najpierw czytana i porównywana, a `editline` wysyłane tylko gdy
    treść się różni. Powód nie jest kosmetyczny: to czyni przebieg **idempotentnym**,
    więc powtórne uruchomienie po częściowej awarii nie nadpisuje poprawnych linii
    i nie zużywa limitu zapytań na nic.
    """
    current = shell.run(f"cat {SETTINGS}").split("\n")
    for number, expected in REQUIRED_LINES.items():
        actual = current[number - 1] if len(current) >= number else None
        if actual == expected:
            _console.print(f"  [dim]linia {number} już poprawna[/]")
            continue
        _console.print(f"  linia {number}: {actual!r} → {expected!r}")
        shell.run(f"editline {SETTINGS} {number} {expected}")


@task("s03e02", hub_name="firmware")
class FirmwareTask(BaseTask):
    """Naprawia konfigurację, odblokowuje binarkę i wyciąga kod `ECCS-…`."""

    dry_run_mode = DRY_RUN_UNSAFE
    """
    `--dry-run` jest tu odmawiany, bo nie istnieje wersja tego przebiegu bez skutków.

    `solve()` edytuje `settings.ini` przez `editline` i kasuje plik blokady na ŻYWEJ
    maszynie wirtualnej. Dotknięcie ścieżki z `.gitignore` kończy się banem i
    przywróceniem VM, a jedyny mechanizm przywracania (`reboot`) kasuje cały postęp
    i jest świadomie poza allowlistą — patrz `AGENTS.md` tego folderu.
    """

    def solve(self, data: None) -> dict[str, str]:
        """
        Zwraca `{"confirmation": "ECCS-…"}` — format oczekiwany przez hub.

        Kolejność wynika z komunikatów samej binarki: najpierw konfiguracja, dopiero
        potem zdjęcie blokady („Remove the lock file **if you are sure you have
        resolved the issue**"). Odwrotna kolejność zostawiłaby maszynę odblokowaną
        z zepsutą konfiguracją.
        """
        shell = ShellTool(self.hub)

        password = read_password(shell)
        _console.print(f"[bold]Hasło:[/] {password}")

        _console.print("[bold]Poprawiam settings.ini[/]")
        _fix_settings(shell)

        _console.print("[bold]Zdejmuję blokadę[/]")
        remove_lock(shell)

        output = shell.run(f"{BINARY} {password}")
        _console.print(f"[dim]{output}[/]")

        match = CODE_RE.search(output)
        if not match:
            raise RuntimeError(f"Brak kodu ECCS w odpowiedzi binarki:\n{output}")
        return {"confirmation": match.group()}
