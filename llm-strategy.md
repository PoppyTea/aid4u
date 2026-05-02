# Strategia wyboru providera LLM

## Zasada nadrzędna: najpierw darmowe, potem tanie, drogie w ostateczności

Każde zadanie zaczynamy od najtańszej opcji i eskalujemy tylko gdy model
faktycznie sobie nie radzi — nie z góry.

---

## Hierarchia providerów

```
1. Gemini (darmowy tier Google AI Studio)  ← ZAWSZE zaczynamy tutaj
2. OpenRouter free models                  ← fallback gdy Gemini nie daje rady
3. OpenRouter płatny                       ← gdy darmowe modele zawodzą
4. OpenAI (bezpośrednio)                   ← rzadko, tylko konkretne modele
5. Anthropic / Gemini Pro / GPT-5.x        ← złożone planowanie, ostateczność
```

---

## Zmienne środowiskowe (kolejność odzwierciedla priorytety)

```bash
# .env

# ── Preferowane ──────────────────────────────────────────────────────────────
GEMINI_API_KEY="sk-.."
# Darmowy tier w Google AI Studio: gemini-2.5-flash, gemini-2.5-flash-lite
# Preview (zwykle darmowe w AI Studio): gemini-3-flash, gemini-3.1-flash-lite
# ⚠️ Płatne: gemini-2.5-pro, gemini-3.1-pro

OPENROUTER_FREE_API_KEY="sk-.."
# Darmowe modele przez OpenRouter (suffix :free w nazwie modelu)
# Lista aktualna: https://openrouter.ai/models?max_price=0

# ── Fallback ─────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY="sk-.."
# Płatne modele przez OpenRouter — szeroki wybór, często tańsze niż direct API

OPENAI_API_KEY="sk-.."
# Gdy zadanie wymaga konkretnego modelu OpenAI

# ── Szczególne okazje ────────────────────────────────────────────────────────
ANTHROPIC_API_KEY="sk-.."
# claude-haiku-4-5-20251001, claude-sonnet-4-6
# Zadania wieloetapowe, złożone planowanie, gdy tańsze modele zawodzą
```

---

## Kiedy eskalować model

| Sygnał | Akcja |
|---|---|
| Model zwraca złe wyniki przy prostym zadaniu | Popraw prompt, spróbuj jeszcze raz |
| Model konsekwentnie myli się w logice (3+ próby) | Przejdź poziom wyżej w hierarchii |
| Zadanie wymaga function calling z wieloma narzędziami | Zacznij od Gemini 2.5 Flash, fallback Sonnet |
| Zadanie z limitem czasu (np. windpower — 40s) | Od razu użyj szybkiego modelu |
| Zadanie agentowe z wieloma krokami | Gemini 2.5 Flash lub Sonnet, nie haiku |
| Vision (obrazki, PNG planszy) | Gemini 2.5 Flash (świetny multimodal, darmowy) |
| Złożone rozumowanie wieloetapowe | gemini-3.1-pro lub claude-sonnet-4-6 |

---

## Modele referencyjne (stan: kwiecień 2026)

### Gemini — Google AI Studio
Modele stabilne są zalecane do użytku produkcyjnego.
Modele `preview` mogą być dostępne za darmo w AI Studio, ale mają restrykcyjniejsze rate limity.

| Model | Tier | Zastosowanie |
|---|---|---|
| `gemini-2.5-flash` | stabilny, darmowy | **domyślny** — szybki, dobry stosunek ceny do jakości |
| `gemini-2.5-flash-lite` | stabilny, darmowy | ultra szybkie/tanie — proste klasyfikacje, tagging |
| `gemini-3-flash` | preview | nowszy, frontier-class przy ułamku kosztów |
| `gemini-3.1-flash-lite` | preview | najnowszy, lekki, frontier-class |
| `gemini-2.5-pro` | stabilny, ⚠️ płatny | złożone zadania, gdy Flash nie wystarczy |
| `gemini-3.1-pro` | preview, ⚠️ płatny | najtrudniejsze zadania, zaawansowane kodowanie agentowe |

> ⚠️ `gemini-2.0-flash` i `gemini-2.0-flash-lite` są **wycofane** — nie używaj.

### OpenRouter — darmowe modele (sufiks `:free`)
Lista zmienia się dynamicznie — zawsze sprawdź aktualną:
https://openrouter.ai/models?max_price=0

### OpenAI (bezpośrednio lub przez OpenRouter)

| Model | Tier | Zastosowanie |
|---|---|---|
| `gpt-5.4-nano` | płatny, najtańszy | proste zadania, gdy Gemini zawodzi |
| `gpt-5.4-mini` | płatny | kodowanie, agenci jako subagenci |
| `gpt-4.1-nano` | płatny, tani | alternatywa dla nano z poprzedniej generacji |
| `gpt-4.1-mini` | płatny | dobry balans cena/jakość |
| `gpt-5.4` | płatny, drogi | agentic workflows, profesjonalne zadania |
| `o3-mini` | płatny, reasoning | zadania wymagające rozumowania krok po kroku |
| `o4-mini` | płatny, reasoning | szybszy/tańszy reasoning, poprzednik gpt-5 mini |
| `o3` | płatny, drogi | złożone reasoning, poprzednik GPT-5 |

> `gpt-4o` i `gpt-4o-mini` nadal działają, ale GPT-5.x i GPT-4.1.x to aktualna generacja.

### Anthropic
| Model | Zastosowanie |
|---|---|
| `claude-haiku-4-5-20251001` | szybkie/tanie zadania (gdy Gemini Flash zawodzi) |
| `claude-sonnet-4-6` | złożone planowanie, agenci, trudne function calling |
| `claude-opus-4-6` | ostateczność — najwyższa jakość, najwyższy koszt |

---

## Jak to wygląda w praktyce

```bash
# Pierwsze podejście — zawsze Gemini 2.5 Flash (stabilny, darmowy)
uv run run.py solve s01e02 --model gemini-2.5-flash

# Prostsze zadanie? Ultra lekki model
uv run run.py solve s01e02 --model gemini-2.5-flash-lite

# Nie działa? Nowszy preview Gemini (frontier-class)
uv run run.py solve s01e02 --model gemini-3-flash

# Nadal nie? OpenRouter free
uv run run.py solve s01e02 --model openrouter/meta-llama/llama-3.3-70b:free

# Złożone zadanie agentowe — od razu Sonnet
uv run run.py solve s04e03 --model claude-sonnet-4-6

# Najtrudniejsze zadanie z wieloetapowym planowaniem
uv run run.py solve s04e03 --model gemini-3.1-pro
```

---

## TODO dla implementacji (nie dotyczy s01e01)

`core/llm/factory.py` wymaga rozszerzenia o:
- `OpenRouterAdapter` — OpenRouter udostępnia OpenAI-compatible API,
  wystarczy zmienić `base_url` w `OpenAIAdapter` na `https://openrouter.ai/api/v1`
- Prefiks routingu w `create_provider()`:
  - `gemini-*` → GeminiAdapter (już jest, obsługuje gemini-2.5-* i gemini-3-*)
  - `openrouter/*` → OpenRouterAdapter (do dodania)
  - `claude-*` → AnthropicAdapter (już jest)
  - `gpt-* / o1-* / o3-* / o4-*` → OpenAIAdapter (już jest)
