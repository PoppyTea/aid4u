# Propozycje reguł — web recon 2026-08-18

> **Status: PROPOZYCJA.** Nie są to aktywne reguły `rNN` — kandydaci z timeboxowanego
> (~15 min) rozpoznania branżowych standardów code review dla projektów solo
> Python/LLM-agent, każdy z konkretnym uzasadnieniem z tego repo, nie z ogólnej wiedzy
> "dobrych praktyk". Wymagają **jawnej akceptacji usera** przed przeniesieniem do
> `strategy/rules/<kategoria>/rNN-slug.md` — auto-adopcja zakazana (patrz
> `strategy/rules/AGENTS.md`, Work Guidance).

## 1. Timeout na wszystkich wywołaniach zewnętrznych
`core/hub/client.py:60` ustawia jawnie `httpx.Client(timeout=30.0)`; `native_tool_bash.py`
ma jawny `timeout: float = 30.0` na każdym poleceniu shell. Ale `core/llm/adapters/`
(`anthropic.py`, `openai.py`, `gemini.py`, `openrouter.py`) — sprawdzone przez
`rg -n "timeout" core/llm/` — **nie mają** jawnego timeoutu na klientach SDK. Wywołanie
LLM jest w tym repo najdroższym i najbardziej podatnym na zawieszenie punktem (sieć +
provider pod obciążeniem), a jedyne dwa miejsca z jawnym timeoutem to akurat te
mniej ryzykowne (hub kursu, lokalny bash). Reguła: każdy klient SDK/HTTP w
`core/llm/adapters/` dostaje jawny timeout, symetrycznie do `core/hub/client.py`.

## 2. Spójność structured logging
Na 28 wywołań `logfire.(info|warning|error)` w `core/` tylko jedno
(`core/hub/client.py:93`: `logfire.warning(f"No flag in response for {task}",
response=result)`) przekazuje strukturalny kwarg obok wiadomości f-string — reszta to
gołe f-stringi. `strategy/observability.md` już definiuje kontekst obowiązkowy dla
zdarzeń Langfuse (`sessionId`, `agentId`, `promptVersion`) — logi Logfire nie mają
analogicznego wymogu. Reguła: `logfire.*()` w kodzie produkcyjnym (`core/`) dołącza
istotne wartości jako kwargs (nie tylko interpoluje w treść), żeby były filtrowalne/
queryowalne w panelu, nie tylko czytelne jako tekst.

## 3. Idempotency-awareness przy retry na mutujących wywołaniach
`core/hub/client.py:213` (`post_api`) ma `@retry` z exponential backoff na 429/5xx/
transport errors — ale `post_api` jest generyczne POST używane m.in. do akcji
mutujących stan po stronie hubu (`/api/zmail`, `/api/packages`, patrz docstring metody).
Retry po transport error/5xx zakłada, że żądanie **nie** dotarło do serwera — ale hub
kursu bywa niestabilny (503, ciała HTML zamiast oczekiwanego formatu — patrz
`core/net.py`), więc możliwość, że serwer przetworzył akcję i tylko odpowiedź się zgubiła,
nie jest zerowa. To inny problem niż r13 (single-submission na poziomie `BaseTask`) —
tu chodzi o retry tenacity samego transportu. Reguła: akcje POST bez naturalnej
idempotencji (nie GET, nie idempotentny PUT) dostają komentarz jawnie oceniający ryzyko
podwójnego efektu przy retry, albo idempotency key, jeśli endpoint hubu to wspiera.

## 4. Zakaz logowania wartości sekretów — reguła jawna, nie tylko dyscyplina
`core/secrets.py` dziś loguje wyłącznie **nazwy** kluczy (`logfire.info(f"Stored {key} in
keyring")`, linie 132/138/140) — nigdy wartości, co jest poprawne, ale to dyscyplina
autora tego jednego pliku, nie egzekwowana reguła repo. Żaden inny plik w `core/`/`tasks/`
ma zakaz logowania surowej treści sekretu — przy dodaniu kolejnego adaptera/integracji
(np. nowy provider LLM, webhook) nic nie chroni przed przypadkowym
`logfire.info(f"Called API with key={api_key}")`. Reguła: `ERROR` na jakikolwiek
`logfire.*`/`print` przekazujący zmienną pochodzącą z `core/secrets.py::SecretManager`
(albo `config.py` pól `*_key`/`*_token`) bez jawnego maskowania.

## 5. Audyt zależności (supply-chain)
`.coderabbit.yaml` stwierdza wprost: "repo jest publiczne, ale <10 gwiazdek". `uv.lock`
pinuje m.in. `anthropic`, `httpx`, `keyring`, `google-genai` — żaden mechanizm w repo
(`rg -n "pip-audit|safety|dependabot|renovate"` — zero trafień poza jednym niezwiązanym
plikiem danych) nie skanuje ich pod kątem CVE. `deprecation-watch` sprawdza deprecation/
breaking changes, ale nie podatności bezpieczeństwa. Reguła: rutyna `cleanup` albo nowa
comiesięczna rutyna uruchamia `uv run pip-audit` (albo odpowiednik) i zgłasza CVE o
severity High+ jako issue `security` w Linear.
