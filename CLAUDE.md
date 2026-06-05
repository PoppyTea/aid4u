# CLAUDE.md — Projekt AI_Devs 4 (aid4u)

Witamy w repozytorium kursu AI Devs 4. Ten plik jest centralnym indeksem projektu.

---

## 🚀 Szybki start
- **Zadanie dnia:** Znajdź odpowiedni folder w `/tasks` i użyj `uv run run.py solve sXXeYY`.
- **Modele LLM:** Zawsze sprawdzaj `models-reference.md` przed zmianą modelu.
- **Observability:** `setup_observability()` musi być zawsze w pierwszej linii skryptu.
- **MCP:** Używaj serwerów dokumentacji (`langfuse`, `logfire`, `context7`) zamiast bazować na treningu, jeśli API biblioteki może być niestabilne.

---

## 🗺️ Gdzie szukać informacji (Index)

| Temat | Dokumentacja |
| :--- | :--- |
| **Domyślne modele / Strategia LLM** | `models-reference.md` oraz `strategy/strategy_llm_v1.0.0.md` |
| **Dekompozycja zadań (JSON format)** | `strategy/strategy_task_decomposition_v1.0.0.md` |
| **Workflow implementacji zadań** | `strategy/tasks/workflow.md` |
| **Struktura infrastruktury (`core/`)** | Zobacz drzewo projektu w `README.md` |
| **MCP (Logfire, Langfuse, Context7)** | `.claude/settings.json` (skonfigurowane serwery) |

---

## 🛠️ Architektura i Stack
- **Python 3.12+**, `uv` jako manager.
- **Wzorce projektowe:**
    - `Strategy/Adapter`: `core/llm/adapters/`
    - `Template Method`: `core/tasks/base.py`
    - `Registry`: `@task` dekorator
    - `Chain of Responsibility`: `core/llm/middleware.py`

---

## ⚙️ Najczęstsze komendy
```bash
uv sync                      # Instalacja środowiska
uv run run.py solve sXXeYY   # Rozwiąż zadanie
uv run pytest                # Szybkie testy jednostkowe
./deploy/deploy.sh           # Deployment na VPS
```

---

## ⚠️ Zasady pracy
1. **TDD:** Testy jednostkowe muszą powstać PRZED implementacją logiki.
2. **LLMClient:** Nie używaj bezpośrednio SDK (anthropic/openai/gemini), korzystaj wyłącznie z `LLMClient`.
3. **Observability:** Używaj automatycznej instrumentacji Logfire. Ręczne spany przez `@observe` tylko dla skomplikowanej logiki biznesowej.
4. **Rate Limit:** Jeśli napotkasz `503`, używaj `hub.get_data_503_tolerant()` zamiast zwykłego fetchera.
