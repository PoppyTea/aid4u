# s04e05_foodwarehouse Module

## Purpose
Utworzenie **po jednym zamówieniu magazynowym na każde miasto** z `food4cities.json`
(8 miast), każde z poprawnym `creatorID`, kodem `destination` i podpisem SHA1
wygenerowanym na danych użytkownika z bazy SQLite. **Zero LLM.**

**Rozwiązane (2026-08-24)** — flaga `{FLG:JUSTEATIT}`, za pierwszym podejściem,
koszt $0.00. Drugie zadanie końcówki, po `s05e03`.

## Ownership
- `warehouse.py`: klient narzędzi (`call`/`query`) + `select_all()` ze stronicowaniem.
- `solution.py`: `@task("s04e05", hub_name="foodwarehouse")` — `reset` → mapy →
  twórca → 8× (podpis, `create`, `append` batch) → zwraca `{"tool": "done"}`.
- `test_solution.py`: 10 testów offline — stronicowanie, złączenie po nazwie, wybór twórcy.
- `probe.py`: sonda — wywołania narzędzi API w formie JSON, surowe odpowiedzi huba.
- `doc/`: treść zadania i fabuła, materiał referencyjny.
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

- 🟡 **Cztery zaszczepione zamówienia zostają i nie przeszkadzają.** `reset` przywraca
  stan z zamówieniami dla Susza, Rewala, Biskupca i Hela — miast spoza `food4cities.json`.
  Sprawdzone: `done` zwraca flagę mimo ich obecności, więc `orders.delete` nie jest
  potrzebne. „Bez nadmiarów" z treści zadania dotyczy pozycji WEWNĄTRZ naszych zamówień.
- Twórcą może być dowolny aktywny użytkownik roli **2 („Obsługa transportów")** — nie
  jeden konkretny. Wszystkie cztery zaszczepione zamówienia mają twórców z tej roli
  (`creatorID` 2, 5, 7, 8); wybór roli wyszedł z tej obserwacji, nie z nazwy.

## Rozstrzygnięcia rekonesansu
- ✅ **`s04e05` NIE zależy od `s04e04`.** `{"tool":"help"}` odpowiada pełną dokumentacją
  bez zaliczonego e04 — fabuła („mamy już informacje, które miasto oferuje jaki towar")
  jest ciągłością narracyjną, nie techniczną. Punkt #2 z listy „Do sprawdzenia
  empirycznie" w `../s04/requirements/season.md` zamknięty; kolejność ataku bez zmian.

## Work Guidance
- **Bez LLM.** Zadanie to pobranie danych, przeliczenie i wysłanie — ocena powtórzona
  w komentarzach kursu: *„użycie agentów tutaj będzie sztuką dla sztuki"*. Wzorzec
  z `s05e03_shellaccess` (deterministyczny łańcuch zapytań + parser) zastosowany wprost.
- Eksploracja: `uv run python -m tasks.s04e05_foodwarehouse.probe '{"tool":"help"}'`.
- Rozmiar strony bierz z odpowiedzi (`limit`), nigdy z założenia — `select_all()` już to robi.

## Verification
- `uv run pytest tasks/s04e05_foodwarehouse/` — 10 testów, zero sieci.
- `uv run run.py solve s04e05 --dry-run` — tworzy komplet zamówień na żywo i pokazuje
  finalne wywołanie zamiast je wysyłać (stan da się obejrzeć przez `orders get`).
- Flaga z huba to ostateczna weryfikacja.

## Child DOX Index
- None.
