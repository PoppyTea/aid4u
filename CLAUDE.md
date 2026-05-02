# aid4u — AI Devs 4 Task Runner

---

## ⚠️ ZASADY MODELI LLM — przeczytaj zanim zaczniesz kodować

**Obowiązuje zawsze, w każdym pliku, który dotykasz.**

### Domyślny model projektu: `gemini-2.5-flash`

```python
# ✅ Jedyne akceptowalne wartości domyślne w kodzie:
model: str = "gemini-2.5-flash"       # domyślny w run.py i adapterach
model: str = "gemini-2.5-flash-lite"  # tylko dla bardzo prostych wywołań

# ❌ NIGDY nie ustawiaj jako domyślnych:
model: str = "gpt-4o-mini"       # przestarzałe
model: str = "gpt-4o"            # przestarzałe
model: str = "gemini-2.0-flash"  # WYCOFANE
model: str = "gemini-1.5-flash"  # WYCOFANE
```

### Hierarchia wyboru — ZAWSZE w tej kolejności:
1. `gemini-2.5-flash` lub `gemini-2.5-flash-lite` — darmowy tier, zacznij tu
2. `gemini-3-flash` / `gemini-3.1-flash-lite` — nowsze preview, przed eskalacją do płatnych
3. `claude-haiku-4-5-20251001` — płatny fallback, gdy Gemini nie daje rady
4. `claude-sonnet-4-6` — złożone zadania agentowe, function calling
5. `gpt-5.4-nano` / `gpt-5.4-mini` / `o4-mini` — alternatywa OpenAI

### Gdzie zmieniać domyślne wartości modeli:
- `run.py` → opcja `--model` w `typer.Option(...)`
- `core/llm/adapters/gemini.py` → `__init__` default
- `core/llm/adapters/openai.py` → `__init__` default
- `core/llm/adapters/anthropic.py` → słownik `ANTHROPIC_MODELS`

Szczegóły: `models-reference.md` | Strategia: `llm-strategy.md`

---

## ⚠️ ZASADY MCP — kiedy sięgać po serwery dokumentacji

Projekt ma skonfigurowane trzy MCP serwery dokumentacyjne w `.claude/settings.json`.
Nie używaj wiedzy treningowej gdy API biblioteki mogło się zmienić — sprawdź MCP.

### Langfuse MCP (`langfuse-docs`)

**Używaj ZAWSZE przed:**
- jakąkolwiek zmianą w `core/observability/setup.py` lub `decorators.py`
- dodawaniem Langfuse trace do nowego zadania
- debugowaniem śledzenia wywołań LLM

**Dlaczego krytyczne:** Langfuse jest na v4 (v2→v3→v4 — trzy breaking changes).
Wiedza treningowa zawiera stare wzorce. Kluczowe zmiany v3→v4:

```python
# ❌ v3 (STARE — nie używaj)
langfuse.update_current_trace(user_id="u1", session_id="s1")
langfuse.start_span(name="x")
langfuse.start_generation(name="x", model="gpt-4")

# ✅ v4 (AKTUALNE)
from langfuse import get_client, propagate_attributes, observe

with propagate_attributes(user_id="u1", session_id="s1"):
    result = call_llm(...)

langfuse = get_client()
langfuse.start_observation(name="x")                            # był start_span
langfuse.start_observation(name="x", as_type="generation", ...) # była start_generation
```

### Logfire MCP (`logfire-docs`)

**Używaj przed:**
- zmianami w konfiguracji `logfire.configure()` lub instrumentacji
- pytaniami o `instrument_anthropic()`, `instrument_httpx()`, `instrument_fastapi()`
- konfigurowaniem eksportu OTEL lub nowych integracji

**Ważne zasady bez potrzeby MCP:**
- `LOGFIRE_TOKEN` = **Write Token** tylko (Read Token nie jest potrzebny)
- `OTEL_EXPORTER_OTLP_*` = NIE potrzebne (używamy Logfire SDK, nie raw OTEL)
- Dev sessions (tymczasowe tokeny 7-dniowe) = NIE używamy, mamy stały projekt

