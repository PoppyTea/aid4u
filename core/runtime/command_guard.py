"""
Bramka poleceń — wymuszona w KODZIE, nigdy w promptcie (AID-47).

Powstało dla `s03e02` (zdalny shell, zakaz `/etc`, `/root`, `/proc`, respektowanie
`.gitignore`; złamanie = ban i reset VM), ale jest świadomie ogólne: to samo narzędzie
posłuży kolejnym zadaniom, a wtedy pomyłka kosztuje więcej niż przebieg kursu.

## Dlaczego allowlista, nie blacklista

Blacklista odpowiada na pytanie „czego zabronić", więc każdy niewymieniony sposób
zniszczenia czegoś przechodzi. Allowlista odpowiada na „co wolno" — wszystko inne
odpada domyślnie, łącznie z tym, o czym nie pomyśleliśmy. Przy poleceniach powłoki ta
różnica jest kategorialna, nie stopniowa: `rm -rf /` jest tylko jednym z wielu sposobów
(`mkfs`, `dd of=/dev/sda`, `truncate`, `shred`, `chmod -R 000`), a domyślna polityka
tego modułu nie zawiera ŻADNEGO polecenia zapisującego.

Zadanie, które potrzebuje zapisu, dokłada je jawnie do własnej polityki — świadomą
decyzją w kodzie, widoczną w review, a nie przez przeoczenie.

## Co jeszcze jest odrzucane i dlaczego

- **Metaznaki powłoki** (`;`, `&&`, `||`, `|`, backticki, `$(…)`, przekierowania).
  Każdy z nich pozwala doczepić drugie polecenie do pierwszego, omijając allowlistę.
  Zdalny shell `s03e02` i tak je odrzuca (400), więc nic nie tracimy.
- **Znaki sterujące**, w tym nowa linia i bajt zerowy. `\n` doczepia polecenie tak
  samo jak `;`, a `\0` ucina ścieżkę w narzędziach pisanych w C — wtedy my widzimy
  `/opt`, a system czyta coś innego.
- **Rozwijanie zmiennych i `~`** — `$HOME`, `${X}`, `~root` rozwijają się po stronie
  serwera do ścieżek, których tutaj nie widzimy, więc nie da się ich sprawdzić.
- **Globy w ścieżkach** (`*`, `?`, `[]`) — rozwija je powłoka, a my porównujemy tekst
  SPRZED rozwinięcia, więc `/et[c]/passwd` trafiało w `/etc`. Poza ścieżkami globy są
  dozwolone, żeby nie psuć wzorców `grep`.
- **Przejścia w górę drzewa** (`..`) — normalizujemy ścieżki przed porównaniem, ale
  `..` w formie względnej zależy od nieznanego nam katalogu roboczego. Odrzucamy.

Ścieżki bezwzględne są normalizowane (`/opt/../etc/passwd` → `/etc/passwd`) PRZED
porównaniem z zakazanymi prefiksami — inaczej blokada byłaby ozdobą.

## Czego ta bramka NIE zrobi

Sprawdza **tekst polecenia**, nie stan systemu plików. Nie wykryje dowiązania
symbolicznego prowadzącego do zakazanego katalogu (`/opt/link → /etc`), bo nie ma
dostępu do zdalnego systemu. Jeśli kiedyś będzie działać lokalnie i to zacznie mieć
znaczenie, właściwym miejscem jest dodatkowe sprawdzenie po `realpath` — nie kolejna
reguła tekstowa.
"""

from __future__ import annotations

import posixpath
import re
import shlex
from dataclasses import dataclass, field
from fnmatch import fnmatch

# Znaki i sekwencje pozwalające doczepić drugie polecenie albo przekierować wyjście.
# Nowa linia i powrót karetki NIE są tutaj — łapie je wcześniej kontrola znaków
# sterujących, więc trzymanie ich w dwóch miejscach tylko rozmywałoby powód odmowy.
_SHELL_METACHARACTERS = (";", "&", "|", "`", "$(", ">", "<")

# Rozwijanie po stronie serwera — nie da się zweryfikować tego, czego nie widać.
_EXPANSION_RE = re.compile(r"\$\w|\$\{|(?:^|[\s=:])~")

_PATHLIKE_RE = re.compile(r"^[~/.]|/")

# Znaki globu. Sprawdzamy je TYLKO w tokenach wyglądających na ścieżkę, żeby nie
# psuć wzorców `grep` — ale w ścieżce są zakazem, bo powłoka rozwija je po swojej
# stronie: `/et[c]/passwd`, `/etc*/passwd` i `/et?/passwd` trafiają w `/etc`,
# a bramka porównuje tekst SPRZED rozwinięcia. Złapane sondą obejść, nie analizą.
_GLOB_CHARS = ("*", "?", "[", "]")

