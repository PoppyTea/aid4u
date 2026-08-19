# s03e04_negotiations Module

## Purpose
Odwrócenie ról: **my wystawiamy dwa publiczne narzędzia HTTP, agent Centrali je
wywołuje**, żeby ustalić miasta oferujące jednocześnie wszystkie 3 potrzebne
przedmioty. Flaga nie powstaje z naszej odpowiedzi — agent sam zgłasza znalezione
miasta, my tylko rejestrujemy adresy i odbieramy wynik. Dopasowanie
deterministyczne, zero LLM.

**Rozwiązane (2026-08-19)** — flaga `{FLG:WINDFARM}` w `.flags.json`, koszt $0.00.
Agent szukał turbiny wiatrowej, akumulatora 48V i inwertera 48V; zmieścił się
w **6 z 10** dostępnych kroków. Odpowiedź: **Domatowo + Skolwin**.

## Ownership
- `catalog.py`: czysta logika, zero I/O sieciowego — ładowanie CSV, normalizacja,
  rdzenie, punktacja dopasowania, przecięcie miast. Testowalne offline.
- `server.py`: FastAPI (`ServerFactory`), endpointy `/search` i `/cities`,
  koperta odpowiedzi, log JSONL do `.run/s03e04_negotiations/` (gitignored).
- `solution.py`: `@task("s03e04", hub_name="negotiations")`. `solve()` **odmawia**
  (kontrakt żywego serwera, patrz `../AGENTS.md`). Rejestracja i polling flagi
  przez `main()`.
- `doc/`: treść zadania i fabuła — materiał referencyjny, nieużywany w runtime.
- Dane wejściowe: `data/input/s03e04_negotiations/` — 3 pliki CSV pobrane przez
  `HubClient.get_public('dane/s03e04_csv/…')`, commitowane.