### Context7 MCP (`context7`)

**Używaj gdy:**
- implementujesz coś opartego o zewnętrzny SDK (FastAPI, httpx, Pydantic, tenacity, Typer)
- nie jesteś pewien czy API biblioteki mogło się zmienić od Twojego treningu
- widzisz deprecation warning w kodzie

**Nie musisz używać dla:** czystej logiki Pythona, standardowych struktur danych.

---

## Cel projektu

Rozwiązywanie zadań z kursu AI Devs 4 (aid4u). Deadline: **01.09.2026**, wymagane minimum 20/25 zadań.
Hub zadań: https://hub.ag3nts.org (logowanie przez EasyCart)

---

## Stack technologiczny

- **Python 3.12+** z `uv` jako package manager
- **LLM:** Gemini (primary, darmowy), Anthropic + OpenAI (płatny fallback) — Adapter pattern
- **Observability:** Logfire (spany/HTTP) + Langfuse (LLM traces/koszty)
- **HTTP:** httpx (z auto-instrumentacją Logfire)
- **Server:** FastAPI + uvicorn (zadania wymagające publicznego endpointu)
- **CLI:** Typer + Rich
- **Testy:** pytest + pytest-mock + respx
- **Deploy:** VPS własny (2GB RAM / 25GB) + systemd

---

## Wzorce projektowe w projekcie

| Wzorzec | Gdzie | Po co |
|---|---|---|
| **Strategy + Adapter** | `core/llm/adapters/` | Zamienność providerów LLM |
| **Facade** | `core/llm/client.py` | Ukrywa middleware pipeline przed zadaniami |
| **Chain of Responsibility** | `core/llm/middleware.py` | Rate limit → cost track → provider call |
| **Template Method** | `core/tasks/base.py` | Stały przepływ: fetch → solve → submit |
| **Registry / Plugin** | `core/tasks/base.py` `@task` dekorator | Automatyczne odkrywanie zadań przez CLI |
| **Factory** | `core/llm/factory.py`, `core/server/factory.py` | Tworzenie adapterów i serwerów |
| **Repository + Cache** | `core/hub/client.py`, `core/hub/cache.py` | Izolacja HTTP, cache przy TDD |
| **Decorator** | `core/observability/decorators.py` | Ręczne spanowanie funkcji |

---

## Struktura projektu

```
aid4u/
├── run.py                          # CLI (Typer) — główny punkt wejścia
├── pyproject.toml
├── .env                            # klucze API (NIE commitować)
│
├── core/                           # infrastruktura — NIE modyfikuj bez powodu
│   ├── config.py                   # Singleton Config (keyring + .env fallback)
│   ├── observability/
│   │   ├── setup.py                # ⚠️ wywołaj jako PIERWSZE w każdym skrypcie
│   │   └── decorators.py           # @observe do ręcznego spanowania
│   ├── llm/
│   │   ├── client.py               # LLMClient Facade — używaj w zadaniach
│   │   ├── factory.py              # tworzy adapter na podstawie nazwy modelu
│   │   ├── middleware.py           # Chain: RateLimit → CostTrack → ProviderCall
│   │   ├── base.py                 # LLMProvider ABC (Strategy interface)
│   │   ├── types.py                # LLMMessage, LLMResponse, Tool, ToolCall
│   │   └── adapters/
│   │       ├── anthropic.py        # Adapter Anthropic SDK
│   │       ├── openai.py           # Adapter OpenAI SDK
│   │       └── gemini.py           # Adapter Gemini SDK
│   ├── hub/
│   │   ├── client.py               # HubClient — wszystkie requesty do hubu
│   │   └── cache.py                # LocalCache — przyśpiesza iteracje TDD
│   ├── server/
│   │   └── factory.py              # ServerFactory — FastAPI z Logfire i health
│   └── tasks/
│       └── base.py                 # BaseTask (Template Method) + TASK_REGISTRY
│
├── tasks/                          # tutaj żyją zadania — każde jako pakiet
│   ├── __init__.py                 # auto-import wszystkich zadań przy starcie
│   └── s01e01_people/
│       ├── __init__.py
│       ├── solution.py             # @task("s01e01") class PeopleTask(BaseTask)
│       ├── prompts.py              # stałe z promptami — osobno od logiki
│       └── test_solution.py        # testy jednostkowe + integration test
│
├── tests/
│   └── core/                       # testy infrastruktury
│       ├── test_hub.py
│       └── test_llm_client.py
│
└── deploy/
    ├── deploy.sh                   # ./deploy/deploy.sh [service-name]
    └── systemd/
        └── aid4u-proxy.service     # szablon jednostki systemd
```

