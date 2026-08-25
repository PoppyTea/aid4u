# s04e03_domatowo Module

## Purpose
Odnalezienie partyzanta ukrytego w ruinach Domatowa (plansza 11×11) i wezwanie
śmigłowca, w budżecie 300 punktów akcji. **Zero LLM.**

**Rozwiązane (2026-08-25)** — flaga `{FLG:WEVEGOTHIM}`, koszt $0.00, **160 z 300
punktów** (31 akcji: 3 `create`, 13 `move`, 3 `dismount`, 12 `inspect`). Trafienie
wypadło dopiero na 12. inspekcji z 14 możliwych, więc to przebieg bliski najgorszemu —
przy wcześniejszym trafieniu koszt spada proporcjonalnie.

## Ownership
- `city.py`: **cała geometria i planowanie, funkcje czyste, zero I/O** — współrzędne,
  klastrowanie celów, wybór punktu zrzutu, podział limitu zwiadowców, klasyfikacja
  komunikatów `inspect`. To tutaj decyduje się koszt operacji, więc to tutaj są testy.
- `solution.py`: `@task("s04e03", hub_name="domatowo")` — cienka powłoka I/O nad `city.py`.
- `test_solution.py`: 43 testy offline, zero sieci.
- `doc/`: treść zadania i fabuła.
- Brak danych statycznych — mapa i stan planszy żyją po stronie API.

## Local Contracts
- **Cel to `block3`** („Blok 3p", 14 pól). Zawężenie ze 121 pól planszy bierze się
  z przechwyconego sygnału w treści zadania: „Ukryłem się w jednym z najwyższych bloków".
- **`solve()` NIE woła `callHelicopter`** — zwraca
  `{"action": "callHelicopter", "destination": <pole>}`, a wysyła je `BaseTask._submit()`.
- **`reset` na starcie** czyni przebieg powtarzalnym (jest darmowy i przelosowuje pozycję
  partyzanta). Bez niego druga próba startowałaby z jednostkami i punktami z pierwszej.
- Limity z treści zadania są **globalne na operację, nie na desant**: 8 zwiadowców,
  4 transportery, 4 pasażerów na pojazd. Przydział powstaje z góry
  (`city.allocate_scouts()`), zanim ruszy pierwszy transporter.

## Model kosztu (zmierzony, nie przepisany z treści)
Treść podaje cennik, ale nie mówi dwóch rzeczy, które wyszły dopiero z sondy:

- `move` raportuje `path_steps` **wliczając pole startowe**, a nalicza za `path_steps - 1`
  (A6→A10: `path_steps: 5`, koszt 28 = 4 × 7).
- Zwiadowca chodzi po **dowolnym** terenie (wchodzi na `block3`), więc jego trasa to
  odległość Manhattan. Transporter jeździ wyłącznie po ulicach, więc jego trasę liczy
  BFS po grafie dróg — odległość w linii prostej byłaby tu kłamstwem.

Stąd cała optymalizacja: krok zwiadowcy kosztuje **7×** tyle co krok transportera, więc
opłaca się nadłożyć drogi pojazdem, żeby skrócić marsz pieszo. `dismount` jest darmowy
i czasem stawia zwiadowcę prosto na celu.

## Pułapki (zweryfikowane na żywo)
- 🔴 **`callHelicopter` nie nadaje się na detektor trafienia, mimo że kusi.** Kosztuje
  0 punktów i zwraca 400, dopóki nikt nie potwierdził człowieka — wygląda jak darmowy,
  autorytatywny test. Ale **wywołanie testujące JEST wykonaniem ewakuacji**: pierwsza
  wersja przeszła tak `--dry-run` i naprawdę zakończyła misję. Detekcja idzie przez
  `getLogs` (też 0 punktów).
- 🔴 **Limit 8 zwiadowców jest globalny.** Dwa pełne czterosobowe desanty wyczerpują go
  w całości i trzeci `create` odbija się od API z HTTP 400 — przy trzecim z trzech
  budynków, czyli po wydaniu punktów na dwa poprzednie.
- 🔴 **Słownik komunikatów `inspect` jest otwarty.** Przebieg zdobywający flagę przyniósł
  trzy sformułowania spoza listy zebranej dzień wcześniej. Dlatego `reads_as_found()`
  zwraca `None` dla nieznanego zdania, a nie `False`, a przemiatanie zlicza takie
  przypadki i mówi o nich w błędzie końcowym. **Zabezpieczeniem jest ta gałąź, nie lista.**
- 🟡 **Zwiadowcy z poprzednich budynków zostają na planszy.** Bez zapamiętania stanu
  SPRZED `dismount` kolejny desant „widzi" ich wszystkich i plan może pchnąć kogoś przez
  pół mapy po 7 punktów za pole.
- 🟡 **`dismount` nie przyjmuje pola docelowego** — stawia zwiadowców „on free tiles
  around vehicle". Gdzie faktycznie wylądowali, mówi dopiero `getObjects`.

## Work Guidance
- **Bez LLM.** Społeczność potwierdza kierunek: *„Tak »deterministycznie« szło u mnie też
  najlepiej, Agent czasem wysyłał w losowe miejsca"*. Jedyny udokumentowany sposób
  przegrania to przepalenie punktów — *„jeśli np. agent zasuwa jednym zwiadowcą
  na piechotę i nie zapamiętuje już sprawdzonych lokalizacji"*.
- Sondowanie jest darmowe: `reset`, `getMap`, `getObjects`, `getLogs`, `expenses`,
  `actionCost`, `searchSymbol` i `help` kosztują 0 punktów.

## Verification
- `uv run pytest tasks/s04e03_domatowo/` — 43 testy, zero sieci.
- `uv run run.py solve s04e03 --dry-run` — pełne przemiatanie na żywo, wywołanie
  ewakuacji wypisane zamiast wysłania (i **nie** wykonane, patrz Pułapki).
- Flaga z huba to ostateczna weryfikacja.

## Child DOX Index
- None.
