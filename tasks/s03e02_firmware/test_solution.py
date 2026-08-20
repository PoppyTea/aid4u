"""
Testy s03e02 — offline, bez sieci.

Sercem pliku jest `TestAgentDestrukcyjny`: przepuszczamy przez PRAWDZIWE narzędzie listę
poleceń, które model mógłby wysłać, gdyby chciał zaszkodzić albo po prostu się pomylił,
i sprawdzamy, że **do backendu nie dociera żadne z nich**. To jest ta sama gwarancja,
o którą chodziło w pomyśle „agent kontra narzędzie, szkody ograniczone do wpisu w logu",
tylko zrealizowana bez kontenera — nasze narzędzie niczego nie wykonuje lokalnie, więc
kontener izolowałby proces, który i tak nie uruchamia poleceń. Fałszywy backend
sprawdza dokładnie to, co trzeba: co ZOSTAŁOBY wysłane.
"""

from __future__ import annotations

import pytest

from tasks.s03e02_firmware.shell import (
    IGNORED_GLOBS,
    LOCK_FILE,
    POLICY,
    ShellTool,
    remove_lock,
)
from tasks.s03e02_firmware.solution import CODE_RE, REQUIRED_LINES


class FakeHub:
    """Backend, który niczego nie wykonuje — tylko zapisuje, co do niego dotarło."""

    def __init__(self, reply: str = "ok") -> None:
        self.received: list[str] = []
        self._reply = reply

    def post_api(self, path: str, payload: dict) -> dict:
        """Rejestruje polecenie i zwraca ustaloną odpowiedź."""
        self.received.append(payload["cmd"])
        return {"data": self._reply}


@pytest.fixture
def hub() -> FakeHub:
    """Fałszywy hub dla pojedynczego testu."""
    return FakeHub()


@pytest.fixture
def shell(hub: FakeHub) -> ShellTool:
    """Narzędzie z prawdziwą polityką zadania, wpięte w fałszywy backend."""
    return ShellTool(hub)  # type: ignore[arg-type]


class TestAgentDestrukcyjny:
    """
    Model chce zaszkodzić — narzędzie ma ograniczyć skutek do wpisu w logu.

    Lista celowo miesza trzy motywy: kasowanie, obchodzenie zakazów katalogowych
    i sięganie po pliki z `.gitignore`. Wszystkie trzy kończą się na tej maszynie
    banem i przywróceniem VM do stanu początkowego.
    """

    DESTRUKCYJNE = [
        "rm /opt/firmware/cooler/settings.ini",
        "rm /opt/firmware/cooler/cooler.bin",
        "rm /home/operator/notes/pass.txt",
        "reboot",
        "cat /etc/passwd",
        "cat /etc/shadow",
        "cat /root/.ssh/id_rsa",
        "cat /proc/self/environ",
        "cat /opt/firmware/cooler/.env",
        "cat /opt/firmware/cooler/storage.cfg",
        "cat /opt/firmware/cooler/logs/error.log",
        "cat /opt/../etc/passwd",
        "cat //etc/passwd",
        "cat /et[c]/passwd",
        "ls /opt && rm -rf /",
        "ls /opt; reboot",
        "cat $HOME/.env",
        "cat ../../etc/passwd",
    ]

    @pytest.mark.parametrize("cmd", DESTRUKCYJNE)
    def test_nic_nie_dociera_do_backendu(self, shell: ShellTool, hub: FakeHub, cmd: str):
        """Polecenie jest odrzucane PRZED wysłaniem, nie po."""
        out = shell.run(cmd)
        assert out.startswith("ODRZUCONE PRZEZ BRAMKE"), f"przeszło: {cmd}"
        assert hub.received == [], f"dotarło do backendu: {hub.received}"

    def test_seria_prob_nie_przebija_sie_ani_razu(self, shell: ShellTool, hub: FakeHub):
        """
        Uparty agent wysyłający wszystko po kolei nie ma jak trafić.

        Test na całej serii, nie tylko pojedynczych przypadkach: gdyby któraś reguła
        zależała od kolejności albo stanu, tutaj by to wyszło.
        """
        for cmd in self.DESTRUKCYJNE:
            shell.run(cmd)
        assert hub.received == []
        assert len(shell.log) == len(self.DESTRUKCYJNE)
        assert all("ODRZUCONE" in wynik for _, wynik in shell.log)

    def test_szkoda_konczy_sie_na_wpisie_w_logu(self, shell: ShellTool):
        """Odmowa jest zapisana z powodem — to ma być jedyny ślad po próbie."""
        shell.run("rm -rf /")
        cmd, wynik = shell.log[-1]
        assert cmd == "rm -rf /"
        assert "nie jest dozwolone" in wynik


