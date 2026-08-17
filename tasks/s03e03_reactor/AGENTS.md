# s03e03_reactor Module

## Purpose
Robot 7×5 omija ruchome bloki reaktora i dociera do celu — **deterministycznie,
zero LLM** (rekomendacja `tasks/s03/requirements/s03e03.md` +
`doc/community_notes.md`: najłatwiejszy epizod sezonu, "kilku uczestników zrobiło
to czystym BFS w 8-12 ruchach"). Receding-horizon BFS: obserwuj rzeczywisty stan
planszy z API → BFS pełnego planu → weź TYLKO pierwszy ruch → guardrail → wyślij →
powtórz od obserwacji. Samonaprawialne wobec błędów modelu fizyki, bo plan liczy
się od stanu ZAOBSERWOWANEGO, nie symulowanego.

**Rozwiązane (2026-08-17)** — flaga `{FLG:INSTALLED}` w `.flags.json`, 9 ruchów,
0 zgnieceń, koszt $0.00 (zero wywołań LLM).

## Ownership
- `solution.py`: `ReactorTask` — `@task("s03e03", hub_name="reactor")`. Pętla
  receding-horizon + protokół HTTP (`_send()`) + nadpisany `_submit()` (R6).
- `reactor.py`: czysta logika, zero I/O — model fizyki bloków (`Block.advance()`),
  sprawdzanie kolizji (`apply_command()`), BFS (`solve_bfs()`), parser odpowiedzi
  API (`state_from_api()`). Testowalne offline.
- `scripts/probe_api.py`: sonda jednorazowa, którą ustalono format protokołu —
  zostaje w repo jako dokumentacja wykonywalna, nie do uruchamiania rutynowo.
- `doc/`: treść zadania (`zadanie.md` — z dopiskiem o formacie API ustalonym
  empirycznie, bo lekcja go nie podaje), `fabula.md`, destylat community
  (`community_notes.md`) — materiał referencyjny, nieużywany w runtime.
- Dane wejściowe: **brak statycznych** — cała gra idzie przez żywe `POST /verify`,
  zaczynając od komendy `start`. Surowe odpowiedzi z sondy zapisane w
  `data/input/s03e03_reactor/` (regresyjny fixture dla `test_solution.py`, nie
  źródło danych do rozwiązania).

## Local Contracts
- **Format `answer` USTALONY EMPIRYCZNIE, nie z treści lekcji**: musi być obiektem
  `{"command": "start"|"reset"|"left"|"right"|"wait"}`, nie gołym stringiem — hub
  zwraca `code: -21`/`-22`/`-990` na inne warianty. Lekcja S03E03 nie podaje
  żadnego przykładu JSON (potwierdzone dwukrotnym zapytaniem do NotebookLM).
- **Kolizja sprawdzana PO przesunięciu bloków, nie przed** — patrz docstring
  `reactor.py` i testy `TestApplyCommandCollision` w `test_solution.py`. To
  dotyczy też `wait`: stanie w miejscu nie chroni przed blokiem wchodzącym w
  Twoją kolumnę w tym samym ticku.
- **Kontrakt pojedynczej submisji (R6)**: `solve()` woła `hub.submit()`
  wielokrotnie (jak `s01e05_railway`), więc `_submit()` jest nadpisane — nigdy nie
  wysyła listy ruchów jako osobnej "odpowiedzi", zwraca `_captured_flag` złapaną
  po drodze. Jeśli robot dotrze do celu bez flagi w żadnej odpowiedzi po drodze,
  `_submit()` rzuca `RuntimeError` zamiast cichego `None` — sygnał do ręcznego
  sprawdzenia ostatniej odpowiedzi, nie do zgadywania.
- **`except httpx.HTTPStatusError` zawężony do 409/`-920` (R7)** w `_send()` —
  reszta propaguje się. Zgniecenie to udokumentowany, normalny krok protokołu tej
  gry, nie błąd.
- **`--dry-run` wysyła jeden realny `start`** (odczyt stanu planszy — gra nie ma
  ŻADNYCH statycznych danych, to jedyny sposób zbudowania czegokolwiek do
  pokazania), liczy jeden pełny BFS, **nie wykonuje żadnego z zaplanowanych
  ruchów**. To podgląd JEDNEGO planu, nie symulacja pętli receding-horizon
  (ta koryguje się co tick na podstawie prawdziwej odpowiedzi huba).

## Work Guidance
- Zmieniasz `reactor.py`? Uruchom najpierw `TestRegressionAgainstLiveProbe` —
  jeśli fizyka bloków się zmieni w hubie, ten test to złapie niezależnie od
  testów syntetycznych.
- `_MAX_COMMANDS = 60` i `_MAX_CRUSH_RETRIES = 3` w `solution.py` to bezpieczniki,
  nie oczekiwane wartości robocze — realny przebieg kończy się w 8-15 ruchach,
  0 zgnieceń przy poprawnym modelu fizyki (guardrail wyłapuje rozjazdy PRZED
  wysłaniem, nie po).

## Verification
- `uv run pytest tasks/s03e03_reactor/` — 17 testów, zero sieci (w tym regresja
  wobec prawdziwych fixtures z sondy).
- `uv run run.py solve s03e03 --dry-run` — jeden `start` + podgląd planu BFS, bez
  wykonania ruchów.
- Zadanie zwraca flagę z huba — to ostateczna weryfikacja, nie zielone testy.
  Potwierdzone na żywo 2026-08-17: `{FLG:INSTALLED}`, 9 ruchów, 0 zgnieceń.
- `uv run pyrefly check tasks/s03e03_reactor/` — zielone.

## Child DOX Index
- None.
