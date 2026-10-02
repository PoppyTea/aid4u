"""
S04E04 `filesystem` — notatki Natana zamienione na strukturę katalogów.

**Zero LLM — wbrew intelowi społeczności, i to jest tu najciekawsze.** Komentarze kursu
są zgodne, że to zadanie lingwistyczne, na którym wykładały się modele lokalne
(*„o ile radziły sobie z czystą gramatyką to gubiły się w znaczeniu tych notatek"*),
a przeszło dopiero `gemini-3-flash` za $0.26. Deterministyczna droga istnieje, bo
w paczce leży plik, którego nikt nie potraktował jako słownika: `transakcje.txt` podaje
**wszystkie miasta i wszystkie towary w mianowniku**, w sztywnym formacie
`Miasto -> towar -> Miasto`. To zamienia „rozpoznaj polską odmianę" w „dopasuj formę
odmienioną do znanego, skończonego słownika" — czyli w dopasowanie rdzenia.

Parsowanie żyje w `notes.py` (funkcje czyste); tutaj zostaje sama komunikacja z API.

## Dlaczego kolejność operacji nie jest kosmetyczna

`help` podaje regułę wprost: **„markdown links must point to existing files"**. Pliki
`/osoby` i `/towary` linkują do `/miasta`, więc katalogi i miasta muszą powstać wcześniej.
`batch_mode` wykonuje operacje po kolei, więc wystarczy właściwa kolejność w jednej liście.

## Weryfikacja niezależna od huba

`ogloszenia.txt` opisuje to samo zapotrzebowanie ośmiu miast, co `food4cities.json`
pobrane w `s04e05` — plik z zupełnie innego zadania. Testy porównują wynik parsera
z tamtym plikiem, więc błąd w rozpoznawaniu odmiany wychodzi offline, a nie na hubie.
Ta walidacja wyłapała trzy osobne usterki, zanim cokolwiek poszło w świat.
"""

from __future__ import annotations

# ─── Observability jako pierwsze ─────────────────────────────────────────────
from core.observability.setup import setup_observability

setup_observability()

# ─── Właściwe importy po setup obserwabilności ───────────────────────────────
import io
import zipfile

import logfire
from rich.console import Console

from core.net import expect_binary
from core.tasks import DRY_RUN_LIVE, BaseTask, task
from tasks.s04e04_filesystem.notes import Ledger, build_operations, read_notes

_console = Console()

NOTES_URL = "dane/natan_notes.zip"


@task("s04e04", hub_name="filesystem")
class FilesystemTask(BaseTask):
    """Buduje `/miasta`, `/osoby` i `/towary` jednym `batch_mode`, potem oddaje `done`."""

    dry_run_mode = DRY_RUN_LIVE
    """
    Odpowiedź powstaje z odpowiedzi huba, więc `--dry-run` wykonuje pełny protokół
    na żywo i wstrzymuje wyłącznie punktowane zgłoszenie. Odwracalne: `reset` czyści cały wirtualny
    system plików.
    """

    def fetch_data(self) -> Ledger:
        """
        Pobiera i rozpakowuje notatki Natana, po czym je czyta.

        Returns:
            Komplet wiedzy z paczki — miasta, towary, oferty, zapotrzebowanie, opiekunowie.
        """
        raw = self.hub.get_public(NOTES_URL)
        payload = raw if isinstance(raw, bytes) else raw.encode()
        # Hub potrafi oddać HTTP 200 ze stroną błędu zamiast pliku; bez tej kontroli
        # `zipfile` wywaliłby się komunikatem o uszkodzonym archiwum, mylącym co do przyczyny.
        expect_binary(payload, "zip", source=NOTES_URL)

        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            files = {
                name: archive.read(name).decode("utf-8")
                for name in archive.namelist()
                if not name.endswith("/")
            }

        ledger = read_notes(files)
        _console.print(
            f"[bold]Notatki:[/] {len(ledger.cities)} miast, {len(ledger.goods)} towarów, "
            f"{len(ledger.managers)} osób"
        )
        return ledger

    def solve(self, data: Ledger) -> dict[str, str]:
        """
        Odtwarza strukturę katalogów w wirtualnym systemie plików.

        Args:
            data: Wynik `fetch_data()`.

        Returns:
            `{"action": "done"}` — finalną weryfikację wysyła `BaseTask._submit()`,
            więc zgłoszenie idzie dokładnie raz.
        """
        # `reset` czyści cały filesystem i jest darmowy, więc czyni przebieg
        # idempotentnym: bez niego powtórka dokładałaby pliki do poprzedniej próby,
        # a `createFile` nadpisuje tylko tę samą ścieżkę.
        self.hub.submit(self._hub_task_name, {"action": "reset"})

        operations = build_operations(data)
        response = self.hub.submit(self._hub_task_name, operations)
        logfire.info("Filesystem zbudowany", operations=len(operations), code=response.get("code"))

        for city in sorted(data.managers):
            _console.print(f"  [cyan]{city:12}[/] {data.managers[city]}")
        _console.print(f"[bold green]Wykonano {len(operations)} operacji[/]")

        return {"action": "done"}
