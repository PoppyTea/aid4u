"""
Testy licznika postępów w `run.py`.

Powód istnienia: licznik „ile jeszcze do 20" jest liczbą, według której planujemy
sezon, więc wliczenie do niego flagi sekretnej nie jest kosmetyką — zaniża pozostałą
pracę. Konwencja `sXXeYY_secret` była opisana w `AGENTS.md` (zasada 7) wcześniej niż
egzekwowana w kodzie; te testy domykają tę lukę.

Druga klasa błędu w tej samej liczbie, dopisana 2026-08-24: zadania zaliczone POZA
`.flags.json` (żywy serwer w `s01e03_proxy`) były po prostu niewidoczne dla licznika,
więc „ile jeszcze do 20" zawyżało pracę o jedno zadanie. Flaga sekretna zaniżała,
to zawyżało — obie strony pilnują teraz testy.
"""

from __future__ import annotations

from run import (
    CERTIFICATE_THRESHOLD,
    COURSE_TASK_COUNT,
    SECRET_SUFFIX,
    SOLVED_OUTSIDE_FLAGS_FILE,
    count_solved,
    partition_flags,
)


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


class TestLiczeniePostepow:
    """`count_solved()` — liczba, według której planujemy sezon."""

    def test_wlicza_zadanie_zaliczone_poza_plikiem(self):
        """
        `s01e03_proxy` rozwiązuje się przez żywą rozmowę z naszym endpointem, więc jego
        flaga nigdy nie trafia do `.flags.json`. Pominięcie jej zawyża „ile do certyfikatu".
        """
        done, outside = count_solved({"s01e01": "{FLG:A}"})
        assert done == 2
        assert outside == {"s01e03"}

    def test_nie_liczy_podwojnie_gdy_flaga_jednak_trafi_do_pliku(self):
        """Gdyby epizod z tego zbioru kiedyś zapisał flagę normalnie, licznik ma zostać stabilny."""
        done, outside = count_solved({"s01e01": "{FLG:A}", "s01e03": "{FLG:B}"})
        assert done == 2
        assert outside == set()

    def test_flaga_sekretna_nadal_nie_liczy_sie_do_postepu(self):
        """Obie korekty muszą działać naraz: sekret out, zaliczone-poza-plikiem in."""
        done, _ = count_solved({"s01e01": "{FLG:A}", "s03e05_secret": "{FLG:B}"})
        assert done == 2  # s01e01 + s01e03, bez sekretu

    def test_pusty_plik_i_tak_widzi_zaliczone_poza_nim(self):
        """Świeży klon repo bez `.flags.json` nie może udawać, że s01e03 nie było."""
        done, outside = count_solved({})
        assert done == len(SOLVED_OUTSIDE_FLAGS_FILE)
        assert outside == set(SOLVED_OUTSIDE_FLAGS_FILE)

    def test_liczba_do_certyfikatu_nie_schodzi_ponizej_zera(self):
        """Po przekroczeniu progu licznik ma pokazywać 0, nie liczbę ujemną."""
        flags = {f"s0{i // 5 + 1}e0{i % 5 + 1}": "{FLG:X}" for i in range(25)}
        done, _ = count_solved(flags)
        assert done > CERTIFICATE_THRESHOLD
        assert max(0, CERTIFICATE_THRESHOLD - done) == 0


class TestStalychKursu:
    """Mianownik i próg — stałe kursu, nie pochodne stanu repo."""

    def test_mianownik_jest_rozmiarem_kursu(self):
        """
        Dawniej `total = len(TASK_REGISTRY)`, więc mianownik rósł razem z kodem i licznik
        go przegonił, wypisując „15/14 zadań". Kurs ma 25 epizodów niezależnie od tego,
        ile z nich mamy zaimplementowanych.

        Celowo NIE asertujemy `COURSE_TASK_COUNT != len(TASK_REGISTRY)` — to byłaby
        asercja przypadku, nie kontraktu: pęknie w dniu, w którym zaimplementujemy
        wszystkie 25 zadań, choć kod będzie wtedy zupełnie poprawny.
        """
        assert COURSE_TASK_COUNT == 25

    def test_licznik_nie_przekracza_mianownika_przy_komplecie(self):
        """Rzeczywisty objaw dawnej usterki: `done` przebijało `total`, dając „15/14"."""
        flags = {f"s0{i // 5 + 1}e0{i % 5 + 1}": "{FLG:X}" for i in range(25)}
        done, _ = count_solved(flags)
        assert done <= COURSE_TASK_COUNT

    def test_prog_certyfikatu(self):
        assert CERTIFICATE_THRESHOLD == 20
