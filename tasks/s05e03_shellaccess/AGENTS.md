# s05e03_shellaccess Module

## Purpose
Namierzenie daty, miasta i współrzędnych spotkania z Rafałem w „archiwum czasu" na
zdalnym serwerze (`/data`), przez okrojony shell wystawiony na `POST /verify`.
**Zero LLM.**

**Rozwiązane (2026-08-24)** — flaga `{FLG:HUGEFILE}`, za pierwszym podejściem, koszt
$0.00, cztery zapytania do huba (trzy eksploracyjne + zgłoszenie). Pierwsza flaga S05.

## Ownership
- `archive.py`: `ArchiveShell` — jedno polecenie = jedno `POST /verify`; bramka poleceń
  i wyciąganie stdout z odpowiedzi.
- `solution.py`: `@task("s05e03", hub_name="shellaccess")` — deterministyczny łańcuch
  trzech `grep`-ów, arytmetyka daty i złożenie polecenia `echo`.
- `probe.py`: sonda eksploracyjna (dowolnie wiele poleceń w jednym przebiegu). Została
  w repo, bo bez niej regexy w `solution.py` wyglądają na wzięte znikąd.
- `test_solution.py`: 16 testów offline — parser, arytmetyka daty, składanie `echo`.
- `doc/`: treść zadania i fabuła, materiał referencyjny.
- Brak danych statycznych — całe wejście żyje na zdalnym serwerze.

## Local Contracts
- **Transportem jest `/verify`, nie `/api/shell`** (inaczej niż w `s03e02_firmware`):
  `{"task":"shellaccess","answer":{"cmd": …}}`, odpowiedź w polu `output`,
  `{"code":100,"message":"Command executed."}` przy powodzeniu. Zgłoszenie eksploracyjne
  i zgłoszenie finalne są nierozróżnialne — flaga pada, gdy **stdout polecenia** jest
  poprawnym JSON-em. Stąd `solve()` zwraca polecenie, a wysyła je dopiero
  `BaseTask._submit()`: jedno wysłanie, bez obejścia szablonu.
- **Domyślna `GuardPolicy` wystarcza bez zmian.** Zawiera już `grep`, `echo`, `ls`,
  `cat`, `find`, `head`, `tail`, `wc`, `file`, `stat`, `pwd`. `jq` (z podpowiedzi
  zadania) świadomie NIE dokładany — bez potoku niewiele wnosi, a potoki bramka
  odrzuca z zasady.
- Współrzędne przechodzą przez cały przepływ jako **tekst**, nigdy `float` —
  `18.968774` ma dotrzeć do walidatora dokładnie tak, nie jako `18.968773999999998`.
- `build_echo_command()` waliduje własny wynik trzy razy (brak apostrofu, `json.loads`,
  `check_command`) i nie ma ścieżki alternatywnej wobec `echo`.

## Struktura archiwum (ustalona sondą — treść zadania jej nie podaje)
```
/data/time_logs.csv    date;description;location;place   4541 wierszy
/data/locations.json   [{location_id, name}]
/data/gps.json         [{latitude, longitude, type, location_id, entry_id}]
```
Klucze łączące **mają inne nazwy po obu stronach**: kolumna `location` → `location_id`,
kolumna `place` → `entry_id`. To jedyna realna zagwozdka w tym zadaniu.

Ścieżka rozwiązania: `grep ciało` (dokładnie jedno trafienie w całym archiwum) →
`2024-11-13;W jaskini znaleziono ciało mężczyzny…;219;954634` → `location_id 219` =
Grudziądz → `entry_id 954634` = `53.432303 / 18.968774`, typ `jaskinia`.

## Pułapki (zweryfikowane na żywo)
- 🔴 **Hub zwraca HTTP 400 przy zbyt dużym stdout.** `grep -n Rafał /data/time_logs.csv`
  (37 trafień) wywraca zapytanie, `grep -c` na tym samym wzorcu przechodzi.
  `raise_for_status()` zamienia to w wyjątek, więc wygląda jak awaria huba, a nie jak
  limit. Każde zapytanie musi być wąskie z założenia.
- 🔴 **`printf` psuje walidator** — przy poprawnych danych zwracał ucięte `{city:`.
  Wyłącznie `echo`.
- 🔴 **Data ma być o dzień WCZEŚNIEJSZA** niż zdarzenie. W archiwum nie ma o tym śladu;
  podpowiedź siedzi zakodowana base64 w treści zadania i wielu jej nie zdekodowało.
- 🟡 **Zdalny shell zjada cudzysłowy przed podziałem na tokeny**, więc wzorzec ze spacją
  (`"location_id": 219`) rozpada się na dwa argumenty i `grep` traktuje drugi jako plik
  (`grep: 219,: No such file or directory`). Wzorce muszą być jednym tokenem — stąd
  `-w <liczba>` zamiast dopasowania do pełnej pary klucz-wartość.
- 🟡 **Fabuła myli:** zapowiada „prosty plik tekstowy, nie bazę danych", a `/data` trzyma
  trzy pliki połączone kluczami. Sonda przed założeniami.
- 🟡 **Nazwy miast są w `locations.json` escape'owane** (`Grudziądz`) — dekodować
  parserem JSON, nie ręcznie.
- Sanity-check: miejsce jest realne. `53.432303 / 18.968774` wypada pod Grudziądzem,
  a typ punktu to `jaskinia` — zgodnie z opisem zdarzenia. Współrzędne spoza Polski
  oznaczałyby, że parser trafił w zły rekord.

## Work Guidance
- **Dlaczego bez pętli agentowej:** archiwum jest relacyjne i deterministyczne, a jedyne
  zdarzenie pasujące do frazy jest jedno. Pętla odkrywałaby to, co widać po czterech
  `grep`-ach — za cenę kilkudziesięciu tur ($0.11 i 17 minut w raportach społeczności).
  Dodatkowo omija to udokumentowany problem: modele Anthropic **odmawiają** pomocy
  w „szukaniu ciała", powołując się na politykę użytkowania. Ścieżka deterministyczna
  nie wykonuje żadnego wywołania providera, więc problem nie występuje.
- Eksploracja: `uv run python -m tasks.s05e03_shellaccess.probe '<polecenie>' [...]`.

## Verification
- `uv run pytest tasks/s05e03_shellaccess/` — 16 testów, zero sieci.
- `uv run run.py solve s05e03 --dry-run` — pełna eksploracja na żywo, finalne polecenie
  wypisane zamiast wysłania.
- Flaga z huba to ostateczna weryfikacja.

## Child DOX Index
- None.
