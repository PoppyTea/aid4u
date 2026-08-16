# Reguły recenzji — aid4u

> Docelowa lokalizacja: `.claude/review-rules.md` w repo.
> Odtworzone z reguł widocznych w archiwalnych recenzjach Qodo (ID w nawiasach = oryginalny numer na platformie Qodo, zostawiony dla śladu).
> Reguły task-specific (format `SEC-`, jedna linia na zdarzenie) celowo pominięte — powstawały per zadanie; patrz uwaga na końcu.

> ⚠️ **Zanim zgłosisz cokolwiek jako nowe znalezisko: sprawdź `.issues/todo-4-agent/`** (łącznie
> z `.issues/todo-4-agent/archive/`) — jeśli pozycja już tam jest (aktywna albo przekreślona jako
> naprawiona), zacytuj ją zamiast pisać drugi raz. Pełna konwencja (przekreślanie zamiast
> usuwania, archiwizacja w pełni domkniętych plików): `.issues/AGENTS.md`. To dotyczy Ciebie jako
> recenzenta w tym repo — CodeRabbit nie ma dostępu do tej konwencji i jej nie zastosuje.

## Severity i mapowanie

Trzy poziomy, zgodne z kontraktem wyjściowym skilla `qodo-get-rules` (nagłówek `📋 Qodo Rules Loaded`), żeby lokalny zamiennik czytający ten plik zachował semantykę egzekwowania:

| Severity | Egzekwowanie przy pisaniu kodu | Pasmo w recenzji PR |
|---|---|---|
| `ERROR` | nienegocjowalne; przy zastosowaniu dopisz komentarz dokumentujący zgodność | `Action_required` |
| `WARNING` | domyślnie stosuj; pominięcie wymaga jednozdaniowego uzasadnienia | `Review_recommended` |
| `RECOMMENDATION` | rozważ, gdy pasuje | `Optional` |

---

## R1 — Dokumentacja kontraktów w AGENTS.md (1490944) · `WARNING`

Zmiana zachowania lub kontraktu komponentu wymaga aktualizacji **najbliższego** `AGENTS.md` w kaskadzie (root → `core/` → `tasks/` → `tasks/sXXeYY_*/`).

Wyzwalacze: nowy tryb błędu, nowe zachowanie retry/sleep, zmiana sygnatury publicznej metody, zmiana semantyki zwracanej wartości.

Naruszenie zgłaszaj jako `📘 Naruszenie reguły` / `⚙ Utrzymywalność`.

## R2 — Strategia pozyskiwania danych wejściowych (2519038) · `WARNING`

Sekcja `Ownership` w `AGENTS.md` zadania musi opisywać, **zanim** `solve()` zostanie zaimplementowane:

- źródło i typ wejścia (endpoint, nazwa pliku, format),
- mechanizm uwierzytelnienia,
- zmienność danych (czy snapshot jest stabilny między sesjami / apikey),
- czy i jak używane jest cache'owanie.

Naruszenie: implementacja `solve()` obecna, a którykolwiek z czterech punktów nieudokumentowany.

## R3 — Docstringi publicznych symboli (2603753) · `RECOMMENDATION`

Każda publiczna funkcja, metoda i klasa (nazwa nie zaczyna się od `_`) ma niepusty docstring jako pierwszą instrukcję.

Obejmuje klasy testowe (`TestXxx`) i nadpisania metod bazowych (`solve`, `fetch_data`).

> Uwaga z historii: przy klasach pytest Qodo samo obniżało to do `●● Umiarkowana`. Jeśli uznasz, że testy mają być zwolnione — dopisz tu wyjątek zamiast ignorować zgłoszenia.

## R4 — Testy jednostkowe dla nowego kodu produkcyjnego (1518481) · `WARNING`

Nowy lub zmodyfikowany kod produkcyjny wymaga testów jednostkowych w tym samym PR.

Dla zadań deterministycznych (bez LLM w pętli) minimum to test sekwencji wywołań hubu przez stub/fake — że `solve()` wykonuje kroki protokołu w oczekiwanej kolejności i zwraca właściwy payload.

Testy pokrywające zmiany w `core/` **nie** zaspokajają tej reguły dla nowego modułu w `tasks/`.

## R5 — Pliki niebędące kodem tylko na `main` (2059936) · `RECOMMENDATION`

Zmiany w `.flags.json`, plikach `*.md` i konfiguracji trafiają bezpośrednio na `main`, nie na gałąź funkcjonalną — chyba że najbliższy `AGENTS.md` zawiera jawne odstępstwo.

