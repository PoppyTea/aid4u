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
  faktyczny JSON.
- `doc/`: treść zadania — materiał referencyjny, nieużywany w runtime.

## Local Contracts
- (uzupełnić po zaimplementowaniu `solution.py`)

## Work Guidance
- (uzupełnić po zaimplementowaniu `solution.py`)

## Verification
- (uzupełnić po zaimplementowaniu `solution.py`)

## Child DOX Index
- None.
