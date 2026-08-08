# s02e05_drone Module

## Purpose
Przeprogramowanie uzbrojonego drona tak, żeby zamiast w elektrownię Żarnowiec
(`PWR6132PL`) uderzył w pobliską tamę — zniszczenie tamy ma dostarczyć wodę do
uszkodzonego systemu chłodzenia (fabuła spina się z `s02e02_electricity`, gdzie
`PWR6132PL` to jedna z zasilanych elektrowni).

**Rozwiązane (2026-08-08)** — flaga `{FLG:LETSFLY}` w `.flags.json`, za pierwszej
próby wysyłki, zero LLM.

## Ownership
- `solution.py`: `DroneTask`, zarejestrowana przez `@task("s02e05", hub_name="drone")`.
- `map_analysis.py`: deterministyczna detekcja sektora tamy z mapy (czerwone linie
  siatki + podbita intensywność wody), bez sieci i bez LLM/vision.
- Dane wejściowe — **jedyne z 5 zadań S02 kwalifikujące się pod kontrakt
  `data/input/`** (dokument referencyjny + statyczna mapa, nie mutowalny payload API,
  w odróżnieniu od `s02e02_electricity`'s `electricity.png`):
  - `data/input/s02e05_drone/fetch_drone_assets.py` pobiera `drone.html` (przez
    `hub.get_public("dane/drone.html")`) i `drone.png` (przez
    `hub.get_data("drone.png", tolerate_503=True)`), waliduje treść przez
    `core.net.expect_binary()` przed zapisem.
- `data/output/s02e05_drone/dam_sector.json`: wynik deterministycznej detekcji
  (sektor + wszystkie wyniki per-komórka) — ground truth do przyszłej kalibracji
  vision/promptów, gdyby `LLMClient` kiedyś dostał wsparcie dla obrazów.
- `doc/`: treść zadania, fabuła, destylat komentarzy kursu — materiał referencyjny,
  nieużywany w runtime.

## Local Contracts
- **Poprawka błędnych założeń w tym pliku (2026-08-08)** — poprzednia wersja
  zakładała `GET /dane/doc/drone.html` przez `get_doc()` i osobny prefiks
  `/dane/mapa_dron.png`. Oba były błędne (zweryfikowane curl-em): realny URL
  dokumentacji to `/dane/drone.html` (bez `/doc/`), a `mapa_dron.png` w ogóle nie
  istnieje — mapa jest pod `/data/{apikey}/drone.png` przez zwykłe `get_data()`.
  ⚠️ **Pułapka soft-404**: zły URL do mapy (`mapa_dron.png`) zwraca HTTP 200 z
  treścią `"task not found"` zamiast 404 — stąd `core.net.expect_binary()` przy
  każdym pobraniu, nie tylko sprawdzenie statusu.
- **Brak LLM/vision — świadoma decyzja, nie obejście.** `LLMClient` w tym repo nie
  ma dziś żadnego wsparcia dla obrazów (`LLMMessage.content` to goły `str` — patrz
  `core/AGENTS.md`). Zamiast dokładać vision pod jedno zadanie, `map_analysis.py`
  wykorzystuje że mapa jest generowana programistycznie z dwoma policzalnymi
  sygnałami: siatka = grube czerwone linie pełnej wysokości/szerokości (odróżnialne
  od szumu progiem pokrycia), sektor tamy = jednoznaczny outlier intensywności
  koloru wody. Zweryfikowane na żywej mapie: sektor (2,4) w siatce 3×4, water
  fraction 6.07% wobec 0.0% w pozostałych 11 sektorach — zero niepewności. Wynik
  **niezależnie potwierdzony przez społeczność kursu** (wielu uczestników wizyjnie
  zlokalizowało tę samą tamę w tym samym sektorze).
- **Pełny kontrakt API drona jest statyczny i znany z góry** (w odróżnieniu od
  `s02e04_mailbox`, gdzie protokół trzeba było odkrywać na żywo) — wyciągnięty raz z
  `drone.html` do stałych w `solution.py`, bez pętli agentowej. Kluczowe reguły:
  `hardReset` na starcie (config drona jest trzymany serwerowo i kumuluje się między
  próbami), `flyToLocation` MUSI być ostatnią instrukcją, `set(return)` obowiązkowe
  (bez niego dron przepada na stałe), misja deklaruje `setDestinationObject(PWR6132PL)`
  ale faktyczny `set(col,row)` celuje w sektor tamy — to jest sedno zadania.
- **`_submit()` nadpisane** (wzorzec z `s02e04_mailbox`) — pomija redundantny drugi
  `POST /verify` jeśli `solve()` już złapało flagę w swojej wewnętrznej pętli.
- **Pillow dodane jako zależność** (`pyproject.toml`) — jedyny sposób dekodowania
  PNG bez pisania własnego dekodera; `numpy` był już dostępny tranzytywnie.
- **`solve()` respektuje `self.dry_run`** — bez sensownego trybu "symulowanej"
  iteracji (pętla feedbacku wymaga prawdziwych odpowiedzi huba), więc `--dry-run`
  buduje i pokazuje sekwencję bez ani jednego `/verify`. **Złapane w praktyce**: pierwsza
  wersja tego kodu wołała `hub.submit()` bezwarunkowo — `--dry-run` wysłał prawdziwe
  zapytanie i faktycznie zdobył flagę, zanim błąd został wykryty i poprawiony.

## Work Guidance
- Mapa terenu ma podbitą intensywność koloru wody przy tamie — celowe ułatwienie
  lokalizacji sektora w siatce. Potwierdzone: to wystarczy do w 100% deterministycznej
  detekcji, żadna analiza wizyjna LLM nie jest potrzebna.
- Jeśli `map_analysis.detect_dam_sector()` kiedyś rzuci `DamSectorAmbiguousError` na
  innej mapie (inny format/kolory), NIE obniżać progów na ślepo — sprawdzić realny
  obraz najpierw (progi `_RED_THRESHOLD`/`_WATER_THRESHOLD`/`_MIN_OUTLIER_RATIO` są
  dostrojone do referencyjnej mapy, nie uniwersalne).

## Verification
- `uv run pytest tasks/s02e05_drone/` — 19 testów (detekcja siatki/sektora na
  syntetycznych obrazach + `solve()` z mockiem huba), bez sieci.
- `uv run run.py solve s02e05 --dry-run` — pokazuje zbudowaną sekwencję instrukcji
  bez wysyłki.
- `uv run run.py solve s02e05` — flaga w konsoli i `.flags.json`.

## Child DOX Index
- None.
