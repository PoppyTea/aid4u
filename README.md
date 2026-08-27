# aid4u

Rozwiązania zadań kursu **AI_Devs 4** wraz z własną infrastrukturą do ich uruchamiania.

**Stan: certyfikat zdobyty (2026-08-26) — 20/25 flag głównych + 1 sekretna.**
Wszystkie zadania sezonów 1–3 i pięć wybranych z sezonów 4–5.

## Czym to jest

Zamiast skryptu na zadanie — jeden runner i wspólna warstwa `core/`:

| Warstwa | Rola |
|---|---|
| `core/llm/` | Jeden `LLMClient` nad Anthropic / OpenAI / Gemini / OpenRouter; wybór modelu przez tier (`fast` → `flagship`), nie przez identyfikator |
| `core/hub/` | Klient `hub.ag3nts.org` — retry, cache, walidacja pobranej treści |
| `core/tasks/` | `BaseTask` (Template Method) + rejestr `@task`; zadanie implementuje `fetch_data()` i `solve()`, resztę dostaje z pudełka |
| `core/runtime/` | Kill switch i budżety — żaden przebieg nie ucieka bez limitu czasu i kosztu |
| `core/observability/` | Logfire + Langfuse, instrumentacja wpięta w `BaseTask` |
| `core/server/` | `ServerFactory` (FastAPI) dla zadań wymagających publicznego endpointu |

Rozwiązania żyją w `tasks/sXXeYY_nazwa/`, każde z własnym kontraktem w `AGENTS.md`
opisującym pułapki danego epizodu.

## Uruchomienie

```bash
uv sync
keyring set aid4u APIKEY            # klucz kursu; reszta kluczy analogicznie
uv run run.py solve s01e01          # rozwiąż zadanie
uv run run.py status                # postęp: ile flag, ile do certyfikatu
```

Coś się zapętliło:

```bash
bash scripts/panic.sh
```

## Dla agentów

Repo jest prowadzone w konwencji **DOX** — `AGENTS.md` w każdym istotnym katalogu jest
wiążącym kontraktem dla swojego poddrzewa. Zacznij od `AGENTS.md` w korzeniu i schodź
w dół do katalogu, który zamierzasz zmienić.
