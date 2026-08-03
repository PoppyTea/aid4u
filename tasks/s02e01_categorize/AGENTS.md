# s02e01_categorize Module

## Purpose
Klasyfikacja 10 towarów jako niebezpieczne (`DNG`) lub neutralne (`NEU`) — ale nie
przez nasz LLM. Piszemy jeden statyczny **prompt** (≤100 tokenów łącznie z danymi
towaru), który hub wysyła do swojego wewnętrznego, bardzo ograniczonego modelu
klasyfikującego. Wyjątek fabularny: części do reaktora (kasety paliwowe) MUSZĄ być
zawsze klasyfikowane jako `NEU`, mimo że obiektywnie są niebezpieczne — to celowe,
żeby uniknąć kontroli.

## Ownership
- `solution.py`: (do utworzenia) klasa zarejestrowana przez
  `@task("s02e01", hub_name="categorize")`.
- Dane wejściowe: `GET /data/{apikey}/categorize.csv` przez `hub.get_data()` —
  **zawsze świeże, bez cache** (zawartość zmienia się co kilka minut;
  `self.cache.get_or_fetch()` serwowałby stare dane z dysku — patrz
  `core/hub/cache.py:45-65` — nie używać tutaj).
- `doc/`: treść zadania + wskazówki z NotebookLM — materiał referencyjny,
  nieużywany w runtime przez `solution.py`.

## Local Contracts
- (uzupełnić po zaimplementowaniu `solution.py`)

## Work Guidance
- (uzupełnić po zaimplementowaniu `solution.py`)

## Verification
- (uzupełnić po zaimplementowaniu `solution.py`)

## Child DOX Index
- None.
