# s03e05_savethem Module

## Purpose
Planowanie trasy posłańca do miasta **Skolwin** na mapie 10×10 przy dwóch niezależnych
budżetach (10 paliwa, 10 jedzenia). Brak statycznej listy narzędzi — jest tylko
`/api/toolsearch`, zwracające 3 najlepsze dopasowania na zapytanie. Deterministycznie,
**zero LLM**.

**Rozwiązane (2026-08-20), obie flagi za jednym posiedzeniem:**
- główna `{FLG:INTACTCITY}` — rakieta 8 pól → `dismount` → marsz 3 przez wodę,
  paliwo 8.0/10, jedzenie 8.3/10, **za pierwszym podejściem**
- sekretna `{FLG:ABEAVER}` — osobna trasa kończąca się na polu bobrów
- koszt $0.00

## Ownership
- `discover.py`: faza odkrywania — `toolsearch` wieloma zapytaniami, potem odpytanie
  każdego narzędzia. Uruchamiane raz; zrzuty w `data/input/s03e05_savethem/`.
- `terrain.py`: czysta logika, zero I/O — model terenu, koszty, **BFS z frontem Pareto**,
  symulator trasy.
- `solution.py`: `@task("s03e05", hub_name="savethem")`. Czyta ZRZUT, nie żywe API.
- `doc/`: treść zadania i fabuła — materiał referencyjny.

## Local Contracts
- **Odpowiedź to płaska lista** `[nazwa_pojazdu, akcja, akcja, …]`; `dismount` jest
  jednym z elementów obok `up`/`down`/`left`/`right`.
- **Endpoint pojazdów to `/api/wehicles`** — z literówką. Poprawna pisownia
  `/api/vehicles` **404-uje w całości**.
- **Każde narzędzie wymaga konkretnej nazwy encji w `query`**, nie opisu: `maps` chce
  nazwy miasta (`Skolwin`), `wehicles` chce nazwy pojazdu (`horse`/`car`/`rocket`/`walk`).
  Zapytania opisowe dostają 404. Wyjątkiem jest `books`, które robi full-text.
- **Narzędzia rozmawiają wyłącznie po angielsku.**
- Hub przyjmuje wyłącznie trasy kończące się na `G` — **z jednym wyjątkiem**: trasa
  kończąca się na polu bobrów jest akceptowana i zwraca flagę sekretną.

## Pułapki (wszystkie zweryfikowane na żywo)
- 🔴 **Budżet jest OSTRY, nie domknięty.** Zużycie równe 10.0 to `-930 "Fuel reached
  zero. Mission failed."`, nie granica. Notatka `resource-consumption` mówi „runs out of
  fuel", co czyta się jak „przekroczy", a znaczy „dobije do zera".
- 🔴 **Backend indeksuje od 1, mapa od 0.** `savethem_backend.php` podaje
  `start: (8,1)`, `goal: (5,9)`, podczas gdy w tablicy z `/api/maps` to `(7,0)` i `(4,8)`.
  Przez to `beaver_spot: (2,7)` oznacza **(1,6)** w tablicy. Dwie próby sekretu spaliły
  się wyłącznie na tej różnicy.
- **`dismount` jest warunkiem KONIECZNYM, nie optymalizacją.** Dystans S→G to 11 ruchów;
  marsz (2.5 jedzenia/ruch), koń (1.6), auto (1.0+0.7) i rakieta (1.0 paliwa) każde
  z osobna przekraczają budżet, a auto i rakieta w dodatku nie wejdą do wody — cel jest
  odcięty rzeką w każdym wierszu. Bez zsiadania zadanie jest **nierozwiązywalne**.
- **Drzewo `T` kosztuje +0.2 paliwa tylko dla trybów silnikowych.** Przy trasie
  zużywającej 8-9 paliwa jedno drzewo potrafi rozstrzygnąć o wykonalności.
- **Legendę terenu (`S`/`G`/`R`/`T`/`W`) da się odczytać z `savethem_preview.html`**
  (funkcja `terrainClass`), bez odkrywania `/api/books` — społeczność zgłasza to jako
  tryb porażki numer jeden.

## Work Guidance
- **Nie zamieniaj dwóch budżetów w jeden koszt.** Trasa tańsza w paliwie bywa droższa
  w jedzeniu, więc istnieje tylko porządek CZĘŚCIOWY — stąd front Pareto po
  `(wiersz, kolumna, tryb)`, a nie Dijkstra. Uzasadnienie odrzucenia BFS/Dijkstry/DP:
  docstring `terrain.py`.
- **Zasoby liczone w dziesiątych jako liczby całkowite.** Na floatach porównanie
  z budżetem potrafi wyciąć poprawne trasy.
- `simulate()` jest twardą bramką przed hubem — liczy zużycie od zera po samej liście
  akcji, więc łapie rozjazd między planem a jego zapisem.
- Solver czyta zrzut z `data/input/`, nie żywe API — testy i `--dry-run` działają offline.

## Verification
- `uv run pytest tasks/s03e05_savethem/` — 23 testy, zero sieci, na prawdziwej mapie.
- `uv run pyrefly check tasks/s03e05_savethem/` — zielone.
- `uv run run.py solve s03e05 --dry-run` — plan + symulacja, bez huba.
- `https://hub.ag3nts.org/savethem_preview.html` — wizualny podgląd po zgłoszeniu.
- Flaga z huba to ostateczna weryfikacja, nie zielone testy.

## Child DOX Index
- None.
