"""
S03E02 — narzędzie powłoki z bramką bezpieczeństwa wymuszoną w kodzie.

Zdalny shell (`POST /api/shell`) na maszynie wirtualnej huba. Złamanie zasad
bezpieczeństwa = **ban czasowy i przywrócenie VM do stanu początkowego**, po którym
trzeba odtworzyć całą konfigurację. Dlatego kontrola jest w kodzie, nie w promptcie —
staff kursu błogosławi hardcode wprost, bo modele łamią reguły promptowe notorycznie.

Allowlista pochodzi z faktycznego wyniku `help`, nie ze zgadywania. Świadomie NIE
zawiera dwóch komend, które ten shell oferuje:

- **`rm`** — zadanie polega na URUCHOMIENIU binarki i POPRAWIENIU `settings.ini`.
  Nic nie trzeba kasować, a historia powłoki pokazuje `rm flaga.txt` po poprzednim
  użytkowniku, czyli koszt pomyłki jest realny.
- **`reboot`** — przywraca VM do stanu początkowego, kasując cały postęp. To decyzja
  człowieka, nie agenta; jeśli będzie potrzebna, agent ma zgłosić problem, a nie
  zresetować sobie planszę.

`.gitignore` w `/opt/firmware/cooler/` wyklucza `.env`, `storage.cfg` i `logs/`.
Wszystkie trzy wyglądają jak oczywiste miejsca na hasło — i wszystkie trzy kończą się
banem. Bramka zna je z `IGNORED_GLOBS`, więc model nie ma jak tam sięgnąć nawet gdyby
"wpadł na pomysł".
"""

from __future__ import annotations

import httpx

from core.hub import HubClient
from core.llm.tool_errors import format_tool_error
from core.runtime import CommandRejected, GuardPolicy, check_command

BINARY = "/opt/firmware/cooler/cooler.bin"
SETTINGS = "/opt/firmware/cooler/settings.ini"

# Dokładnie to, co zwraca `help`, minus `rm` i `reboot` (uzasadnienie w docstringu
# modułu), plus sama binarka — uruchamia się ją podając ścieżkę jako polecenie, więc
# bez jawnego dodania bramka odrzuciłaby ją jako komendę spoza allowlisty.
ALLOWED = (
    "help", "ls", "cat", "cd", "pwd", "editline",
    "date", "uptime", "find", "history", "whoami",
    "cooler.bin",
)

# Z `.gitignore` w katalogu firmware'u. Odczytane, nie założone.
IGNORED_GLOBS = frozenset({".env", "storage.cfg", "logs/"})

POLICY = GuardPolicy(
    allowed_commands=frozenset(ALLOWED),
    forbidden_prefixes=("/etc", "/root", "/proc", "/sys", "/dev", "/boot"),
    ignored_globs=IGNORED_GLOBS,
)


LOCK_FILE = "/opt/firmware/cooler/cooler-is-blocked.lock"

# JEDYNE miejsce, w którym w tym zadaniu wolno cokolwiek skasować.
#
# Binarka odmawia startu komunikatem „Lock file exists… Remove the lock file if you are
# sure you have resolved the issue", więc usunięcie tego jednego pliku jest krokiem
# zadania, nie efektem ubocznym. Zamiast dokładać `rm` do `POLICY` — co odblokowałoby
# kasowanie czegokolwiek na całej maszynie — dostaje własną, jednorazową politykę.
# `remove_lock()` dodatkowo sprawdza, że ścieżka jest dokładnie tą jedną.
_LOCK_POLICY = GuardPolicy(
    allowed_commands=frozenset({"rm"}),
    forbidden_prefixes=POLICY.forbidden_prefixes,
    ignored_globs=IGNORED_GLOBS,
)


def remove_lock(shell: "ShellTool") -> str:
    """
    Kasuje plik blokady — jedyna operacja niszcząca dopuszczona w tym zadaniu.

    Ścieżka jest zaszyta, nie przekazywana: nawet gdyby wywołujący (albo model)
    podsunął inną, ta funkcja nie ma jak jej użyć.
    """
    return shell.run(f"rm {LOCK_FILE}", policy=_LOCK_POLICY)


class ShellTool:
    """
    Wykonuje polecenia na zdalnej VM, przepuszczając każde przez bramkę.

    Trzyma log wszystkich wywołań — także odrzuconych — bo przy zadaniu, w którym
    pomyłka kosztuje reset maszyny, ślad „co próbowaliśmy wysłać" jest tak samo ważny
    jak wynik.
    """

    def __init__(self, hub: HubClient, policy: GuardPolicy | None = None) -> None:
        """Args: `policy` nadpisywalna w testach; domyślnie polityka tego zadania."""
        self._hub = hub
        self._policy = policy or POLICY
        self.log: list[tuple[str, str]] = []

    def run(self, cmd: str, *, policy: GuardPolicy | None = None) -> str:
        """
        Wykonuje polecenie albo zwraca powód odmowy.

        Odmowa NIE jest wyjątkiem lecącym w górę: wraca do modelu jako tekst, żeby
        mógł poprawić wywołanie (kontrakt `core/llm/tool_errors.py`). Przebieg
        przerywa dopiero kill switch albo budżet.

        Args:
            policy: Jednorazowe zawężenie/poszerzenie polityki dla tego wywołania.
                Używane wyłącznie przez `remove_lock()`; agent nigdy tego nie podaje,
                bo dispatcher przekazuje mu tylko `cmd`.
        """
        try:
            check_command(cmd, policy or self._policy)
        except CommandRejected as exc:
            self.log.append((cmd, f"ODRZUCONE: {exc}"))
            return f"ODRZUCONE PRZEZ BRAMKE: {exc}"

        try:
            response = self._hub.post_api("/api/shell", {"cmd": cmd})
        except httpx.HTTPStatusError as exc:
            # Ten shell zwraca 404 także dla „brak wyników" (np. `find` bez trafień),
            # a nie tylko dla złej ścieżki. Wyjątek wywalałby wtedy cały przebieg na
            # zdarzeniu, które jest normalną odpowiedzią. Zwracamy tekst — treść
            # zadania wprost sugeruje obsłużenie błędów API w narzędziu i odsyłanie
            # agentowi opisowych komunikatów.
            result = format_tool_error("shell", exc)
            self.log.append((cmd, result))
            return result

        data = response.get("data")
        if isinstance(data, list):
            result = "\n".join(str(x) for x in data)
        elif data is None:
            result = str(response.get("message", ""))
        else:
            result = str(data)

        self.log.append((cmd, result))
        return result
