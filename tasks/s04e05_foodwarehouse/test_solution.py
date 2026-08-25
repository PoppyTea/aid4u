"""
Testy s04e05 — offline, bez sieci.

Zakres celowo wąski: stronicowanie odczytu bazy i złączenie miast po nazwie. To dwie
rzeczy, które w tym zadaniu psują się CICHO — niepełna tabela i nietrafione dopasowanie
dają zamówienie mniej, a nie wyjątek. Reszta przepływu to wywołania HTTP, których test
jednostkowy nie zweryfikuje lepiej niż `--dry-run` na żywym hubie.
"""

from __future__ import annotations

import pytest

from tasks.s04e05_foodwarehouse.solution import FoodWarehouseTask, OrderPreparationError
from tasks.s04e05_foodwarehouse.warehouse import Warehouse, WarehouseError


class FakeHub:
    """Hub, który nic nie wysyła — oddaje przygotowane odpowiedzi i zapisuje żądania."""

    def __init__(self, responses: list[dict]) -> None:
        """Kolejne wywołania `submit()` zwracają kolejne elementy `responses`."""
        self.responses = list(responses)
        self.calls: list[dict] = []

    def submit(self, task: str, answer: dict) -> dict:
        """Zapisuje żądanie i oddaje następną przygotowaną odpowiedź."""
        self.calls.append(answer)
        return self.responses.pop(0)


def warehouse(hub: FakeHub) -> Warehouse:
    """
    Buduje `Warehouse` na fałszywym hubie.

    Jedno miejsce z `type: ignore` zamiast jednego w każdym teście — `Warehouse`
    potrzebuje wyłącznie metody `submit()`, ale deklaruje pełny `HubClient`.
    Ta sama konwencja co `tasks/s03e02_firmware/test_solution.py:49`.
    """
    return Warehouse(hub)  # type: ignore[arg-type]


def page(rows: list[dict], total: int, limit: int = 30) -> dict:
    """Buduje odpowiedź `database` w kształcie, w jakim oddaje ją hub."""
    return {"code": 170, "rows": rows, "totalTableRows": total, "count": len(rows), "limit": limit}


class TestStronicowanieOdczytu:
    """`select_all()` — pułapka numer jeden tego zadania."""

    def test_pobiera_wszystkie_strony(self) -> None:
        """
        Realny przypadek: `destinations` ma 40 wierszy przy `limit: 30`.

        Naiwny `select *` oddaje 30 i nie sygnalizuje tego niczym poza polami
        `totalTableRows`/`limit` — czyli dziesięć miast po cichu zostałoby bez zamówienia.
        """
        first = [{"destination_id": i, "name": f"M{i}"} for i in range(30)]
        second = [{"destination_id": i, "name": f"M{i}"} for i in range(30, 40)]
        hub = FakeHub([page(first, 40), page(second, 40)])

        rows = warehouse(hub).select_all("destinations")

        assert len(rows) == 40
        assert "offset 30" in hub.calls[1]["query"]

    def test_rozmiar_strony_bierze_z_odpowiedzi_nie_z_zalozenia(self) -> None:
        """Zaszyte „30" działałoby dziś i gubiło wiersze w dniu zmiany backendu."""
        hub = FakeHub([page([{"a": 1}], 3, limit=1), page([{"a": 2}], 3), page([{"a": 3}], 3)])

        warehouse(hub).select_all("t")

        assert "limit 1 offset 1" in hub.calls[1]["query"]

    def test_pierwsze_zapytanie_bez_limitu(self) -> None:
        """Rozmiar strony trzeba najpierw POZNAĆ — więc pierwsze zapytanie go nie narzuca."""
        hub = FakeHub([page([{"a": 1}], 1)])

        warehouse(hub).select_all("t")

        assert "limit" not in hub.calls[0]["query"]

    def test_niekompletny_wynik_przerywa_zamiast_udawac_komplet(self) -> None:
        """Backend deklaruje 40, oddaje 30 i pustą stronę — cichy brak jest gorszy niż błąd."""
        hub = FakeHub([page([{"a": 1}], 40), page([], 40)])

        with pytest.raises(WarehouseError, match="pobrano 1 wierszy, backend deklaruje 40"):
            warehouse(hub).select_all("t")

    def test_brak_rozmiaru_strony_przerywa(self) -> None:
        """Bez `limit` nie da się stwierdzić, czy wynik jest kompletny — nie zgadujemy."""
        hub = FakeHub([{"rows": [{"a": 1}], "totalTableRows": 40}])

        with pytest.raises(WarehouseError, match="rozmiaru strony"):
            warehouse(hub).select_all("t")


