# s02e02_electricity Module

## Purpose
Puzzle elektryczne na planszy 3x3 — segmenty rur/kabli trzeba obracać o 90° (jedyna
dozwolona operacja, jeden obrót = jedno zapytanie do API) tak, żeby doprowadzić prąd
ze wspólnego źródła awaryjnego (lewy-dolny róg) do trzech elektrowni: `PWR6132PL`,
`PWR1593PL`, `PWR7264PL`. Okablowanie musi tworzyć obwód zamknięty.

## Ownership
- `solution.py`: (do utworzenia) klasa zarejestrowana przez
  `@task("s02e02", hub_name="electricity")`.
- Dane wejściowe: `GET /data/{apikey}/electricity.png` przez `hub.get_data()` —
  **mutowalne**: obraz zmienia się po każdym wysłanym `rotate`, więc trzeba go
  pobierać ponownie po każdej akcji, nie raz na start. Referencyjny stan docelowy
  (publiczny, bez apikey): `https://hub.ag3nts.org/i/solved_electricity.png`.
- `doc/`: treść zadania — materiał referencyjny, nieużywany w runtime.

## Local Contracts
- **Cross-episode note:** `PWR6132PL` to ta sama elektrownia (Żarnowiec) co w
  fabule `s02e05_drone` — nie ignorować fabuły, może nieść kontekst między
  epizodami (potwierdzony wzorzec z S01, patrz `tasks/AGENTS.md`).
- (reszta — uzupełnić po zaimplementowaniu `solution.py`)

## Work Guidance
- (uzupełnić po zaimplementowaniu `solution.py`)

## Verification
- (uzupełnić po zaimplementowaniu `solution.py`)

## Child DOX Index
- None.
