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

## Wykrywanie trafienia — dlaczego NIE przez `callHelicopter`

Kuszące jest użycie `callHelicopter` jako testu: kosztuje 0 punktów i zwraca HTTP 400,
dopóki nikt nie potwierdził człowieka. Ta droga jest jednak błędna i została odrzucona
po tym, jak zadziałała: **wywołanie testujące JEST wykonaniem ewakuacji**, więc
`--dry-run` — który ma pokazać odpowiedź bez jej wysyłania — kończył misję naprawdę.

Zamiast tego czytamy `getLogs` (też 0 punktów) i klasyfikujemy ostatni wpis przez
`city.reads_as_found()`. Zdanie nierozpoznane nie jest cicho traktowane jako pustka —
przemiatanie liczy takie przypadki i mówi o nich w błędzie końcowym.
"""

from __future__ import annotations

# ─── Observability jako pierwsze ─────────────────────────────────────────────
from core.observability.setup import setup_observability

setup_observability()

# ─── Właściwe importy po setup obserwabilności ───────────────────────────────
import logfire
from rich.console import Console
from rich.markup import escape

from core.runtime import check_abort
from core.tasks import DRY_RUN_LIVE, BaseTask, task
from tasks.s04e03_domatowo.city import (
    ROAD_TILE,
    TARGET_TILE,
    Landing,
    allocate_scouts,
    cluster,
    plan_landing,
    reads_as_found,
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

    dry_run_mode = DRY_RUN_LIVE
    """
    Odpowiedź powstaje z odpowiedzi huba, więc `--dry-run` wykonuje pełny protokół
    na żywo i wstrzymuje wyłącznie punktowane zgłoszenie. Odwracalne: `reset` na
    starcie przywraca planszę i punkty akcji.
    """

    _unreadable: int = 0
    """Liczba wpisów logu, których nie dało się jednoznacznie zaklasyfikować."""

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

        self._unreadable = 0
        crews = allocate_scouts([len(b) for b in buildings], MAX_SCOUTS, MAX_PASSENGERS)
        if len(buildings) > MAX_TRANSPORTERS:
            raise MissionFailed(
                f"{len(buildings)} budynków przy limicie {MAX_TRANSPORTERS} transporterów."
            )
        _console.print(f"[bold]Przydział zwiadowców:[/] {crews} (limit {MAX_SCOUTS})")

        for building, crew in zip(buildings, crews, strict=True):
            landing = plan_landing(building, roads, SPAWN)
            found = self._search(landing, crew)
            if found:
                _console.print(f"[bold green]Partyzant znaleziony:[/] {found}")
                return {"action": "callHelicopter", "destination": found}

        unreadable = (
            f" {self._unreadable} wpisów logu miało nierozpoznane słownictwo — przeczytaj"
            " je (`getLogs`) zanim uznasz planszę za pustą."
            if self._unreadable
            else ""
        )
        raise MissionFailed(
            f"Sprawdzono wszystkie {sum(len(b) for b in buildings)} pól `{TARGET_TILE}` "
            f"i nie znaleziono człowieka.{unreadable}"
        )

    def _search(self, landing: Landing, passengers: int) -> str | None:
        """
        Wysadza desant pod jednym budynkiem i sprawdza jego pola.

        Args:
            landing: Punkt zrzutu i cele budynku.
            passengers: Liczba zwiadowców przydzielona temu budynkowi z globalnego
                limitu — patrz `city.allocate_scouts()`.

        Returns:
            Pole, na którym potwierdzono człowieka, albo `None` gdy budynek jest pusty.
        """
        # Zwiadowcy z poprzednich budynków nadal stoją na planszy, więc bez zapamiętania
        # stanu SPRZED desantu kolejny budynek „widziałby" ich wszystkich i plan mógłby
        # pchnąć kogoś przez pół mapy po 7 punktów za pole.
        before = self._scout_positions()

        transporter = self._call(
            action="create", type="transporter", passengers=passengers
        )["object"]
        self._call(action="move", object=transporter, where=landing.dropoff)
        self._call(action="dismount", object=transporter, passengers=passengers)

        # Gdzie faktycznie wylądowali, wie tylko API: `dismount` stawia zwiadowców
        # „on free tiles around vehicle", bez możliwości wskazania pola. Czasem trafia
        # to od razu w cel i wtedy pierwszy krok jest za darmo.
        scouts = {
            unit: field for unit, field in self._scout_positions().items() if unit not in before
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
            verdict = self._read_verdict(target)
            if verdict is True:
                return target
            if verdict is None:
                self._unreadable += 1

        return None

    def _scout_positions(self) -> dict[str, str]:
        """Mapa `identyfikator zwiadowcy → pole`, prosto z API (odczyt kosztuje 0)."""
        return {
            unit["id"]: unit["position"]
            for unit in self._call(action="getObjects")["objects"]
            if unit["typ"] == "scout"
        }

    def _read_verdict(self, field: str) -> bool | None:
        """
        Czyta najświeższy wpis logu dla danego pola i klasyfikuje go.

        Returns:
            `True` gdy człowiek potwierdzony, `False` gdy pusto, `None` gdy słownictwo
            komunikatu nie pasuje do żadnej ze znanych grup.
        """
        entries = [e for e in self._call(action="getLogs")["logs"] if e.get("field") == field]
        if not entries:
            return None

        message = str(entries[-1].get("msg", ""))
        verdict = reads_as_found(message)
        if verdict is None:
            logfire.warning("Nierozpoznany komunikat inspect", field=field, msg=message)
            _console.print(f"    [yellow]?[/] {field}: {escape(message)}")
        return verdict

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