class TestZlaczenieMiast:
    """Pułapka numer dwa: nazwy miast mają inną wielkość liter po obu stronach."""

    def test_mapa_ignoruje_wielkosc_liter(self) -> None:
        """
        `food4cities.json` ma `domatowo`, `destinations.name` ma `Domatowo`.

        Dosłowne porównanie zwraca zero wierszy i wygląda jak „miasta nie ma w tabeli" —
        społeczność kursu wyciągnęła z tego wniosek, że miasto jest zniszczone i trzeba
        je pominąć. Zmierzone: `where name = 'domatowo'` → 0 wierszy,
        `where name = 'Domatowo'` → `destination_id 761834`.
        """
        hub = FakeHub([page([{"destination_id": 761834, "name": "Domatowo"}], 1)])
        task = FoodWarehouseTask.__new__(FoodWarehouseTask)

        mapping = task._load_destinations(warehouse(hub))

        assert mapping["domatowo"] == 761834


class TestWyborTworcy:
    """`creatorID` musi wskazywać istniejącego użytkownika roli obsługującej transporty."""

    ROWS = [
        {"user_id": 7, "login": "bkurek", "birthday": "1951-04-12", "role": 2, "is_active": 1},
        {"user_id": 2, "login": "tgajewski", "birthday": "1991-04-06", "role": 2, "is_active": 1},
        {"user_id": 4, "login": "praktykant", "birthday": "2000-01-01", "role": 3, "is_active": 1},
    ]

    def test_wybiera_deterministycznie_najnizsze_id(self) -> None:
        """Dwa przebiegi mają dać ten sam podpis, więc wybór nie może zależeć od kolejności."""
        hub = FakeHub([page(self.ROWS, len(self.ROWS))])
        task = FoodWarehouseTask.__new__(FoodWarehouseTask)

        assert task._pick_creator(warehouse(hub))["login"] == "tgajewski"

    def test_pomija_inne_role(self) -> None:
        """Praktykant ma niższy `user_id` niż `bkurek`, a mimo to nie może być twórcą."""
        hub = FakeHub([page(self.ROWS, len(self.ROWS))])
        task = FoodWarehouseTask.__new__(FoodWarehouseTask)

        assert task._pick_creator(warehouse(hub))["role"] == 2

    def test_brak_kandydata_przerywa(self) -> None:
        """Pusta lista twórców oznacza zmianę po stronie backendu, nie powód do improwizacji."""
        hub = FakeHub([page([{"user_id": 4, "role": 3, "is_active": 1}], 1)])
        task = FoodWarehouseTask.__new__(FoodWarehouseTask)

        with pytest.raises(OrderPreparationError, match="Brak aktywnego użytkownika"):
            task._pick_creator(warehouse(hub))


class TestBrakMiastaWBazie:
    """Miasto bez kodu docelowego to błąd danych, nie pozycja do pominięcia."""

    def test_nieznane_miasto_przerywa_zamiast_pomijac(self) -> None:
        """
        Pominięcie miasta dałoby siedem zamówień zamiast ośmiu i odrzucenie na `done`
        bez wskazania przyczyny — dokładnie ten tryb porażki opisuje intel społeczności.
        """
        task = FoodWarehouseTask.__new__(FoodWarehouseTask)

        with pytest.raises(OrderPreparationError, match="nie ma odpowiednika"):
            task._place_order(warehouse(FakeHub([])), {"login": "x"}, "atlantyda", {}, {"woda": 1})