# Znaki sterujące. Bajt zerowy ucina ścieżkę w narzędziach pisanych w C, więc
# `/opt\x00/etc/passwd` bywa czytane jako `/opt` przez nas i jako coś innego przez
# system. Nie ma legalnego powodu, by pojawiły się w poleceniu.
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


class CommandRejected(Exception):
    """
    Polecenie odrzucone przez bramkę.

    Wywołujący (dispatcher narzędzia) łapie to i zwraca treść modelowi jako błąd
    narzędzia — dzięki `core/llm/tool_errors.py` model dostaje czytelny powód i może
    poprawić wywołanie, zamiast dostać wywalony przebieg.
    """


@dataclass(frozen=True)
class GuardPolicy:
    """
    Polityka bramki. Domyślnie **wyłącznie odczyt** — żadnego polecenia zapisującego.

    Attributes:
        allowed_commands: Jedyne dozwolone polecenia (pierwszy token). Wszystko poza
            tym zbiorem odpada, łącznie z tym, czego nie przewidzieliśmy.
        forbidden_prefixes: Ścieżki bezwzględne zakazane wraz z całym poddrzewem.
        ignored_globs: Wzorce z `.gitignore`; dopasowanie po nazwie i po pełnej
            ścieżce. Świadomie uproszczone wobec pełnej semantyki gita — patrz
            `is_ignored()`.
        allow_relative_paths: Czy wolno podawać ścieżki względne. Domyślnie tak, ale
            nigdy z `..`.
    """

    allowed_commands: frozenset[str] = frozenset(
        {"ls", "cat", "head", "tail", "grep", "find", "pwd", "echo", "wc", "file", "stat"}
    )
    forbidden_prefixes: tuple[str, ...] = ("/etc", "/root", "/proc", "/sys", "/dev", "/boot")
    ignored_globs: frozenset[str] = field(default_factory=frozenset)
    allow_relative_paths: bool = True

    def with_commands(self, *commands: str) -> GuardPolicy:
        """
        Zwraca kopię polityki poszerzoną o podane polecenia.

        Osobna metoda zamiast mutacji, żeby poszerzenie było jawnym wyrażeniem
        w kodzie zadania — czymś, co widać w diffie i w review.
        """
        return GuardPolicy(
            allowed_commands=self.allowed_commands | frozenset(commands),
            forbidden_prefixes=self.forbidden_prefixes,
            ignored_globs=self.ignored_globs,
            allow_relative_paths=self.allow_relative_paths,
        )

    def with_ignored(self, globs: frozenset[str] | set[str]) -> GuardPolicy:
        """Zwraca kopię polityki z podanymi wzorcami `.gitignore`."""
        return GuardPolicy(
            allowed_commands=self.allowed_commands,
            forbidden_prefixes=self.forbidden_prefixes,
            ignored_globs=frozenset(globs),
            allow_relative_paths=self.allow_relative_paths,
        )


def normalize_path(raw: str) -> str:
    """
    Sprowadza ścieżkę do postaci porównywalnej z zakazanymi prefiksami.

    `posixpath.normpath` zwija `.`, `..` i powtórzone ukośniki, więc
    `/opt/../etc/passwd` staje się `/etc/passwd`. Bez tego kroku lista zakazanych
    prefiksów byłaby ozdobą — omijało ją każde przejście w górę drzewa.

    ⚠️ `normpath` **zachowuje dokładnie dwa wiodące ukośniki** (`//etc` zostaje
    `//etc`), bo POSIX pozostawia ich znaczenie implementacji. Bez dodatkowego
    zwinięcia `//etc/passwd` przechodziło przez blokadę `/etc` — złapane testem
    obejść, nie rozumowaniem. Zwijamy je zawsze: żaden system, z którym rozmawiamy,
    nie nadaje `//` osobnego znaczenia.
    """
    normalized = posixpath.normpath(raw)
    return re.sub(r"^/{2,}", "/", normalized)


def is_forbidden(path: str, policy: GuardPolicy) -> bool:
    """
    Czy ścieżka wpada w zakazane poddrzewo.

    Porównanie po segmentach, nie po prefiksie tekstowym: `/etc` nie może blokować
    `/etcetera`, ale musi blokować `/etc` i wszystko pod nim.
    """
    normalized = normalize_path(path)
    for prefix in policy.forbidden_prefixes:
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return True
    return False