---

## Jak dodać nowe zadanie

1. Utwórz folder: `tasks/s0XeYY_nazwa/`
2. Napisz testy w `test_solution.py` (najpierw — TDD!)
3. Zaimplementuj `solution.py`:
   ```python
   from core.tasks import BaseTask, task

   @task("s0XeYY")       # ← nazwa musi pasować do nazwy w hubie
   class MojaTask(BaseTask):

       def fetch_data(self):                    # opcjonalne
           return self.cache.get_or_fetch(
               "plik.csv",
               lambda: self.hub.get_data("plik.csv"),
           )

       def solve(self, data) -> ...:           # WYMAGANE
           answer = ...                        # logika rozwiązania
           return answer                       # zwróć odpowiedź do /verify
   ```
4. Dodaj eksport w `tasks/s0XeYY_nazwa/__init__.py`
5. Uruchom: `uv run run.py solve s0XeYY`

Zadania wymagające serwera HTTP (proxy, negotiations, domatowo):
```python
from core.server import ServerFactory, run_server

app = ServerFactory.create("s01e03-proxy")

@app.post("/")
async def handle(body: Request) -> Response:
    ...

if __name__ == "__main__":
    run_server(app, port=8000)
```

---

## Komendy

```bash
# Instalacja
uv sync

# Uruchomienie zadania
uv run run.py solve s01e01
uv run run.py solve s01e01 --model gemini-2.5-flash
uv run run.py solve s01e01 --dry-run          # bez wysyłania do hubu

# Lista i postępy
uv run run.py list
uv run run.py status

# Testy
uv run pytest                                  # unit testy (offline, szybkie)
uv run pytest -m integration                   # integration (wymaga .env i sieci)
uv run pytest tasks/s01e01_people/ -v          # testy konkretnego zadania
uv run pytest --cov=core --cov-report=term-missing  # pokrycie kodu

# Deployment
./deploy/deploy.sh                             # push na VPS
./deploy/deploy.sh aid4u-proxy                 # push + restart serwisu
```

---

## Konwencje

### Testy (TDD)
- **Warstwa 1 (unit):** szybkie, offline, mock LLM i HTTP. Domyślnie uruchamiane.
- **Warstwa 2 (integration):** `@pytest.mark.integration` — tylko świadomie, z flagą `-m integration`.
- Czyste funkcje (`parse_csv`, `filter_candidates`, `format_answer`) — testowalność bez mocków.
- Każdy nowy plik logiki → odpowiednie testy PRZED implementacją.

### Narzędzia LLM
Zawsze przez `LLMClient` — nigdy bezpośrednio przez SDK:
```python
# ✅ Dobrze
result = self.llm.chat([LLMMessage.user("Pytanie")])
data = self.llm.structured(messages, MySchema)

# ❌ Źle — omija middleware, Logfire, cost tracking
import anthropic
client = anthropic.Anthropic(...)
```

### Modele — kiedy którego używać

Pełna strategia w `llm-strategy.md`. Skrócona ściągawka:

