"""
S04E05 — klient API magazynu i odczytu bazy.

Całe API zadania idzie przez `POST /verify` z obiektem narzędzia w polu `answer`,
więc „klient" to cienka warstwa nad `HubClient.submit()`. Wydzielona z `solution.py`
z jednego powodu: **paginacja odczytu bazy**, która jest tu jedyną nieoczywistą
mechaniką i jedynym miejscem, gdzie łatwo po cichu zgubić dane.

## Paginacja — pułapka numer jeden tego zadania

Każda odpowiedź `database` niesie `totalTableRows` i `limit`. Zmierzone 2026-08-24:
`destinations` ma **40 wierszy przy `limit: 30`**, więc naiwny `select * from destinations`
oddaje 30 z 40 i **nie sygnalizuje tego niczym poza tymi dwoma polami**. Staff kursu
naprowadzał na to słowami „zwróć uwagę na to, co jeszcze jest zwracane z bazy".

`select_all()` czyta `limit` z odpowiedzi zamiast go zakładać — gdyby backend zmienił
stronę na 20 albo 50, kod nadal pobierze komplet.
"""

from __future__ import annotations

from typing import Any

import logfire

from core.hub import HubClient
from core.runtime import check_abort

HUB_TASK = "foodwarehouse"


class WarehouseError(RuntimeError):
    """API magazynu odpowiedziało czymś, czego nie umiemy bezpiecznie zinterpretować."""


class Warehouse:
    """Klient narzędzi zadania — jedno wywołanie narzędzia to jedno `POST /verify`."""

    def __init__(self, hub: HubClient) -> None:
        """Zapamiętuje klienta huba."""
        self._hub = hub

    def call(self, **payload: Any) -> dict:
        """Wywołuje narzędzie i zwraca surową odpowiedź huba."""
        check_abort()
        return self._hub.submit(HUB_TASK, payload)

    def query(self, sql: str) -> dict:
        """Pojedyncze zapytanie do bazy (tylko odczyt, jedna strona wyników)."""
        return self.call(tool="database", query=sql)

    def select_all(self, table: str, columns: str = "*") -> list[dict]:
        """
        Pobiera KOMPLET wierszy tabeli, stronicując po `limit` z odpowiedzi.

        Args:
            table: Nazwa tabeli.
            columns: Lista kolumn do wybrania (domyślnie wszystkie).

        Returns:
            Wszystkie wiersze tabeli.

        Raises:
            WarehouseError: Gdy backend nie poda rozmiaru strony albo gdy pobrana
                liczba wierszy nie zgadza się z deklarowanym `totalTableRows` —
                cicha niekompletność jest tu gorsza niż przerwany przebieg, bo
                brakujące miasto oznacza brakujące zamówienie i odrzucenie na `done`.
        """
        # Pierwsze zapytanie BEZ `limit` — po to, żeby backend sam podał rozmiar strony
        # i rozmiar tabeli. Zaszycie tu „30" działałoby dziś i cicho gubiło wiersze
        # w dniu, w którym backend zmieni stronę.
        first = self.query(f"select {columns} from {table}")
        rows: list[dict] = list(first.get("rows") or [])
        total = first.get("totalTableRows")
        page_size = first.get("limit")

        if not isinstance(page_size, int) or page_size <= 0:
            raise WarehouseError(
                f"Tabela {table}: backend nie podał rozmiaru strony (`limit`={page_size!r}), "
                "więc nie da się bezpiecznie stwierdzić, czy wynik jest kompletny."
            )

        while total is not None and len(rows) < total:
            response = self.query(
                f"select {columns} from {table} limit {page_size} offset {len(rows)}"
            )
            page = response.get("rows") or []
            # Pusta strona kończy pętlę nawet gdy `totalTableRows` kłamie — inaczej
            # rozjazd między deklaracją a rzeczywistością dawałby nieskończoną pętlę.
            if not page:
                break
            rows.extend(page)

        if total is not None and len(rows) != total:
            raise WarehouseError(
                f"Tabela {table}: pobrano {len(rows)} wierszy, backend deklaruje {total}."
            )

        logfire.info(f"Pobrano tabelę {table}", rows=len(rows))
        return rows
