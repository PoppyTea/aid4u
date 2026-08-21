# s03e02_firmware Module

## Purpose
Uruchomienie sterownika chłodzenia (`/opt/firmware/cooler/cooler.bin`) na zdalnej VM
przez okrojony shell (`POST /api/shell`), zdobycie kodu `ECCS-…`. **Zero LLM.**

**Rozwiązane (2026-08-20)** — flaga `{FLG:CANTTOUCHTHIS}`, koszt $0.00, **domyka
Sezon 3 (5/5)**.

## Ownership
- `shell.py`: narzędzie powłoki + polityka bramki. Allowlista pochodzi z faktycznego
  wyniku `help`, nie ze zgadywania.
- `solution.py`: `@task("s03e02", hub_name="firmware")` — deterministyczna sekwencja.
- `doc/`: treść zadania i fabuła, materiał referencyjny.
- Brak danych statycznych — cały stan żyje na zdalnej VM.

## Local Contracts
- Odpowiedź: `{"confirmation": "ECCS-…"}` (40 znaków hex), nie goły string.
- **Binarkę uruchamia się podając ŚCIEŻKĘ jako polecenie** (`/opt/…/cooler.bin <hasło>`),
  więc `cooler.bin` musi być jawnie na allowliście — inaczej bramka odrzuci ją jako
  komendę spoza zbioru.
- **Kolejność wymuszona przez komunikaty binarki:** najpierw `settings.ini`, dopiero
  potem zdjęcie blokady („Remove the lock file **if you are sure you have resolved the
  issue**"). Odwrotnie zostawiłoby maszynę odblokowaną z zepsutą konfiguracją.
- `editline <plik> <nr-linii> <treść>` to jedyny sposób edycji — nie ma `sed`, `echo >`
  ani niczego standardowego.

## Pułapki (zweryfikowane na żywo)
- 🔴 **`.gitignore` w katalogu firmware'u wyklucza `.env`, `storage.cfg` i `logs/`.**
  Wszystkie trzy wyglądają jak oczywiste miejsce na hasło; dotknięcie któregokolwiek
  kończy się banem i przywróceniem VM. Hasło leży w `/home/operator/notes/pass.txt`.
- 🔴 **Historia powłoki to zamierzona ścieżka podpowiedzi** — pokazuje próby hasła,
  flagę `-D` i `cat error.log` (czyli ruch, który dziś kończy się banem, bo `logs/`
  jest w `.gitignore`).
- **Blokada, nie złe hasło.** `cooler.bin admin1` nie zwraca błędu uwierzytelnienia,
  tylko `Lock file exists…`. Łatwo to pomylić z „hasło nie działa" i zacząć zgadywać.
- `find` bez trafień zwraca **404**, nie pustą listę — narzędzie musi to znieść, bo to
  normalna odpowiedź, nie awaria.
- `.git/` w katalogu firmware'u to żart (`🍕+🍍=❤️`), nie repozytorium.

## Work Guidance
- **`rm` i `reboot` są POZA allowlistą zadania.** `rm` wchodzi wyłącznie przez
  `remove_lock()`, z własną, jednorazową polityką i zaszytą ścieżką — poszerzenie
  `POLICY` odblokowałoby kasowanie czegokolwiek na maszynie. `reboot` kasuje cały
  postęp, więc jest decyzją człowieka, nie agenta.
- `_fix_settings()` porównuje linie przed zapisem, więc przebieg jest **idempotentny** —
  powtórka po częściowej awarii nie nadpisuje poprawnych linii.
- **Dlaczego bez pętli agentowej:** po sondzie `help` przestrzeń problemu okazała się
  mała i w pełni deterministyczna (trzy linie, jeden lock, jedno hasło). Pętla dokładałaby
  koszt i niedeterminizm, żeby model odkrył to, co już wiadomo — a to epizod
  z udokumentowanym rozrzutem kosztu ×140. Osłony (`command_guard`, throttle,
  `tool_errors`) pracują tak samo w trybie deterministycznym.

## Verification
- `uv run pytest tasks/s03e02_firmware/` — 37 testów, zero sieci. W tym
  `TestAgentDestrukcyjny`: 18 poleceń niszczących przechodzi przez PRAWDZIWE narzędzie
  i **żadne nie dociera do backendu**.
- `uv run run.py solve s03e02 --dry-run` — pełna sekwencja bez zgłoszenia.
- Flaga z huba to ostateczna weryfikacja.

## Child DOX Index
- None.
