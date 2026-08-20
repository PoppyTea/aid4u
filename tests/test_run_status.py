"""
Testy licznika postępów w `run.py`.

Powód istnienia: licznik „ile jeszcze do 20" jest liczbą, według której planujemy
sezon, więc wliczenie do niego flagi sekretnej nie jest kosmetyką — zaniża pozostałą
pracę. Konwencja `sXXeYY_secret` była opisana w `AGENTS.md` (zasada 7) wcześniej niż
egzekwowana w kodzie; te testy domykają tę lukę.
"""

from __future__ import annotations

from run import SECRET_SUFFIX, partition_flags


class TestPartycjonowanieFlag:
    """Rozdział flag głównych i sekretnych."""

    def test_flaga_sekretna_nie_liczy_sie_do_glownych(self):
        main, secrets = partition_flags(
            {"s03e05": "{FLG:A}", "s03e05_secret": "{FLG:B}"}
        )
        assert list(main) == ["s03e05"]
        assert list(secrets) == ["s03e05_secret"]

    def test_bez_sekretow_wszystko_jest_glowne(self):
        flags = {"s01e01": "{FLG:A}", "s02e03": "{FLG:B}"}
        main, secrets = partition_flags(flags)
        assert main == flags
        assert secrets == {}

    def test_pusty_rejestr(self):
        assert partition_flags({}) == ({}, {})

    def test_sufiks_musi_byc_na_koncu(self):
        """`_secret` w środku nazwy to zwykłe zadanie, nie flaga sekretna."""
        main, secrets = partition_flags({"s03e05_secret_extra": "{FLG:X}"})
        assert list(main) == ["s03e05_secret_extra"]
        assert secrets == {}

    def test_kilka_sekretow_z_roznych_epizodow(self):
        main, secrets = partition_flags(
            {
                "s03e04": "{FLG:A}",
                "s03e04_secret": "{FLG:B}",
                "s03e05": "{FLG:C}",
                "s03e05_secret": "{FLG:D}",
            }
        )
        assert len(main) == 2 and len(secrets) == 2

    def test_klucze_pozostaja_nietkniete(self):
        """Partycjonowanie nie może obcinać sufiksu — to robi dopiero warstwa wyświetlania."""
        _, secrets = partition_flags({"s03e05_secret": "{FLG:B}"})
        assert "s03e05_secret" in secrets

    def test_sufiks_jest_wspoldzielony_ze_zrodlem_prawdy(self):
        """Test nie może zaszywać własnej kopii konwencji."""
        assert SECRET_SUFFIX == "_secret"
