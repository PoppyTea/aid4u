# Aktualne modele LLM — szybka ściągawka

> Stan: kwiecień 2026. Aktualizuj gdy pojawią się nowe modele.
> Pełna strategia wyboru: `llm-strategy.md`

---

## Domyślny model projektu

```
gemini-2.5-flash
```

To jest wartość domyślna `--model` w `run.py` i startowy punkt dla każdego zadania.

---

## Gemini — Google AI Studio

### Stabilne (zalecane do użytku)
| Identyfikator API | Tier | Użyj gdy |
|---|---|---|
| `gemini-2.5-flash` | darmowy | **domyślny** — większość zadań |
| `gemini-2.5-flash-lite` | darmowy | prostszy tagging, filtrowanie CSV |
| `gemini-2.5-pro` | ⚠️ płatny | Flash nie daje rady |

### Preview (zwykle darmowe w AI Studio, mogą być niestabilne)
| Identyfikator API | Użyj gdy |
|---|---|
| `gemini-3-flash` | nowszy, frontier-class, próba przed Sonnetem |
| `gemini-3.1-flash-lite` | najnowszy lekki model |
| `gemini-3.1-pro` | ⚠️ płatny — wieloetapowe planowanie agentowe |

### ❌ Wycofane — NIE UŻYWAJ
- `gemini-2.0-flash` — wycofany
- `gemini-2.0-flash-lite` — wycofany
- `gemini-1.5-flash` — wycofany

---

## Anthropic (płatny fallback)

| Identyfikator API | Użyj gdy |
|---|---|
| `claude-haiku-4-5-20251001` | szybki fallback gdy Gemini zawodzi |
| `claude-sonnet-4-6` | złożona logika, function calling, agenci |
| `claude-opus-4-6` | ostateczność — najwyższy koszt |

---

## OpenAI (płatny fallback, przez OpenRouter lub bezpośrednio)

| Identyfikator API | Użyj gdy |
|---|---|
| `gpt-5.4-nano` | tani fallback OpenAI, proste zadania |
| `gpt-5.4-mini` | kodowanie, subagenci |
| `gpt-4.1-nano` | tańsza alternatywa z poprzedniej generacji |
| `gpt-4.1-mini` | balans cena/jakość poprzedniej generacji |
| `o4-mini` | reasoning krok po kroku |
| `o3` | złożone reasoning, poprzednik GPT-5 |

### ❌ Przestarzałe (działają, ale są starą generacją)
- `gpt-4o`, `gpt-4o-mini` — poprzednia generacja, zastąpione przez GPT-5.x i GPT-4.1.x

---

## Gdzie w kodzie żyją domyślne wartości

| Plik | Co |
|---|---|
| `run.py` linia ~71 | domyślna wartość `--model` w CLI |
| `core/llm/adapters/gemini.py` linia ~16 | domyślny model gdy nie podano |
| `core/llm/adapters/openai.py` linia ~16 | domyślny model gdy nie podano |
| `core/llm/adapters/anthropic.py` linia ~15 | słownik aliasów fast/balanced/powerful |
| `core/llm/factory.py` | routing prefix → adapter |

---

## Routing w factory.py (prefiks → adapter)

```
claude-*          →  AnthropicAdapter
gemini-*          →  GeminiAdapter      (gemini-2.5-*, gemini-3-*, gemini-3.1-*)
gpt-*             →  OpenAIAdapter      (gpt-5.4-*, gpt-5-*, gpt-4.1-*)
o1-* / o3-* / o4-* → OpenAIAdapter
openrouter/*      →  OpenRouterAdapter  (TODO — do zaimplementowania)
```
