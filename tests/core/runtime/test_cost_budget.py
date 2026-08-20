"""
Testy budżetu kosztu — Warstwa 2 kill switcha (AID-62).

Powód istnienia: wszystkie udokumentowane katastrofy kosztowe w komentarzach kursu do
S03E02 to **przekroczony budżet**, nie zły wynik („~$4, zabiło budżet $5 w 5 minut").
Ta osłona jest bezpiecznikiem, nie prewencją — cenę znamy dopiero po wywołaniu — więc
testy pilnują dokładnie tego, co obiecuje: przerwania PO przekroczeniu i głośnej
awarii, gdy ceny nie da się policzyć.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.runtime import AbortRun, check_abort, end_run, record_cost, spent_usd, start_run


class TestBudzetKosztu:
    """Zachowanie limitu na cały przebieg."""

    def test_przerywa_po_przekroczeniu(self):
        """Suma powyżej limitu przerywa przebieg przy najbliższym `check_abort()`."""
        start_run(max_cost=0.10)
        record_cost(0.07)
        check_abort()  # jeszcze pod limitem
        record_cost(0.05)
        with pytest.raises(AbortRun, match="budżet kosztu"):
            check_abort()

    def test_nie_przerywa_dokladnie_na_limicie(self):
        """Limit jest przekroczeniem, nie osiągnięciem — inaczej $1.00 z $1.00 by wywalało."""
        start_run(max_cost=0.10)
        record_cost(0.10)
        check_abort()

    def test_brak_limitu_nie_przerywa_nigdy(self):
        """Bez `max_cost` żadna suma nie przerywa — budżet jest opcjonalny."""
        start_run()
        record_cost(999.0)
        check_abort()

    def test_zero_znaczy_wylacz(self):
        """`--max-cost 0` to „bez limitu", inaczej niż `max_seconds=0` („przerwij zaraz")."""
        start_run(max_cost=0)
        record_cost(999.0)
        check_abort()

    def test_ujemny_limit_odrzucony(self):
        """Ujemny budżet nie ma znaczenia — lepiej odrzucić niż zgadywać intencję."""
        with pytest.raises(ValueError, match="max_cost"):
            start_run(max_cost=-1)

    def test_koszt_sumuje_sie_przez_przebieg(self):
        """Kolejne wywołania akumulują się, a nie nadpisują."""
        start_run(max_cost=10)
        for _ in range(4):
            record_cost(0.25)
        assert spent_usd() == pytest.approx(1.0)

    def test_end_run_zeruje_budzet(self):
        """Budżet jest stanem globalnym — nierozliczony przeciekłby na kolejny przebieg."""
        start_run(max_cost=0.01)
        record_cost(5.0)
        end_run()
        assert spent_usd() == 0.0
        check_abort()  # brak aktywnego przebiegu — nie ma czego przerywać

    def test_akumulacja_floatow_nie_przerywa_na_dokladnym_limicie(self):
        """
        Regresja: sto wywołań po $0.01 daje w zmiennoprzecinkowym
        `1.0000000000000007`, więc bez marginesu budżet $1.00 przerywał przebieg
        DOKŁADNIE na limicie — mimo że wydano dokładnie tyle, ile wolno.
        """
        start_run(max_cost=1.0)
        for _ in range(100):
            record_cost(0.01)
        assert spent_usd() > 1.0, "test straciłby sens, gdyby suma była dokładna"
        check_abort()

    def test_realne_przekroczenie_nadal_przerywa(self):
        """Margines dotyczy błędu reprezentacji, nie pobłażliwości wobec budżetu."""
        start_run(max_cost=1.0)
        record_cost(1.01)
        with pytest.raises(AbortRun):
            check_abort()

    def test_koszt_bez_aktywnego_przebiegu_jest_ignorowany(self):
        """`record_cost()` poza przebiegiem nie może wybuchnąć ani nic akumulować."""
        record_cost(1.0)
        assert spent_usd() == 0.0


class TestCichaAwariaOslony:
    """
    `cost=None` znaczy „nie udało się policzyć ceny".

    Przy ustawionym budżecie to jest cicha awaria osłony — przebieg wygląda na
    chroniony, nie będąc. Ten sam wzorzec `except Exception` ukrywał martwe
    `genai_prices.calculate()` przez wiele tygodni, więc tu musi być głośno.
    """

    def test_ostrzega_gdy_budzet_ustawiony(self):
        """Brak ceny przy ustawionym budżecie to cicha awaria osłony — musi być głośna."""
        start_run(max_cost=1.0)
        with patch("logfire.warning") as warn:
            record_cost(None)
        warn.assert_called_once()

    def test_milczy_gdy_budzetu_nie_ma(self):
        """Bez limitu brak ceny to zwykły brak telemetrii, nie awaria osłony."""
        start_run()
        with patch("logfire.warning") as warn:
            record_cost(None)
        warn.assert_not_called()

    def test_nieudane_liczenie_nie_zawyza_sumy(self):
        """Nieznana cena nie może być liczona jako jakakolwiek wartość."""
        start_run(max_cost=1.0)
        record_cost(0.5)
        record_cost(None)
        assert spent_usd() == pytest.approx(0.5)


class TestWspolistnieniaZBudzetemCzasu:
    """Oba limity działają niezależnie i oba są sprawdzane w `check_abort()`."""

    def test_sam_koszt_bez_czasu(self):
        """Budżet kosztu działa bez ustawionego budżetu czasu."""
        start_run(max_cost=0.01)
        record_cost(1.0)
        with pytest.raises(AbortRun, match="kosztu"):
            check_abort()

    def test_sam_czas_bez_kosztu(self):
        """Budżet czasu nie został zepsuty przez dołożenie kosztu."""
        start_run(max_seconds=0)
        record_cost(999.0)
        with pytest.raises(AbortRun, match="czasu"):
            check_abort()

    def test_oba_naraz_daja_aktywny_budzet(self):
        """Podanie obu limitów naraz aktywuje budżet i sprawdza oba."""
        start_run(max_seconds=3600, max_cost=0.01)
        record_cost(1.0)
        with pytest.raises(AbortRun):
            check_abort()