## Local Contracts
- **Hub wymaga DOKŁADNIE 2 narzędzi.** Treść zadania mówi „możesz ogarnąć
  wszystko jednym", ale walidator odrzuca: `Field "tools" must contain exactly 2
  elements (tool #1 and tool #2)`.
- **Klucz to `URL` WIELKIMI literami**, obok `description`. Pola `name` nie ma.
- Agent wysyła `{"params": "<NL>"}`, oczekuje `{"output": "<tekst>"}`.
- **Odpowiedź musi mieścić się w 4–500 bajtach.** Każda ścieżka błędu też kończy
  się poprawnym `output` — agent, który nie dostanie odpowiedzi, **przerywa pracę
  na stałe**. Dlatego `ToolRequest.params` jest typu `Any`, nie `str`: walidacja
  422 byłaby dla agenta równoznaczna z ciszą.
- Odbiór flagi: `answer.action = "check"` — `action` **wewnątrz** `answer`.
  `-500 "No results yet"` to normalny stan, nie błąd; ponawiać.
- Agent ma 10 kroków i szuka 3 przedmiotów.

## Work Guidance
- **`/search` przeszukuje CAŁY katalog**, nie tylko podzespoły turbiny. Epizod ma
  sekret (druga flaga), a jeden z uczestników kursu zaświadcza, że agent znalazł
  go sam, zanim rozwiązał zadanie główne — zawężenie zakresu odcięłoby tę ścieżkę.
- **Punktujemy pokrycie tokenów NAZWY pozycji, parametry techniczne (`400W`,
  `48V`) tylko podbijają ranking.** Liczenie ich do pokrycia dawało 0 trafień dla
  „szukam turbiny wiatrowej" (2 tokeny zapytania wobec 4 tokenów pozycji).
- **Pozycja bez miast schodzi na koniec rankingu** (`sellable` jest pierwszym
  kryterium sortowania). Bez tego sierota `06OTEB` wygrywała zapytania o
  akumulator 12V i prowadziła agenta w ślepy zaułek.
- Restart serwera po każdej zmianie — uruchomiony proces trzyma stary kod.
- Fallback LLM (normalizacja do mianownika) **nie jest zaimplementowany**;
  deterministyczna kaskada wystarczyła. Wracać do tego tylko jeśli `/debug`
  pokaże nietrafione zapytania.
- **Krótkie kwalifikatory (≤2 znaki) nie liczą się do pokrycia nazwy.** To
  poprawka z PIERWSZEGO, nieudanego przebiegu na żywo: `Inwerter DC/AC 48V 3000W`
  miał rdzenie nazwy `('inwerter','dc','ac')`, więc zapytanie `inwerter` dawało
  pokrycie 1/3 i wypadało nawet z progu awaryjnego. Hub odpowiedział
  `-790 "The store does not have inverters"`. Log JSONL był jedynym źródłem,
  które to pokazało — `/debug` huba nie ujawnia naszej decyzji dopasowania.

## Pułapki danych (zweryfikowane 2026-08-19)
- **Zduplikowany kod `06OTEA` z komentarzy kursu już NIE ISTNIEJE** — dane
  załatano (`06OTEA`/`06OTEB`), wszystkie 2137 kodów i nazw są unikalne.
- **Łatka zostawiła sierotę:** `Akumulator kwasowy 12V 200Ah` (`06OTEB`) to
  jedyna pozycja bez żadnego miasta. Pusty wynik jest dla niej POPRAWNY.
- **306 z 2137 kodów nie zawiera cyfry**, więc kształtu `[A-Z0-9]{6}` nie da się
  odróżnić od sześcioliterowego polskiego słowa. `CatalogIndex.extract_code()`
  waliduje kandydatów wobec katalogu.
- `cities.csv` nie ma znaku nowej linii na końcu — `csv` radzi sobie, `wc -l`
  gubi ostatnie z 51 miast.
- W katalogu **nie ma kabli ani kontrolerów ładowania** — przykład „kabel 10m"
  z treści zadania jest ilustracyjny, nie pochodzi z tego zbioru.

## Verification
- `uv run pytest tasks/s03e04_negotiations/` — 34 testy, zero sieci, na
  prawdziwych CSV (odmiana, literówka, limit bajtów, sierota, kontrakt huba).
- `uv run pyrefly check tasks/s03e04_negotiations/` — zielone.
- Smoke lokalny: `uv run python -m tasks.s03e04_negotiations.server`, potem
  `curl -X POST localhost:8004/search -d '{"params":"szukam turbiny wiatrowej"}'`.
- `https://hub.ag3nts.org/debug` — realny ruch od agenta, sprawdzać PRZED `check`.
- Zadanie zwraca flagę z huba — to ostateczna weryfikacja, nie zielone testy.

## Sekret (druga flaga) — stan: nieudane jedno podejście (2026-08-19)
- Nazwa flagi (jedyna wskazówka): „Dostałbym ją gdyby nie ta cenzura!" → hipoteza:
  cenzor tnie jawne `{FLG:...}`, trzeba przemycić flagę zakodowaną (base64).
- Tryb `--secrets` (`secrets_probe.py`, env `S03E04_SECRETS`): prompt injection w
  opisach (limit **300 znaków**, `-875`) + wzmocnienie w odpowiedziach; socjotechnika
  („kanał audytu", „darmowy odbiór") + żądanie base64. Poller dekoduje base64/rot13.
- **Dlaczego nie zadziałało:** po pierwszym zaliczeniu głównej flagi hub oddaje
  **zbuforowany** wynik i **nie uruchamia agenta ponownie** — 0 nowych wywołań
  narzędzi w przebiegu sekretnym. Injection nigdy nie dotarł do agenta.
- **Wniosek na powrót (po 20 flagach):** sekretu trzeba próbować **przed** albo
  **razem z** pierwszym zaliczeniem (jedna rejestracja, injection od startu), nie w
  osobnym drugim podejściu z tego samego konta. Ewentualny reset zadania po stronie
  huba — nieznany.

## Child DOX Index
- None.
