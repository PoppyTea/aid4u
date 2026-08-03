# s02e05_drone Module

## Purpose
Przeprogramowanie uzbrojonego drona tak, żeby zamiast w elektrownię Żarnowiec
(`PWR6132PL`) uderzył w pobliską tamę — zniszczenie tamy ma dostarczyć wodę do
uszkodzonego systemu chłodzenia (fabuła spina się z `s02e02_electricity`, gdzie
`PWR6132PL` to jedna z zasilanych elektrowni).

## Ownership
- `solution.py`: (do utworzenia) klasa zarejestrowana przez
  `@task("s02e05", hub_name="drone")`.
- Dane wejściowe — **jedyne z 5 zadań S02 kwalifikujące się pod istniejący
  kontrakt `data/input/`** (dokument referencyjny, nie mutowalny payload API):
  - `GET /dane/doc/drone.html` (publiczne, bez apikey) przez `hub.get_doc()` —
    pasuje wprost do istniejącego prefixu `/dane/doc/`.
  - `GET /dane/mapa_dron.png` (publiczne, bez apikey) — **inny prefix** niż
    `get_doc()` obsługuje; przy realizacji dodać małą generyczną metodę
    publicznego GET w `core/hub/client.py` (np. `get_public(path)`), nie tu.
  - Docelowy folder: `data/input/s02e05_drone/` (patrz `data/input/AGENTS.md`) —
    fetch script wzorowany na `data/input/s01e04_sendit/fetch_spk_files.py`
    (uproszczony, chyba że `drone.html` faktycznie linkuje dalsze strony —
    sprawdzić przy realizacji, nie zakładać teraz).
- `doc/` (w tym folderze zadania): treść fabuły/zadania z NotebookLM — materiał
  referencyjny, nieużywany w runtime.

## Local Contracts
- (uzupełnić po zaimplementowaniu `solution.py`)

## Work Guidance
- Mapa terenu ma podbitą intensywność koloru wody przy tamie — celowe ułatwienie
  lokalizacji sektora w siatce.

## Verification
- (uzupełnić po zaimplementowaniu `solution.py`)

## Child DOX Index
- None.
