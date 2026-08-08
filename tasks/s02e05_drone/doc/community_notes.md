# s02e05 (drone) — destylat z komentarzy kursu

Źródło: `aid4u-private/00-materialy-z-kursu/12_komentarze-do-lekcje-zadania/md/s02e05_aid4u_comments.md`
(oryginał nieprzetrzebiony, ~1300 linii). Poniżej tylko sygnał przydatny dla
**deterministycznego** podejścia z `solution.py` — pominięte wątki o promptach/modelach
vision, bo `solve()` nie używa LLM w ogóle (patrz uzasadnienie w `AGENTS.md`).

## Protokół API — potwierdzone zachowania

- **Config drona jest trzymany po stronie serwera i kumuluje się między próbami.**
  Błędy z wcześniejszych prób (np. testowych, niedokończonych) zostają w stanie drona i
  psują kolejne próby w mylący sposób. `hardReset` na starcie sekwencji jest zalecany
  wprost przez staff, nie tylko przez treść zadania.
- **`flyToLocation` MUSI być ostatnią instrukcją.** Potwierdzone wielokrotnie — ktoś
  dostawał "brak instrukcji powrotu" mimo obecnego `set(return)` w liście, bo kolejność
  była zła; poprawka: "spróbuj najpierw wszystko ustawić, a potem wydać komendę żeby
  leciał".
- **`selfCheck` ≠ skonfigurowany dron.** `selfCheck` sprawdza tylko sprzęt ("fully
  operational and ready for flight") — nie oznacza, że plan misji (cel, sektor, wysokość)
  jest ustawiony. `flyToLocation` bez pełnej konfiguracji zwraca błąd mimo pozytywnego
  `selfCheck`.
- **Bez `set(return)` dron przepada na stałe** ("we will lose it forever") — twardy wymóg,
  nie kosmetyka.

## Znaczenie kodów błędów (potwierdzone przykładami z huba)

- `-880` **"Hey, you do know we're only pretending to destroy power plants, not actually
  destroy one, OK?"** — zły cel bombardowania: sektor `set(x,y)` wskazuje na elektrownię
  (zadeklarowany cel), nie na tamę. Rozwiązanie: sektor musi być tamy, nie elektrowni —
  `setDestinationObject` i `set(x,y)` celowo wskazują dwa różne miejsca.
- `-880` **"I don't think you'll hit the dam. You'll drop the bomb somewhere nearby."**
  — sektor jest BLISKI, ale niedokładny. Sygnał, że detekcja siatki/sektora ma błąd o
  jedno pole — w naszym przypadku deterministyczna detekcja jest jednoznacznym outlierem
  (patrz `map_analysis.py`), więc ten błąd nie jest oczekiwany, ale gdyby się pojawił,
  wskazuje na przesunięcie o 1 w `col`/`row`, nie losowy błąd.
- `-945` **"I don't know that location."`** — brak albo zły `setDestinationObject` (model
  próbował podać nazwę lokalizacji zamiast kodu obiektu, albo pominął instrukcję).

## Sektor tamy — niezależna weryfikacja

Wielu uczestników niezależnie zlokalizowało tamę w sektorze **(2, 4)** (kolumna 2, wiersz
4, indeksowane od 1) na siatce **3 kolumny × 4 wiersze** — dokładnie to, co wykrywa
`map_analysis.detect_dam_sector()` programistycznie (bez LLM/vision) na tej samej mapie.
Zgodność niezależnej detekcji wizyjnej (ludzie + modele) z detekcją programistyczną
(kolor/geometria) jest silnym potwierdzeniem poprawności metody.

## Rzeczy pominięte świadomie (nie dotyczą podejścia deterministycznego)

- Debata o modelach vision (`gpt-4o` vs `gpt-5.4` vs `gemini-3-flash-preview`) — zbędna,
  `solve()` nie wysyła obrazu do żadnego modelu.
  OpenAI moderation refusals na prompt "zniszcz tamę" — nie dotyczy, zero promptów LLM.
- Architektury wieloagentowe (Vision phase → Agent phase) opisywane w komentarzach —
  zastąpione jednym deterministycznym przebiegiem `solve()`.
