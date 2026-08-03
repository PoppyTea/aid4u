# s02e01_categorize Module

## Purpose
Klasyfikacja 10 towarów jako niebezpieczne (`DNG`) lub neutralne (`NEU`) — ale nie
przez nasz LLM. Piszemy jeden statyczny **prompt** (≤100 tokenów łącznie z danymi
towaru), który hub wysyła do swojego wewnętrznego, bardzo ograniczonego modelu
klasyfikującego. Wyjątek fabularny: części do reaktora (kasety paliwowe) MUSZĄ być
zawsze klasyfikowane jako `NEU`, mimo że obiektywnie są niebezpieczne — to celowe,
żeby uniknąć kontroli.

## Ownership
- `solution.py`: `CategorizeTask` (`@task("s02e01", hub_name="categorize")`) —
  `_PROMPT_PREFIX` (statyczny prefiks promptu), `_build_prompt()`, `_call()`
  (POST /verify wrapper z guardem na `expected_code`).
- Dane wejściowe: `GET /data/{apikey}/categorize.csv` przez `hub.get_data()` —
  **zawsze świeże, bez cache** (zawartość zmienia się co kilka minut;
  `self.cache.get_or_fetch()` serwowałby stare dane z dysku — patrz
  `core/hub/cache.py:45-65` — nie używać tutaj).
- `doc/`: treść zadania + wskazówki z NotebookLM — materiał referencyjny,
  nieużywany w runtime przez `solution.py`.

## Local Contracts
- **`answer` MUSI być obiektem JSON `{"prompt": "..."}`, nie gołym stringiem**
  — nieudokumentowane w treści zadania, odkryte live: string → 400 "answer
  field is not valid JSON"; string zacytowany w cudzysłowie → 400 "must
  contain a JSON structure (object or array)".
- Kody odpowiedzi (odkryte live, nieudokumentowane): `code: 2` = reset
  ("Balance renewed"); `code: 1` = poprawna klasyfikacja (`debug.result:
  "correct classification"`, `classified_items` rośnie); `code: -890` = zła
  klasyfikacja (`debug.result: "wrong classification"`) — **zeruje cały
  budżet natychmiast**, nie tylko koszt tego zapytania; `code: -910` =
  "Insufficient funds" (wszystkie kolejne wywołania failują, dopóki nie
  wyślesz `reset` ponownie).
- `solve()` resetuje na start KAŻDEGO uruchomienia (nie tylko po błędzie) —
  bo hub liczy budżet per-sesja, nie per-CSV-fetch, więc bez tego dziedziczy
  się stan z poprzedniej próby.
- Prompt musi być precyzyjny co do zakresu `DNG`: **tylko faktyczna broń**
  (broń palna, amunicja, ostrza, broń obezwładniająca) — NIE "cokolwiek brzmi
  niebezpiecznie". Pierwsza wersja promptu ("Weapons, explosives, hazardous =
  DNG") błędnie sklasyfikowała `"Diesel fuel injector nozzles"` jako `DNG`
  (żywy test 2026-08-03, patrz Verification) — słowo "fuel" samo w sobie nie
  jest sygnałem DNG. Wyjątek reaktora/paliwa jądrowego jest częścią tej samej
  zasady ("fuel/reactor/nuclear/military-labeled ≠ automatycznie DNG"), nie
  osobnym specjalnym przypadkiem w prompt-logice.

## Work Guidance
- Jeśli hub zwróci `-890` (zła klasyfikacja) na jakimś towarze, dopracuj
  `_PROMPT_PREFIX` (zawężaj kryteria DNG), zresetuj i uruchom ponownie — CSV
  się zmienia co kilka minut, więc konkretne towary z poprzedniej próby mogą
  już nie wystąpić, ale kategorie (broń vs. wszystko inne) się powtarzają.
- Token budżet ma mały margines (~60-65/100 wg `cl100k_base` dla obecnego
  promptu) — nie rozszerzaj `_PROMPT_PREFIX` bez ponownego sprawdzenia przez
  `tiktoken`.

## Verification
- `uv run run.py solve s02e01 --dry-run` (2026-08-03): zero realnych wywołań
  `/verify` (tylko `GET categorize.csv`), zbudowany prompt pokazany w
  podglądzie.
- Live (2026-08-03): pierwsza wersja promptu — błąd klasyfikacji na
  `"Diesel fuel injector nozzles"` (`-890`), budżet wyzerowany, reszta
  zapytań `-910`. Po zawężeniu kryteriów DNG do faktycznej broni: pełne 10/10
  poprawnych klasyfikacji, flaga `{FLG:SMUGGLER}` otrzymana i zapisana w
  `.flags.json`.

## Child DOX Index
- None.
