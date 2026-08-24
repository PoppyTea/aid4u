# s04e05_foodwarehouse Module

## Purpose
Zbudowanie jednego zamówienia magazynowego pokrywającego zapotrzebowanie wszystkich miast
z `food4cities.json`, z podpisem SHA1 wygenerowanym na danych użytkownika z bazy SQLite.
Drugie zadanie końcówki, po `s05e03`.

**Status: scaffolding (2026-08-24).** `solution.py` **do utworzenia** — folder zawiera
rekonesans i materiał referencyjny. Taki stan jest jawnie dopuszczony przez
`tasks/AGENTS.md` (Local Contracts, wyjątek „season kickoff").

## Ownership
- `probe.py`: sonda — wywołania narzędzi API w formie JSON, surowe odpowiedzi huba.
- `doc/`: treść zadania i fabuła, materiał referencyjny.
- `solution.py`: **do utworzenia** — deterministyczny przepływ, bez LLM (uzasadnienie niżej).
- Dane wejściowe: `data/input/s04e05_foodwarehouse/food4cities.json` (677 B, pobrane
  2026-08-24). Statyczne, więc trzymane w repo, nie w `.cache/`.

## Local Contracts
- Całe API idzie przez `POST /verify`, `answer` jako obiekt z kluczem `tool`:
  `orders` (get/create/append/delete), `signatureGenerator`, `database`, `reset`, `done`.
- Baza jest **tylko do odczytu**: dozwolone `SELECT …`, `SHOW TABLES`,
  `SHOW CREATE TABLE t`, `.tables`, `.schema`. Zapisy zablokowane.
- Tabele: `destinations` (40 wierszy), `roles`, `users`.
- `reset` przywraca stan początkowy — próby są darmowe, więc iterowanie nic nie kosztuje.

## Pułapki (zweryfikowane na żywo 2026-08-24)
- 🔴 **Odpowiedź `database` jest paginowana i mówi o tym wprost.** Każda odpowiedź niesie
  `totalTableRows` i `limit`. Dla `destinations`: `totalTableRows: 40`, `limit: 30` —
  naiwny `select * from destinations` oddaje **30 z 40** wierszy i nic o tym nie sygnalizuje
  poza tymi dwoma polami. `limit 30 offset 30` działa i oddaje brakującą dziesiątkę
  (sprawdzone). To jest ta rzecz, na którą staff naprowadzał uczestników słowami
  „zwróć uwagę na to, co jeszcze jest zwracane z bazy".
- 🔴 **Wielkość liter NIE zgadza się między źródłami.** Klucze w `food4cities.json` są
  z małej (`domatowo`, `opalino`), a `destinations.name` z wielkiej (`Domatowo`, `Pyzdry`).
  `where name = 'domatowo'` zwraca **zero wierszy**, `where name = 'Domatowo'` zwraca
  `destination_id: 761834`. To dwie ODRĘBNE pułapki — intel społeczności zlepiał je
  w jedną („domatowo nie ma w tabeli, bo miasto zniszczone"), a naprawa jednej bez
  drugiej nadal daje niekompletne zamówienie.
- 🟡 Zamówienie ma pokryć zapotrzebowanie **dokładnie** — bez niedoborów i bez nadwyżek.

## Rozstrzygnięcia rekonesansu
- ✅ **`s04e05` NIE zależy od `s04e04`.** `{"tool":"help"}` odpowiada pełną dokumentacją
  bez zaliczonego e04 — fabuła („mamy już informacje, które miasto oferuje jaki towar")
  jest ciągłością narracyjną, nie techniczną. Punkt #2 z listy „Do sprawdzenia
  empirycznie" w `../s04/requirements/season.md` zamknięty; kolejność ataku bez zmian.

## Work Guidance
- **Bez LLM.** Zadanie to pobranie danych, przeliczenie i wysłanie — ocena powtórzona
  w komentarzach kursu: *„użycie agentów tutaj będzie sztuką dla sztuki"*. Wzorzec
  z `s05e03_shellaccess` (deterministyczny łańcuch zapytań + parser) stosuje się wprost.
- Eksploracja: `uv run python -m tasks.s04e05_foodwarehouse.probe '{"tool":"help"}'`.
- Przed pisaniem `solution.py`: przegląd sekcji `s04e05` w
  `../s04/requirements/source/community-intel.md`.

## Verification
(brak — `solution.py` jeszcze nie istnieje; docelowo `--dry-run` + flaga z huba)

## Child DOX Index
- None.
