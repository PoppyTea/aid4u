# s02e04_mailbox Module

## Purpose
Przeszukanie aktywnej skrzynki mailowej operatora systemowego (API `zmail`) w
poszukiwaniu wiadomości od donosiciela "Wiktora" (domena `proton.me`), żeby
wydobyć trzy wartości: `date` (data planowanego ataku), `password` (hasło do
systemu pracowniczego), `confirmation_code` (format `SEC-` + 32 znaki = 36 razem).

**Rozwiązane (2026-08-07)** — flaga `{FLG:TRAITOR}` w `.flags.json`.

## Ownership
- `solution.py`: `MailboxTask`, zarejestrowana przez `@task("s02e04", hub_name="mailbox")`.
- Dane wejściowe: **żywe, nie statyczny plik** — `POST /api/zmail` przez `hub.post_api()`.
  Skrzynka jest cały czas w użyciu — nowe maile mogą wpływać w trakcie pracy (empirycznie
  potwierdzone: kod potwierdzenia przyszedł błędny, a 2 minuty później nadeszła poprawka w
  osobnym mailu w tym samym wątku), więc brak wyniku nie znaczy że informacji nie ma
  (spróbować ponownie — stąd narzędzie `wait_seconds`, patrz Local Contracts).
- `doc/`: treść zadania, fabuła, destylat komentarzy kursu — materiał referencyjny,
  nieużywany w runtime.
- `prompts.py`: system prompt agenta + kickoff message.
- `test_solution.py`: mock `HubClient`, weryfikuje dispatch narzędzi, walidację formatu
  `confirmation_code`, throttle/budżet `wait_seconds`, gating `dry_run` — bez sieci.

## Local Contracts
- **Protokół `zmail` (odkryty na żywo przez `help`, 2026-08-07):** `help`, `getInbox`
  (`page`, `perPage` 5-20), `getThread` (`threadID` → lista wiadomości bez treści),
  `getMessages` (`ids`: rowID/messageID/tablica → pełna treść), `search` (`query`: słowa,
  `"fraza"`, `-wyklucz`, `from:`, `to:`, `subject:`, `subject:"fraza"`, `subject:(fraza)`,
  `OR`/`AND`; brak operatora = `AND`), `reset` (czyści licznik requestów na apikey).
- **Rate limit jest realny**, mimo że treść zadania go nie wspomina — potwierdzone
  empirycznie (`{"code": -9999, "message": "Za często wykonujesz zapytania. Zwolnij."}`,
  HTTP 429, bez `retry_after` w body). `HubClient.post_api()` ma teraz wbudowany retry z
  exponential backoffem na 429/5xx, `reraise=True` (patrz `core/AGENTS.md`) — `zmail_action`
  w `solution.py` dodatkowo throttluje wywołania w kodzie (nie zostawione modelowi) jako
  drugą linię obrony.
- **Narzędzia agenta** (`LLMClient.run_agent_loop`, wzorzec z `s01e02_findhim`):
  `zmail_action(action, params)` — cienki, generyczny wrapper na `post_api`; `action` jawnie
  wygrywa nad ewentualnym `params["action"]`, `params` nie-dict zwraca błąd zamiast wywalać
  wyjątek. 4xx (np. zła akcja) trafia do agenta jako ustrukturyzowany feedback; 5xx po
  wyczerpaniu retry w `HubClient` NIE przerywa całego `solve()` — `run_agent_loop()` łapie
  wyjątek na poziomie wykonania narzędzia i zamienia go w generyczny komunikat błędu widoczny
  dla agenta (patrz `core/llm/client.py`), więc to "twardy sygnał że coś nie działa", nie
  wyjątek przerywający `solve()`. `submit_answer(password, date, confirmation_code)` —
  `confirmation_code` ma LOKALNĄ bramkę walidacji formatu (SEC- + 32 znaki ASCII
  alfanumeryczne) przed jakąkolwiek siecią; dopóki nie przejdzie, wywołanie w ogóle nie
  dociera do huba i `state["last_submission"]` NIE jest ustawiane (żeby niepoprawna próba
  nigdy nie stała się fallbackiem dla finalnego submit). `password`/`date` nie mają takiej
  bramki — mogą być puste, byle kod był poprawny. Respektuje `self.dry_run`. `wait_seconds
  (seconds)` — per-call clamp 5-60s + globalny budżet 300s na całe `solve()`, oba wymuszone
  w kodzie.
- **Bez duplikatu `/verify` na ścieżce sukcesu** — `submit_answer` woła `hub.submit()`
  naprawdę wewnątrz pętli; `MailboxTask` nadpisuje `_submit()` żeby pominąć redundantny
  drugi POST z automatycznego finału `BaseTask.run()`, jeśli flaga została już złapana w
  pętli (zamiast dublować żywe wywołanie na hubie, który i tak rate-limituje).
- **System prompt musi jawnie nakazywać wywołanie `submit_answer` przed zakończeniem
  pracy** — bez tej instrukcji obserwowano (2026-08-07, Haiku) agenta kończącego pętlę bez
  ani jednej próby wysyłki, mimo że miał już poprawne wartości w kontekście. Prompt musi też
  jasno rozróżniać, że tylko `confirmation_code` ma lokalną bramkę — wcześniejsza wersja
  sugerowała że każde pole można zostawić puste i i tak dostać feedback z huba, co było
  nieprawdą dla `confirmation_code` (złapane w code review PR #57, poprawione).

## Work Guidance
- **Rewizja wyboru modelu (2026-08-07):** treść zadania sugeruje tani model
  (`google/gemini-3-flash-preview`) jako wystarczający. W tym repo `claude-haiku-4-5`
  (domyślny start wg `strategy/llm-selection.md`) **zawiódł 3x pod rząd** na żywym
  przebiegu — kończył pętlę bez wywołania `submit_answer` mimo instrukcji, albo gubił się w
  odkrywaniu protokołu. `claude-sonnet-5` rozwiązał zadanie za pierwszym razem (8 iteracji,
  jeden `submit_answer`, flaga od razu) — dokładnie sygnał "function calling z wieloma
  narzędziami → zacznij od Sonnet 5" ze `strategy/llm-selection.md`, potwierdzony
  empirycznie, nie tylko teoretycznie. Dla tego zadania: **zaczynaj od `claude-sonnet-5`,
  nie od Haiku**.
- Podejście agentowe z function calling (szukaj → czytaj → wyciągaj wnioski → szukaj dalej)
  pasuje tu lepiej niż sztywny skrypt — potwierdzone w praktyce, nie tylko wg treści
  zadania.

## Verification
- `uv run run.py solve s02e04 --model claude-sonnet-5` — flaga w konsoli i `.flags.json`.
- `uv run pytest tasks/s02e04_mailbox/` — testy dispatchu narzędzi (bez sieci, mock hub).

## Child DOX Index
- None.