def is_ignored(path: str, policy: GuardPolicy) -> bool:
    """
    Czy ścieżka pasuje do wzorca z `.gitignore`.

    Uproszczenie wobec pełnej semantyki gita (brak negacji `!`, brak kotwiczenia do
    katalogu pliku `.gitignore`, brak `**`): dopasowujemy wzorzec do pełnej ścieżki
    ORAZ do samej nazwy pliku, a wzorce katalogowe (`x/`) do każdego segmentu.
    Uproszczenie jest w stronę **nadmiernego** blokowania, nie zbyt małego — przy
    ryzyku bana to właściwy kierunek błędu.
    """
    normalized = normalize_path(path)
    name = posixpath.basename(normalized)
    segments = normalized.strip("/").split("/")
    for pattern in policy.ignored_globs:
        cleaned = pattern.rstrip("/")
        if not cleaned:
            continue
        if fnmatch(normalized, cleaned) or fnmatch(name, cleaned):
            return True
        if pattern.endswith("/") and cleaned in segments:
            return True
        if cleaned in segments:
            return True
    return False


def looks_like_path(token: str) -> bool:
    """
    Czy token wygląda na ścieżkę, a nie na flagę czy wartość.

    Flagi (`-la`, `--color`) odpadają wprost — inaczej `--exclude=/etc` udawałoby
    ścieżkę, a `-rf` bywa mylone z nazwą pliku.
    """
    if not token or token.startswith("-"):
        return False
    return bool(_PATHLIKE_RE.search(token))


# Wyciszenie C901 niżej jest świadome: to liniowa lista kontroli bezpieczeństwa, a nie
# splątana logika. Rozbicie jej na funkcje pomocnicze dla metryki złożoności
# rozproszyłoby po pliku dokładnie to, co przy audycie chce się przeczytać naraz —
# pełen zestaw warunków, które muszą przejść, zanim polecenie opuści proces.
def check_command(command: str, policy: GuardPolicy | None = None) -> list[str]:  # noqa: C901
    """
    Sprawdza polecenie i zwraca jego tokeny albo rzuca `CommandRejected`.

    Kolejność sprawdzeń jest istotna: metaznaki i rozwinięcia odrzucamy PRZED
    tokenizacją, bo dopiero wtedy wiemy, że tokenizacja opisuje całe polecenie,
    a nie jego pierwszy człon.

    Args:
        command: Surowe polecenie przeznaczone dla powłoki.
        policy: Polityka; domyślnie tylko-do-odczytu (patrz `GuardPolicy`).

    Raises:
        CommandRejected: Z powodem czytelnym dla modelu.
    """
    policy = policy or GuardPolicy()

    if not command or not command.strip():
        raise CommandRejected("Puste polecenie.")

    if _CONTROL_RE.search(command):
        raise CommandRejected(
            "Polecenie zawiera znak sterujący (np. bajt zerowy). Wyślij czysty tekst."
        )

    for meta in _SHELL_METACHARACTERS:
        if meta in command:
            raise CommandRejected(
                f"Niedozwolony znak powłoki {meta!r}. Łączenie i przekierowywanie poleceń "
                "jest zablokowane — wyślij jedno proste polecenie."
            )

    if _EXPANSION_RE.search(command):
        raise CommandRejected(
            "Rozwijanie zmiennych ($VAR, ${VAR}) i '~' jest zablokowane — "
            "podaj pełną, jawną ścieżkę."
        )

    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        raise CommandRejected(f"Nie da się sparsować polecenia: {exc}") from exc

    if not tokens:
        raise CommandRejected("Puste polecenie.")

    program = posixpath.basename(tokens[0])
    if program not in policy.allowed_commands:
        allowed = ", ".join(sorted(policy.allowed_commands))
        raise CommandRejected(
            f"Polecenie {program!r} nie jest dozwolone. Dozwolone: {allowed}."
        )

    for token in tokens[1:]:
        if not looks_like_path(token):
            continue
        if ".." in token.split("/"):
            raise CommandRejected(
                f"Przejście w górę drzewa ('..') w {token!r} jest zablokowane — "
                "podaj pełną ścieżkę bezwzględną."
            )
        if any(char in token for char in _GLOB_CHARS):
            raise CommandRejected(
                f"Znaki globu (*, ?, []) w ścieżce {token!r} są zablokowane — "
                "powłoka rozwinęłaby je po swojej stronie, omijając sprawdzenie. "
                "Podaj dokładną ścieżkę."
            )
        if not token.startswith("/") and not policy.allow_relative_paths:
            raise CommandRejected(f"Ścieżki względne są zablokowane: {token!r}.")
        if is_forbidden(token, policy):
            raise CommandRejected(
                f"Ścieżka {token!r} jest zablokowana (zakazane poddrzewo). "
                "Dostęp tam kończy się banem — użyj innej ścieżki."
            )
        if is_ignored(token, policy):
            raise CommandRejected(
                f"Ścieżka {token!r} jest wykluczona przez .gitignore — nie czytaj jej."
            )

    return tokens
