# s04e04_filesystem Module

## Purpose
Uporządkowanie notatek Natana Ramsa w wirtualnym systemie plików Centrali: `/miasta`
(zapotrzebowanie jako JSON), `/osoby` (kto odpowiada za handel), `/towary` (kto co
sprzedaje). **Zero LLM.**

**Rozwiązane (2026-08-25)** — flaga `{FLG:DEALWITHIT}`, koszt $0.00, jeden `batch_mode`
z 32 operacjami. Społeczność płaciła tu $0.26 za `gemini-3-flash`, a modele lokalne
w ogóle nie przechodziły.

## Ownership
- `notes.py`: **cały odczyt notatek, funkcje czyste, zero I/O** — składanie nazw plików,
  dopasowanie odmiany, trzy parsery i budowa listy operacji.
- `solution.py`: `@task("s04e04", hub_name="filesystem")` — pobranie paczki, `reset`,
  jeden batch, zwrot `{"action": "done"}`.
- `test_solution.py`: 30 testów offline.
- `doc/`: treść zadania i fabuła.
- Dane wejściowe: `data/input/s04e04_filesystem/natan_notes.zip`. **Tylko archiwum jest
  w repo** — `.gitignore` ma globalne `*.txt`, więc rozpakowane notatki są lokalne.
  Dlatego testy czytają z ZIP-a, nie z katalogu.

## Dlaczego zero LLM, skoro wszyscy używali modelu
Intel kursu jest zgodny: to zadanie lingwistyczne, modele lokalne się na nim wykładały
(*„o ile radziły sobie z czystą gramatyką to gubiły się w znaczeniu tych notatek"*).
Deterministyczna droga istnieje, bo w paczce leży plik, którego nikt nie potraktował
jako **słownika**: `transakcje.txt` podaje wszystkie miasta i wszystkie towary
w mianowniku, w sztywnym formacie `Miasto -> towar -> Miasto`.

To zamienia „rozpoznaj polską odmianę" w „dopasuj formę odmienioną do znanego,
skończonego słownika" — czyli w dopasowanie rdzenia, nie rozumienie języka.

## Local Contracts
- **`solve()` NIE woła `done`** — zwraca `{"action": "done"}`, wysyła `BaseTask._submit()`.
- **`reset` na starcie** czyni przebieg idempotentnym (`createFile` nadpisuje tylko tę samą
  ścieżkę, więc bez resetu zostawałyby pliki z poprzedniej, błędnej próby).
- **Kolejność operacji w batchu jest wymuszona przez API**, nie kosmetyczna: `help` mówi
  „markdown links must point to existing files", więc katalogi i `/miasta` muszą powstać
  przed `/osoby` i `/towary`.
- Weryfikacja parsera jest **niezależna od huba**: `ogloszenia.txt` opisuje to samo
  zapotrzebowanie, co `food4cities.json` z `s04e05`, więc testy porównują wynik z plikiem
  z innego zadania.

## Pułapki (zweryfikowane na żywo)
- 🔴 **Nazwy plików muszą być małymi literami.** Niepisane — nie ma tego ani w treści
  zadania, ani w `help`. `/miasta/Brudzewo` → `code -940` „Invalid file path.",
  `/miasta/brudzewo` przechodzi.
- 🔴 **Kropki w nazwach zabronione** → `code -935` „File extensions are not allowed.
  Use names without dots." Żadnych `.md`.
- 🔴 **`ł` nie ma dekompozycji kanonicznej.** `unicodedata.normalize("NFD", …)` + odsiew
  znaków łączących usuwa `ą`, `ę`, `ż`, ale `ł` zostawia nietknięte, więc `łopata`
  i `wołowina` szłyby do nazw plików z polskim znakiem — wprost wbrew treści zadania.
- 🔴 **`maka` jest prefiksem `makaron`.** Dopasowanie „pierwszy pasujący" wpisywało mąkę
  w miejsce makaronu, cicho i we wszystkich miastach naraz. Stąd dopasowanie od
  najdłuższego rdzenia.
- 🔴 **Dwie osoby są przedstawione na raty** — nazwisko w jednym zdaniu, imię w innym
  („Kisiel ma do mnie dzwonic" … „Rafal oddzwonil"; „od Konkel" … „Teraz to Lena").
  To jest ta „polska semantyka", o którą rozbijały się modele.
- 🟡 **Filtr po pozycji w zdaniu nie działa** na wyrazy otwierające zdanie: „Kisiel" i
  „Rafal" też stoją na początku zdania, więc odsianie wszystkiego, co otwiera zdanie,
  wycięłoby prawdziwe nazwisko razem z „Najpierw". Stąd krótka, zamknięta lista
  `_NOT_A_NAME` plus twarda walidacja w `read_notes()`.
- 🟡 **Nagłówek `rozmowy.txt` podaje nazwisko w dopełniaczu** („przez Natana Ramsa
  z Domatowa") — wpuszczony do przebiegu ustawiał Domatowu „Natana Ramsa".
- 🟡 **`listFiles` zwraca `entries`, nie `files`**, a listing `/` nie pokazuje katalogów.
  Czytanie złego klucza sugeruje, że batch nic nie utworzył, mimo że utworzył wszystko.
- 🟡 **Nie ma akcji czytania pliku** — treści nie da się odczytać z API, weryfikuje je
  dopiero `done` albo podgląd `filesystem_preview.html`.
- `ziemniaki` przechodzą w liczbie mnogiej, mimo reguły „mianownik w liczbie pojedynczej"
  z treści zadania. Nie zmieniać na `ziemniak` bez powodu — tak zaakceptował walidator.

## Work Guidance
- `reset` jest darmowy, więc iterowanie nic nie kosztuje poza czasem.
- Zmiany w parserze weryfikuj testem zgodności z `food4cities.json` przed dotknięciem huba
  — wyłapał trzy osobne usterki, każdą cichą.

## Verification
- `uv run pytest tasks/s04e04_filesystem/` — 30 testów, zero sieci.
- `uv run run.py solve s04e04 --dry-run` — buduje pełną strukturę na żywo i pokazuje
  finalne wywołanie zamiast je wysyłać; stan da się obejrzeć przez `listFiles`.
- Flaga z huba to ostateczna weryfikacja.

## Child DOX Index
- None.
