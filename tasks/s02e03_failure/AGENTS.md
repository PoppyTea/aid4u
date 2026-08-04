# s02e03_failure Module

## Purpose
Kompresja ogromnego pliku logów z awarii elektrowni do skondensowanej wersji
tekstowej (jedna linia = jedno zdarzenie), mieszczącej się w limicie 1500 tokenów i
zawierającej tylko informacje istotne dla analizy przyczyny awarii (zasilanie,
chłodzenie, pompy wodne, oprogramowanie, inne podzespoły). Weryfikacja jest
iteracyjna — hub/"technicy" zwracają feedback, co poprawić.

## Ownership
- `solution.py`: (do utworzenia) klasa zarejestrowana przez
  `@task("s02e03", hub_name="failure")`.
- Dane wejściowe: `GET /data/{apikey}/failure.json` przez `hub.get_data()`.
  Zweryfikowane live (2026-08-03): 248 KB, mimo rozszerzenia `.json` treść to zwykły
  tekst — jedna linia logu na zdarzenie (`[timestamp] [LEVEL] opis...`), nie
  faktyczny JSON. **Uwaga:** oficjalna treść zadania (`doc/zadanie.md`) podaje URL
  z rozszerzeniem `.log`, nie `.json` — do zweryfikowania przy pierwszym realnym
  `hub.get_data()`; nie zakładać które jest poprawne bez sprawdzenia.
- `doc/`: treść zadania (`zadanie.md`, `fabula.md`) + destylat cheese-strategies
  z komentarzy kursu (`community_notes.md`) — materiał referencyjny, nieużywany
  w runtime.

## Local Contracts
- Odpowiedź to POST `/verify` z `answer.logs` = string, wiersze oddzielone `\n`,
  jeden wiersz = jedno zdarzenie. Zachować: data `YYYY-MM-DD`, godzina `HH:MM`/`H:MM`,
  poziom ważności, identyfikator podzespołu.
- **Limit tokenów jest `< 1500`, nie `≤ 1500`** — potwierdzony live przykład
  odrzucenia przy dokładnie 1500/1500 (100%). Celować w margines (np. ~1400).
- Feedback z huba wskazuje brakujący/niejasny podzespół po nazwie ("...unable to
  determine what happened to device xxxxx") — trzeba go sparsować i doszukać w
  pełnym logu, nie zaczynać kompresji od zera przy każdej iteracji.

## Work Guidance
- **MVP w 5 krokach** (destylat z `doc/community_notes.md`, patrz tam po pełne
  źródła i cytaty):
  1. Pobierz `failure.log`/`.json` (patrz uwaga w Ownership o rozszerzeniu).
  2. Deduplikuj programistycznie (ten sam opis, różny timestamp → zostaw jeden) —
     pojedynczy najskuteczniejszy krok wg społeczności, potrafi zejść z tysięcy
     wpisów do rzędu wielkości dziesiątek.
  3. Odfiltruj `[INFO]` programistycznie (regex/kod, nie LLM) — to szum.
  4. Dopiero to co zostaje idzie do modelu do klasyfikacji/kompresji per
     podzespół (`gpt-5.4-nano` / `gpt-4o-mini` wracają najczęściej jako
     tanie-i-skuteczne w relacjach społeczności — nie brać za pewnik, zweryfikować
     na drabinie modeli z `strategy/llm-selection.md`).
  5. Zlicz tokeny lokalnie przed wysyłką, wyślij, sparsuj feedback o brakującym
     podzespole, doszukaj go w pełnym logu, dołóż, powtórz aż flaga.
- Nie trzymać pełnych logów w kontekście głównego agenta — narzędzie do
  filtrowania/wyszukiwania (po poziomie, po tekście komponentu) + osobne
  narzędzie do liczenia tokenów, ewentualnie subagent dedykowany do samej
  kompresji opisów.
- "Najważniejsze zdarzenia" ≠ tylko rdzeń reaktora — trzeba przejść wszystkie
  zgłoszone przez feedback podzespoły (np. `ECCS8`), nie tylko oczywiste.

## Verification
- (uzupełnić po zaimplementowaniu `solution.py`)

## Child DOX Index
- None.