> Uwaga z historii: to zgłoszenie było u Ciebie **odrzucane** (PR-#46, PR-#21). Albo dopisz odstępstwo do root `AGENTS.md` i usuń tę regułę, albo zostaw ją jako `Opcjonalne`. Trzymanie reguły, którą konsekwentnie odrzucasz, uczy Cię ignorowania całej sekcji.

---

## R6 — Kontrakt pojedynczej submisji *(nowa — z obserwacji)* · `ERROR`

**Status: naruszenie obecne w kodzie** (zweryfikowane 14.08.2026).
`tasks/s02e03_failure/solution.py` — jest `solve()` (223) i `hub.submit()` (269), brak `_submit()` i brak `run()`. `BaseTask.run()` wysyła drugi raz po zakończeniu `solve()`. To uwaga #3 z PR #56, nienaprawiona. Poprawka z PR #57 była task-lokalna (`_submit()` w `MailboxTask`) i z definicji nie objęła `FailureTask`.

`BaseTask.run()` zawsze wykonuje `_submit()` po `solve()`. Zadanie, które woła `hub.submit()` **wewnątrz** `solve()` (pętla feedbacku, protokół wieloetapowy), musi:

- nadpisać `_submit()` tak, by zwracał flagę przechwyconą w `solve()` bez ponownego wywołania hubu, **albo**
- nadpisać `run()`, pomijając bazowy krok submisji.

Dodatkowo: każde bezpośrednie `hub.submit()` w kodzie zadania musi respektować `self.dry_run` — `BaseTask._submit()` jest jedynym miejscem, które to egzekwuje, więc obejście go łamie semantykę `--dry-run` (patrz PR-#51).

Zgłaszaj jako `🐞 Bug` / `≡ Poprawność`, pasmo **Wymaga działania**.

## R7 — Obsługa wyjątków HTTP zawężona do udokumentowanego kodu *(nowa — z obserwacji)* · `ERROR`

**Status: naruszenie obecne w kodzie** (zweryfikowane 14.08.2026).
`tasks/s02e03_failure/solution.py:270-271` — `except httpx.HTTPStatusError as exc: return exc.response.json()`, bez sprawdzenia `status_code` i bez `try/except ValueError`. 401/403/500 są traktowane jak feedback protokołu; niepoprawny JSON w ciele wywali `ValueError`. To uwaga #1 z PR #56, nienaprawiona.
`tasks/s02e04_mailbox/solution.py:165` — do sprawdzenia; szerokie łapanie może tam być celowe (przekazywanie treści 4xx agentowi), ale wymaga jawnego ograniczenia do kodów, dla których to zachowanie jest udokumentowane.

Wzorzec wracał w trzech PR-ach (#51, #56, #57); w #51 i #57 domknięty.

Wymagania:

- `except httpx.HTTPStatusError` musi sprawdzać konkretny kod, dla którego zachowanie jest udokumentowane; pozostałe re-raise.
- `response.json()` na ścieżce błędu zawsze w `try/except ValueError` z sensownym fallbackiem.
- Wartości liczbowe z ciała odpowiedzi (`retry_after`) parsowane defensywnie: brak klucza, typ nienumeryczny, wartość ujemna.
- `@retry` z tenacity bez `reraise=True` podmienia oryginalny wyjątek na `RetryError` — wywołujący łapiący `HTTPStatusError` przestaje działać. Albo `reraise=True`, albo jawna obsługa `RetryError` z rozpakowaniem `last_attempt.exception()`.

## R8 — Spójność `reraise` w metodach dekorowanych `@retry` *(nowa — z obserwacji)* · `WARNING`

**Status: niespójność obecna w kodzie** (zweryfikowane 14.08.2026).

`@retry` z tenacity bez `reraise=True` po wyczerpaniu prób rzuca `tenacity.RetryError`, a nie oryginalny wyjątek. Wywołujący, który łapie `httpx.HTTPStatusError` albo `httpx.TransportError`, przestaje działać — i to po cichu: nie ma błędu składni, nie ma ostrzeżenia, jest tylko obsługa, która nagle nie łapie.

W `core/hub/client.py`:

| Metoda | Linia | `reraise=True` |
|---|---|---|
| `_get_data_plain` | 154 | **brak** |
| `_get_data_503_tolerant` | 167 | **brak** |
| `get_public` | 181 | **brak** |
| `post_api` | 213 | jest (poprawka z PR #57) |

Wymóg: **wszystkie** metody z `@retry` w jednej klasie mają ten sam kontrakt wyjątków. Albo wszędzie `reraise=True`, albo wszędzie jawna obsługa `RetryError` z rozpakowaniem `last_attempt.exception()` — nie mieszać.

> Czy trzy pozostałe metody realnie gryzą, zależy od tego, czy któryś wywołujący łapie wyjątki `httpx` wokół `get_data`. Zanim to zmienisz, sprawdź: `rg -n "get_data|get_public" -B2 -A6 tasks/ core/`. Jeśli nikt nie łapie — to nadal warto ujednolicić, ale jako porządek, nie jako naprawę.

---

## Reguły ad hoc z treści zadania

Qodo generowało reguły z opisu konkretnego zadania (np. „confirmation_code to `SEC-` + 32 znaki ASCII alfanumeryczne", „dokładnie jedno zdarzenie na linię"). Zamiast dopisywać je tutaj ręcznie, recenzent ma czytać `tasks/sXXeYY_*/doc/zadanie.md` dotkniętego zadania i traktować zapisane tam **wymagania formatu odpowiedzi** jako reguły obowiązujące w tym PR — z cytatem odpowiedniego fragmentu w sekcji Dowód.
