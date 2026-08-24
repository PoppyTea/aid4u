"""
S05E03 — dostęp do „archiwum czasu" przez zdalny shell.

W odróżnieniu od `s03e02_firmware` transportem NIE jest `/api/shell`, tylko zwykłe
`POST /verify`: każda komenda to osobne zgłoszenie `{"task":"shellaccess",
"answer":{"cmd": …}}`, a hub odsyła stdout w ciele odpowiedzi. Flaga pojawia się
dopiero wtedy, gdy stdout komendy sam w sobie jest poprawnym JSON-em z odpowiedzią —
czyli ostatnie zgłoszenie niczym formalnie nie różni się od zgłoszeń eksploracyjnych.

## Dlaczego bramka poleceń mimo braku ryzyka bana

`s03e02` karał za dotknięcie zakazanego pliku banem i resetem VM; tutaj takiej kary
nie ma. Bramka zostaje, bo kosztuje jedną linijkę, a chroni przed pomyłką w drugą
stronę: polecenie sklejone z dwóch (`;`, `|`, `$(…)`) albo z rozwinięciem `~`/`$HOME`
wykonałoby się po stronie serwera inaczej, niż wygląda tutaj. Domyślna `GuardPolicy`
wystarcza bez zmian — zawiera już `ls`, `cat`, `head`, `tail`, `grep`, `find`, `wc`,
`file`, `stat`, `pwd` i `echo`, czyli komplet potrzebny w tym zadaniu.

Świadomie NIE dokładamy `jq`, mimo że podpowiedź z treści zadania go wymienia:
parsowanie robimy w Pythonie nad wynikiem `grep`, a `jq` bez potoku i tak niewiele
by wniósł — potoki bramka odrzuca z zasady.

## Limit rozmiaru wyniku (zmierzony, nieudokumentowany)

Hub odpowiada **HTTP 400** na polecenie, którego stdout jest zbyt duży —
`grep -n Rafał /data/time_logs.csv` (37 trafień) wywraca zapytanie, a `grep -c` na
tym samym wzorcu przechodzi. To nie jest błąd polecenia: `raise_for_status()` w
`HubClient` zamienia to w wyjątek, więc wygląda jak awaria. Konsekwencja dla
`solution.py`: każde zapytanie ma być wąskie z założenia (dokładna fraza, `-w`,
ograniczony kontekst), nigdy „pobierz wszystko i przefiltruj u siebie".
"""

from __future__ import annotations

import logfire

from core.hub import HubClient
from core.runtime import check_abort, check_command

HUB_TASK = "shellaccess"

# Kształt odpowiedzi ustalony sondą, nie z dokumentacji — treść zadania opisuje samo
# żądanie. `output` niesie stdout, reszta to fallback na wypadek innego kształtu przy
# błędzie (wtedy komunikat jest jedyną informacją, jaką mamy).
_STDOUT_FIELD = "output"
_FALLBACK_FIELDS = ("message", "msg", "answer")


class ArchiveShell:
    """
    Zdalna powłoka nad archiwum, opakowana w bramkę poleceń.

    Każde `run()` to jedno `POST /verify`. Zwraca stdout jako tekst; pełną
    odpowiedź huba (z ewentualną flagą) udostępnia `last_response`.
    """

    def __init__(self, hub: HubClient) -> None:
        """Zapamiętuje klienta huba i zeruje ślad po ostatniej odpowiedzi."""
        self._hub = hub
        self.last_response: dict = {}

    def run(self, cmd: str) -> str:
        """
        Wykonuje jedno polecenie na zdalnym serwerze i zwraca jego stdout.

        Args:
            cmd: Polecenie powłoki. Przechodzi przez `check_command()` PRZED
                wysłaniem — odrzucenie podnosi `CommandRejected`, nie wysyła nic.

        Returns:
            Stdout polecenia jako tekst (pusty string, gdy hub nic nie odesłał).
        """
        check_abort()
        check_command(cmd)
        logfire.info("Archive shell command", cmd=cmd)

        self.last_response = self._hub.submit(HUB_TASK, {"cmd": cmd})
        return extract_output(self.last_response)


def extract_output(response: dict) -> str:
    """
    Wyciąga stdout polecenia z odpowiedzi huba.

    Osobna funkcja, a nie metoda, żeby dało się ją przetestować bez sieci i bez
    budowania `HubClient` (który przy konstrukcji sięga po klucz API).
    """
    # Pusty `output` jest PRAWIDŁOWYM wynikiem, nie brakiem wyniku: `grep` bez trafień
    # zwraca dokładnie to. Gdyby pusty string spadał do fallbacku, polecenie bez trafień
    # raportowałoby `"Command executed."` jako swój stdout — czyli „nic nie znalazłem"
    # wyglądałoby jak „coś znalazłem". Stąd `output` sprawdzany osobno i po TYPIE,
    # nie po prawdziwości.
    stdout = response.get(_STDOUT_FIELD)
    if isinstance(stdout, str):
        return stdout

    for key in _FALLBACK_FIELDS:
        value = response.get(key)
        if isinstance(value, str) and value:
            return value
    return ""
