"""
S04E03 `domatowo` — odnalezienie partyzanta i ewakuacja w budżecie 300 punktów akcji.

**Zero LLM.** Cała treść zadania sprowadza się do jednego pytania: w którym z pól typu
`block3` siedzi człowiek. Przechwycony sygnał („Ukryłem się w jednym z najwyższych
bloków") zawęża 121 pól planszy do 14, a reszta to arytmetyka kosztu. Społeczność
potwierdza kierunek: *„Tak »deterministycznie« szło u mnie też najlepiej, Agent czasem
wysyłał w losowe miejsca."*

Jedyny udokumentowany sposób przegrania to przepalenie punktów — *„jeśli np. agent
zasuwa jednym zwiadowcą na piechotę i nie zapamiętuje już sprawdzonych lokalizacji"*.
Stąd kształt rozwiązania: transporter dowozi grupę (1 pkt/pole), `dismount` jest darmowy,
a zwiadowca robi najwyżej kilka kroków po 7 pkt wewnątrz budynku.

## Wykrywanie trafienia — protokół, nie dopasowanie tekstu

Logi `inspect` to zdania generowane, o zmiennym słownictwie („Pokój pusty…", „Nic
wartościowego…", „Pomieszczenie bez ludzi…"), więc rozpoznawanie sukcesu po treści
byłoby kruche. Zamiast tego pytamy API: `callHelicopter` **kosztuje 0 punktów** i zwraca
HTTP 400, dopóki żaden zwiadowca nie potwierdził człowieka. Próba po każdej inspekcji
jest więc darmowa i autorytatywna — sam hub rozstrzyga, czy już znaleźliśmy.
"""

from __future__ import annotations

# ─── Observability jako pierwsze ─────────────────────────────────────────────
from core.observability.setup import setup_observability

setup_observability()

# ─── Właściwe importy po setup obserwabilności ───────────────────────────────
import httpx
import logfire
from rich.console import Console
from rich.markup import escape

from core.runtime import check_abort
from core.tasks import BaseTask, task
from tasks.s04e03_domatowo.city import (
    ROAD_TILE,
    TARGET_TILE,
    Landing,
    cluster,
    plan_landing,
    sweep_order,
    tiles_of,
)

_console = Console()

HUB_TASK = "domatowo"

# Limity z treści zadania. Przekroczenie kończy się odmową ze strony API, więc plan
# desantu musi się w nich zmieścić, zanim cokolwiek wyślemy w teren.
MAX_SCOUTS = 8
MAX_TRANSPORTERS = 4
MAX_PASSENGERS = 4

# Pole, na którym API stawia nowo utworzone jednostki (`create` opisuje „A6 -> D6").
SPAWN = "A6"


class MissionFailed(RuntimeError):
    """Operacja nie może się udać — przerywamy, zamiast dopalać punkty w ciemno."""


@task("s04e03", hub_name="domatowo")
class DomatowoTask(BaseTask):
    """Deterministyczne przeszukanie najwyższych bloków i wezwanie śmigłowca."""

    def solve(self, data: None) -> dict[str, str]:
        """
        Znajduje partyzanta i zwraca wywołanie ewakuacji.

        Args:
            data: Nieużywane — cały stan żyje po stronie API zadania.

        Returns:
            `{"action": "callHelicopter", "destination": <pole>}` — wysyła je
            `BaseTask._submit()`, żeby zgłoszenie poszło dokładnie raz.
        """
        # `reset` jest darmowy i przelosowuje pozycję partyzanta, więc czyni każdy
        # przebieg powtarzalnym: bez niego druga próba startowałaby z jednostkami
        # i punktami z pierwszej.
        self._call(action="reset")

        grid = self._call(action="getMap")["map"]["grid"]
        roads = set(tiles_of(grid, ROAD_TILE))
        buildings = cluster(tiles_of(grid, TARGET_TILE))
        _console.print(
            f"[bold]Cele:[/] {sum(len(b) for b in buildings)} pól `{TARGET_TILE}` "
            f"w {len(buildings)} budynkach"
        )

        for building in buildings:
            landing = plan_landing(building, roads, SPAWN)
            found = self._search(landing)
            if found:
                _console.print(f"[bold green]Partyzant znaleziony:[/] {found}")
                return {"action": "callHelicopter", "destination": found}

        raise MissionFailed(
            f"Sprawdzono wszystkie {sum(len(b) for b in buildings)} pól `{TARGET_TILE}` "
            "i nie znaleziono człowieka — założenie z przechwyconego sygnału nie działa."
        )

    def _search(self, landing: Landing) -> str | None:
        """
        Wysadza desant pod jednym budynkiem i sprawdza jego pola.

        Returns:
            Pole, na którym potwierdzono człowieka, albo `None` gdy budynek jest pusty.
        """
        passengers = min(MAX_PASSENGERS, len(landing.targets))
        transporter = self._call(
            action="create", type="transporter", passengers=passengers
        )["object"]
        self._call(action="move", object=transporter, where=landing.dropoff)
        self._call(action="dismount", object=transporter, passengers=passengers)

        # Gdzie faktycznie wylądowali, wie tylko API: `dismount` stawia zwiadowców
        # „on free tiles around vehicle", bez możliwości wskazania pola. Czasem trafia
        # to od razu w cel i wtedy pierwszy krok jest za darmo.
        scouts = {
            unit["id"]: unit["position"]
            for unit in self._call(action="getObjects")["objects"]
            if unit["typ"] == "scout"
        }
        _console.print(
            f"  desant na [cyan]{landing.dropoff}[/] ({landing.drive_cost} pkt dojazdu), "
            f"{len(scouts)} zwiadowców"
        )

        for scout, target in sweep_order(landing.targets, scouts):
            if scouts[scout] != target:
                self._call(action="move", object=scout, where=target)
                scouts[scout] = target

            self._call(action="inspect", object=scout)
            if self._human_confirmed(target):
                return target

        return None

    def _human_confirmed(self, field: str) -> bool:
        """
        Pyta API, czy któryś zwiadowca potwierdził już człowieka.

        `callHelicopter` kosztuje 0 punktów i odpowiada 400, dopóki nikt nie potwierdził —
        to czyni z niego darmowy, autorytatywny test. Treść logów `inspect` jest
        generowana i zmienna, więc nie nadaje się na kryterium.
        """
        try:
            self.hub.submit(HUB_TASK, {"action": "callHelicopter", "destination": field})
        except httpx.HTTPStatusError as rejected:
            if rejected.response.status_code == 400:
                return False
            raise
        return True

    def _call(self, **payload: str | int) -> dict:
        """Jedna akcja API zadania; loguje pozostały budżet, gdy hub go poda."""
        check_abort()
        response = self.hub.submit(HUB_TASK, payload)

        left = response.get("action_points_left")
        if left is not None:
            logfire.info("Akcja domatowo", action=payload.get("action"), points_left=left)
            if left <= 0:
                raise MissionFailed(f"Wyczerpano punkty akcji przy {escape(str(payload))}.")
        return response