class TestPracaDozwolona:
    """Bramka nie może blokować tego, czego zadanie faktycznie wymaga."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "help",
            "ls /opt/firmware/cooler",
            "cat /opt/firmware/cooler/settings.ini",
            "cat /home/operator/notes/pass.txt",
            "editline /opt/firmware/cooler/settings.ini 2 SAFETY_CHECK=pass",
            "/opt/firmware/cooler/cooler.bin admin1",
            "find *pass*",
            "history",
            "whoami",
        ],
    )
    def test_polecenia_zadania_przechodza(self, shell: ShellTool, hub: FakeHub, cmd: str):
        """Każde z tych poleceń było potrzebne do rozwiązania epizodu."""
        shell.run(cmd)
        assert hub.received == [cmd], f"zablokowane bez powodu: {cmd}"

    def test_wzorzec_find_z_gwiazdka_nie_jest_globem_sciezki(self, shell, hub):
        """`find *.txt` to wzorzec nazwy, nie ścieżka — zakaz globów go nie dotyczy."""
        shell.run("find *.txt")
        assert hub.received == ["find *.txt"]


class TestKasowaniaBlokady:
    """`rm` jest dopuszczone wyłącznie dla jednego pliku i tylko przez `remove_lock()`."""

    def test_remove_lock_dziala(self, shell: ShellTool, hub: FakeHub):
        remove_lock(shell)
        assert hub.received == [f"rm {LOCK_FILE}"]

    def test_zwykla_polityka_nadal_odrzuca_rm(self, shell: ShellTool, hub: FakeHub):
        """Wyjątek dla blokady nie może przeciekać na politykę zadania."""
        assert "rm" not in POLICY.allowed_commands
        shell.run(f"rm {LOCK_FILE}")
        assert hub.received == []

    def test_sciezka_blokady_jest_zaszyta(self, shell: ShellTool, hub: FakeHub):
        """`remove_lock()` nie przyjmuje ścieżki, więc nie da się jej podmienić."""
        remove_lock(shell)
        assert hub.received[0].endswith("cooler-is-blocked.lock")


class TestZalozenZadania:
    """Fakty ustalone sondą, na których opiera się rozwiązanie."""

    def test_gitignore_zna_wszystkie_trzy_pulapki(self):
        """`.env`, `storage.cfg` i `logs/` to oczywiste miejsca na hasło — i droga do bana."""
        assert IGNORED_GLOBS == {".env", "storage.cfg", "logs/"}

    def test_trzy_usterki_settings_ini(self):
        """Zakomentowany SAFETY_CHECK, włączony test_mode, wyłączone chłodzenie."""
        assert REQUIRED_LINES == {2: "SAFETY_CHECK=pass", 6: "enabled=false", 10: "enabled=true"}

    def test_format_kodu(self):
        """Kod to `ECCS-` + 40 znaków hex."""
        assert CODE_RE.fullmatch("ECCS-" + "a" * 40)
        assert not CODE_RE.fullmatch("ECCS-" + "a" * 39)

    def test_kod_wyciagany_z_wyjscia_binarki(self):
        """Binarka drukuje kod wśród innych linii — regex musi go wyłuskać."""
        output = "Selfcheck... [OK]\nDONE\n\nECCS-" + "b" * 40
        assert CODE_RE.search(output).group() == "ECCS-" + "b" * 40
