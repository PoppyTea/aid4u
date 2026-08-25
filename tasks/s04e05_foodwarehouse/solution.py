"""
S04E05 `foodwarehouse` — osiem zamówień magazynowych pod zapotrzebowanie miast.

**Zero LLM.** Zadanie to pobranie danych, złączenie ich po kluczach i wysłanie —
ocena powtórzona w komentarzach kursu: *„użycie agentów tutaj będzie sztuką dla sztuki"*
i *„jeśli zadanie polega na pobraniu danych, przeliczeniu ich i wysłaniu, to po co
wplątywać w to model?"*.

Przepływ:

1. `food4cities.json` → mapa `miasto → {towar: ilość}` (8 miast).
2. `destinations` (SQLite, **stronicowane**) → mapa `miasto → destination_id`.
3. `users` → twórca zamówień z roli „Obsługa transportów".
4. Per miasto: `signatureGenerator` → `orders.create` → `orders.append` (batch).
5. `done` — zwracane jako odpowiedź zadania, wysyła je dopiero `BaseTask._submit()`.

Dwie pułapki, obie zmierzone na żywo — szczegóły w `AGENTS.md` tego folderu:
odpowiedź `database` jest stronicowana (40 wierszy przy `limit: 30`), a nazwy miast
mają inną wielkość liter po obu stronach złączenia.
"""

from __future__ import annotations

# ─── Observability jako pierwsze ─────────────────────────────────────────────
from core.observability.setup import setup_observability

setup_observability()

# ─── Właściwe importy po setup obserwabilności ───────────────────────────────
import json

import logfire
from rich.console import Console

from core.net import expect_not_html
from core.tasks import BaseTask, task
from tasks.s04e05_foodwarehouse.warehouse import Warehouse, WarehouseError

_console = Console()

CITIES_URL = "dane/food4cities.json"

# Rola twórcy zamówień. Wybrana nie z nazwy, tylko z obserwacji: wszystkie cztery
# zaszczepione zamówienia (creatorID 2, 5, 7, 8) należą do użytkowników tej roli.
CREATOR_ROLE = 2


class OrderPreparationError(RuntimeError):
    """Dane nie pozwalają zbudować kompletu zamówień — przerywamy zamiast zgadywać."""


@task("s04e05", hub_name="foodwarehouse")
class FoodWarehouseTask(BaseTask):
    """Tworzy po jednym zamówieniu na miasto i zwraca wywołanie `done` jako odpowiedź."""

    def fetch_data(self) -> dict[str, dict[str, int]]:
        """
        Pobiera zapotrzebowanie miast z huba.

        Returns:
            Mapa `miasto → {towar: ilość}`.
        """
        raw = self.hub.get_public(CITIES_URL)
        payload = raw if isinstance(raw, bytes) else raw.encode()
        # Hub potrafi oddać HTTP 200 ze stroną błędu zamiast pliku — bez tej kontroli
        # `json.loads` wywaliłby się komunikatem o składni, mylącym co do przyczyny.
        expect_not_html(payload, source=CITIES_URL)
        return json.loads(payload)

    def solve(self, data: dict[str, dict[str, int]]) -> dict[str, str]:
        """
        Buduje komplet zamówień i zwraca wywołanie kończące zadanie.

        Args:
            data: Zapotrzebowanie miast z `fetch_data()`.

        Returns:
            `{"tool": "done"}` — finalną weryfikację wysyła `BaseTask._submit()`.
        """
        warehouse = Warehouse(self.hub)

        # Bez tego powtórny przebieg dokładałby drugi komplet zamówień do pierwszego,
        # a zadanie wymaga DOKŁADNIE tylu zamówień, ile jest miast. `reset` czyni
        # każde uruchomienie idempotentnym i jest darmowy.
        warehouse.call(tool="reset")

        destinations = self._load_destinations(warehouse)
        creator = self._pick_creator(warehouse)
        _console.print(
            f"[bold]Twórca:[/] {creator['login']} (ID {creator['user_id']}, "
            f"{creator['name_surname']})"
        )

        for city, needs in data.items():
            self._place_order(warehouse, creator, city, destinations, needs)

        _console.print(f"[bold green]Utworzono {len(data)} zamówień[/]")
        return {"tool": "done"}

    def _load_destinations(self, warehouse: Warehouse) -> dict[str, int]:
        """
        Buduje mapę `nazwa miasta → destination_id`, kluczowaną bez wielkości liter.

        `food4cities.json` używa małych liter (`domatowo`), a `destinations.name`
        wielkich (`Domatowo`) — dosłowne porównanie zwraca zero wierszy i wygląda
        jak „miasta nie ma w tabeli". Stąd `casefold()` po obu stronach złączenia.
        """
        rows = warehouse.select_all("destinations")
        return {row["name"].casefold(): row["destination_id"] for row in rows}

    def _pick_creator(self, warehouse: Warehouse) -> dict:
        """
        Wybiera aktywnego użytkownika z roli twórcy zamówień.

        Deterministycznie najniższy `user_id`, żeby dwa przebiegi dały ten sam podpis
        i dały się porównać. Podpis wiąże login, datę urodzenia i cel, więc jeden
        twórca obsługuje wszystkie miasta.
        """
        rows = warehouse.select_all(
            "users", "user_id, login, name_surname, birthday, role, is_active"
        )
        candidates = [
            row for row in rows if row.get("role") == CREATOR_ROLE and row.get("is_active")
        ]
        if not candidates:
            raise OrderPreparationError(
                f"Brak aktywnego użytkownika w roli {CREATOR_ROLE} wśród {len(rows)} wierszy."
            )
        return min(candidates, key=lambda row: row["user_id"])

    def _place_order(
        self,
        warehouse: Warehouse,
        creator: dict,
        city: str,
        destinations: dict[str, int],
        needs: dict[str, int],
    ) -> None:
        """Tworzy jedno zamówienie dla miasta i dopisuje do niego komplet towarów."""
        destination = destinations.get(city.casefold())
        if destination is None:
            raise OrderPreparationError(
                f"Miasto {city!r} nie ma odpowiednika w tabeli destinations "
                f"({len(destinations)} wpisów) — bez kodu docelowego nie ma zamówienia."
            )

        # Podpis wraca w polu `hash`, nie `signature` — mimo że `orders.create`
        # oczekuje go pod nazwą `signature`. Ustalone sondą; `help` opisuje parametry
        # wejściowe narzędzia, nie kształt jego odpowiedzi.
        generated = warehouse.call(
            tool="signatureGenerator",
            action="generate",
            login=creator["login"],
            birthday=creator["birthday"],
            destination=destination,
        )
        signature = generated.get("hash") or generated.get("signature")
        if not signature:
            raise OrderPreparationError(f"Brak podpisu dla {city} (destination {destination}).")

        created = warehouse.call(
            tool="orders",
            action="create",
            title=f"Dostawa dla: {city}",
            creatorID=creator["user_id"],
            destination=destination,
            signature=signature,
        )
        order_id = created.get("id") or (created.get("order") or {}).get("id")
        if not order_id:
            raise WarehouseError(f"Utworzenie zamówienia dla {city} nie zwróciło id: {created}")

        # Batch — jedno wywołanie na miasto zamiast jednego na towar. Ilości idą
        # dokładnie takie, jak w pliku: zadanie odrzuca zarówno braki, jak i nadmiary.
        warehouse.call(tool="orders", action="append", id=order_id, items=needs)

        logfire.info("Zamówienie utworzone", city=city, destination=destination, items=len(needs))
        _console.print(f"  [cyan]{city:14}[/] → {destination}  ({len(needs)} pozycji)")