| Model | Provider | Kiedy |
|---|---|---|
| `gemini-2.5-flash` | Gemini (darmowy) | **domyślny** — zacznij tu zawsze |
| `gemini-2.5-flash-lite` | Gemini (darmowy) | ultra szybki — tagging, filtrowanie |
| `gemini-3-flash` | Gemini (preview) | nowszy, frontier-class, zwykle darmowy |
| `gemini-3.1-flash-lite` | Gemini (preview) | najnowszy lekki model |
| `gemini-2.5-pro` | Gemini (płatny) | gdy Flash nie wystarczy |
| `gemini-3.1-pro` | Gemini (płatny) | wieloetapowe planowanie agentowe |
| `claude-haiku-4-5-20251001` | Anthropic (płatny) | szybki fallback gdy Gemini zawodzi |
| `claude-sonnet-4-6` | Anthropic (płatny) | złożona logika, function calling, agenci |
| `claude-opus-4-6` | Anthropic (płatny) | ostateczność — najwyższa jakość |
| `gpt-5.4-nano` | OpenAI (płatny) | tani fallback OpenAI |
| `gpt-5.4-mini` | OpenAI (płatny) | kodowanie, subagenci |
| `o4-mini` | OpenAI (płatny) | reasoning krok po kroku |

> ⚠️ `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-1.5-flash` są **wycofane**.

### Obserwabilność
- `setup_observability()` musi być **pierwszą linią** w każdym skrypcie uruchomieniowym.
- `logfire.instrument_anthropic()` i `logfire.instrument_httpx()` działają automatycznie po setup.
- `@observe("moja_funkcja")` — tylko gdy potrzebujesz ręcznego spanu dla złożonej logiki.
- Langfuse UI: https://cloud.langfuse.com — trace każdego wywołania LLM z tokenami i kosztem.
- Logfire UI: https://logfire.pydantic.dev — HTTP calls, błędy, czasy odpowiedzi.

### Serwery na VPS
```bash
# Nowy serwis
sudo cp deploy/systemd/aid4u-proxy.service /etc/systemd/system/aid4u-mojeserwis.service
sudo vim /etc/systemd/system/aid4u-mojeserwis.service  # zmień ExecStart
sudo systemctl daemon-reload
sudo systemctl enable aid4u-mojeserwis
sudo systemctl start aid4u-mojeserwis
sudo journalctl -u aid4u-mojeserwis -f  # logi w czasie rzeczywistym
```

---

## Typowe problemy

**Rate limiting (zadanie railway, windpower):**
`RateLimitMiddleware` w pipeline obsługuje to automatycznie przez tenacity.
Dla zadania `railway` używaj `hub.get_data_503_tolerant()` zamiast `hub.get_data()`.

**Pętla agentowa nie kończy się:**
`LLMClient.run_agent_loop()` ma `max_iterations=10` domyślnie.
Jeśli agent się zapętla — zwiększ limit lub popraw prompt systemowy.

**Cache powoduje stare dane:**
`rm -rf .cache/` czyści wszystko.
`self.cache.invalidate("plik.csv")` czyści jeden wpis (np. po resecie planszy electricity).

**Brak flagi w odpowiedzi hubu:**
`hub.get_flag(response)` przeszukuje wszystkie pola odpowiedzi.
Jeśli zwraca None — wydrukuj `response` i sprawdź surową strukturę.

**Zadanie wymaga publicznego URL:**
Używaj VPS + systemd. Stały URL: `http://TWOJ_VPS_IP:PORT`.
Pamiętaj o otwarciu portu: `sudo ufw allow PORT`.

---

## Zadania i ich status

| ID | Nazwa | Typ | Status |
|---|---|---|---|
| s01e01 | people | CSV + LLM tagging | ✅ zaimplementowane |
| s01e02 | findhim | Function calling + geo | 🔲 TODO |
| s01e03 | proxy | HTTP server z pamięcią sesji | 🔲 TODO |
| s01e04 | (multimodalność) | Pliki/obrazy | 🔲 TODO |
| s01e05 | railway | API bez docs, 503 retry | 🔲 TODO |
| s02e02 | electricity | Vision + puzzle | 🔲 TODO |
| s02e04 | mailbox | Agent przeszukujący maile | 🔲 TODO |
| s02e05 | drone | Sterowanie przez API | 🔲 TODO |
| s03e04 | negotiations | Własne narzędzia dla agenta | 🔲 TODO |
| s04e02 | windpower | Async + MD5 + 40s limit | 🔲 TODO |
| s04e03 | domatowo | Mapa + zwiadowcy | 🔲 TODO |
