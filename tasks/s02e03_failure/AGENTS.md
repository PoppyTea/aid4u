# s02e03_failure Module

## Purpose
Kompresja ogromnego pliku logów z awarii elektrowni do skondensowanej wersji
tekstowej (jedna linia = jedno zdarzenie), mieszczącej się w limicie 1500 tokenów i
zawierającej tylko informacje istotne dla analizy przyczyny awarii (zasilanie,
chłodzenie, pompy wodne, oprogramowanie, inne podzespoły). Weryfikacja jest
iteracyjna — hub/"technicy" zwracają feedback, co poprawić.

**Rozwiązane (2026-08-07)** — flaga `{FLG:SQUASHIT}` w `.flags.json`, model
`claude-haiku-4-5-20251001`, ~5 rund weryfikacji (mieszanka przekroczeń tokenów
i brakujących podzespołów, oba typy feedbacku obsłużone automatycznie).

## Ownership
- `solution.py`: `FailureTask` — `@task("s02e03", hub_name="failure")`.
- Dane wejściowe: `GET /data/{apikey}/failure.log` przez `hub.get_data()`
  (**`.log`, nie `.json`** — potwierdzone live 2026-08-07, wcześniejsza
  niejednoznaczność rozstrzygnięta). 248 KB, zwykły tekst — jedna linia logu na
  zdarzenie (`[YYYY-MM-DD HH:MM:SS] [LEVEL] opis...`). Live snapshot: 2137
  linii, 90 unikalnych opisów, 55 nie-INFO, 7 podzespołów (ECCS8, WTRPMP,
  WTANK07, FIRMWARE, STMTURB12, PWR01, WSTPOOL2) — treść generowana per
  sesja/apikey, więc te liczby mogą się różnić przy kolejnym pobraniu.
- `doc/`: treść zadania (`zadanie.md`, `fabula.md`) + destylat cheese-strategies
  z komentarzy kursu (`community_notes.md`) — materiał referencyjny, nieużywany
  w runtime.

## Local Contracts
- Odpowiedź to POST `/verify` z `answer.logs` = string, wiersze oddzielone `\n`,
  jeden wiersz = jedno zdarzenie. Zachować: data `YYYY-MM-DD`, godzina `HH:MM`/`H:MM`,
  poziom ważności, identyfikator podzespołu.
- **Limit tokenów jest `< 1500`, nie `≤ 1500`** — potwierdzony live przykład
  odrzucenia przy dokładnie 1500/1500 (100%). `solution.py` celuje w
  `_TARGET_TOKEN_BUDGET = 1400`.
- **`/verify` zwraca HTTP 400 (nie 200) dla niekompletnej odpowiedzi** —
  potwierdzone live 2026-08-07: `{"code": -960, "message": "..."}`. To normalny
  krok iteracji, nie błąd — `HubClient.submit()` rzuca na to
  `httpx.HTTPStatusError` (bo `>= 400` → `raise_for_status()`), więc
  `FailureTask._verify()` łapie ten wyjątek i czyta `exc.response.json()` jak
  zwykłą odpowiedź z feedbackiem.
- Feedback z huba wskazuje brakujący/niejasny podzespół po nazwie ("...unable to
  determine what happened to device xxxxx") — `solve()` sprawdza czy nazwa
  jednego ze znanych podzespołów jest podciągiem wiadomości, i jeśli tak,
  przywraca dla niego pełny nieskompresowany opis (`_restore_component`).

## Work Guidance
- **LLM nie trzyma jawnego budżetu tokenów na wpis, nawet gdy się o to prosi
  wprost** — potwierdzone empirycznie 2026-08-07 (Haiku): kolejne rundy z coraz
  ostrzejszym "skróć mocniej" zbiegały bardzo wolno (~1870 → 1590 → 1511
  tokenów, wciąż nad limitem). Nie płacić za więcej rund w nadziei na trafienie
  — jedna runda kompresji LLM + deterministyczne przycięcie na poziomie
  tokenów tiktoken jako gwarancja (patrz `_hard_trim` w `solution.py`).
- Realne dane (2026-08-07) okazały się dużo mniejsze niż zakładał pierwotny
  plan poniżej — dedup+filtr kodem (bez LLM) sam sprowadza 2137 linii do 55.
  To już mały zestaw, mieści się w jednym wywołaniu LLM bez potrzeby
  architektury z narzędziem do przeszukiwania logu czy subagentem. Zostawiamy
  oryginalny plan społeczności niżej jako punkt odniesienia, gdyby kolejna
  sesja/apikey dała dużo większy plik:
  1. Pobierz `failure.log`.
  2. Deduplikuj programistycznie (ten sam opis, różny timestamp → zostaw jeden).
  3. Odfiltruj `[INFO]` programistycznie (regex/kod, nie LLM) — to szum.
  4. Dopiero to co zostaje idzie do modelu do kompresji opisów.
  5. Zlicz tokeny lokalnie przed wysyłką, wyślij, sparsuj feedback, powtórz aż flaga.
- "Najważniejsze zdarzenia" ≠ tylko rdzeń reaktora — trzeba przejść wszystkie
  zgłoszone przez feedback podzespoły (np. `ECCS8`), nie tylko oczywiste.

## Verification
- Zadanie zwraca flagę z huba — to ostateczna weryfikacja (potwierdzone live
  2026-08-07, `{FLG:SQUASHIT}`, `claude-haiku-4-5-20251001`, ~5 rund).
- `uv run run.py solve s02e03 --dry-run --model <model>` — sprawdza
  fetch→dedup→filtr→kompresję→budżet tokenów bez wysyłki do huba (ale LLM
  jest wywoływany naprawdę — kosztuje realne zapytanie).
- `uv run --with ruff ruff check tasks/s02e03_failure/`, `uv run pyrefly check
  tasks/s02e03_failure/`, `uv run basedpyright tasks/s02e03_failure/` — zielone
  przed każdym commitem kodu w tym folderze.

## Child DOX Index
- None.
