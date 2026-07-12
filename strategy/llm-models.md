# Aktualne modele LLM — szybka ściągawka

> Stan: 8 lipca 2026 (na podstawie ai.google.dev/gemini-api/docs/models i /pricing). Aktualizuj gdy pojawią się nowe modele.
> Zastępuje `models-reference.md` (root) i `strategy_llm_v1.0.0.md` (Obsidian) — patrz `naming-conventions.md`.
> Pełna strategia wyboru / eskalacji / tierów: `strategy/llm-selection.md`.

---

## Domyślny model projektu

```
gemini-2.5-flash
```

To jest wartość domyślna `--model` w `run.py` i startowy punkt dla każdego zadania.
Domyślny tier: **standard** (darmowy) — patrz `strategy/llm-selection.md` po opis flagi `--premium`.

---

## Gemini — Google AI Studio

**Ważne — free vs paid tier:** "darmowy" tier w Gemini API działa na kluczu z projektu Google Cloud
z **wyłączonym** billingiem — dane wtedy trafiają do Google na trening (`used to improve our
products: Yes`), i obowiązują dzienne limity requestów (RPD). Włączenie billingu (tier płatny,
osobny projekt = osobny klucz `GEMINI_API_KEY_PREMIUM`) wyłącza trening na Twoich danych i zdejmuje
limity, ale kosztuje per token. Wszystkie modele niżej *technicznie* mają darmowy tier — różnica
jest w tym, jak hojne są limity i czy grounding (Search/Maps) w ogóle działa bez płacenia.

### Stabilne (zalecane do użytku)
| Identyfikator API | Tier | Użyj gdy |
|---|---|---|
| `gemini-2.5-flash` | darmowy, hojne RPD | **domyślny** — większość zadań, dobry stosunek ceny do jakości |
| `gemini-2.5-flash-lite` | darmowy, hojne RPD | prostszy tagging, filtrowanie CSV, zadania "at scale" |
| `gemini-2.5-pro` | darmowy tier istnieje, ale wąskie limity | Flash nie daje rady — głębsze rozumowanie, coding |
| `gemini-3.5-flash` | darmowy tier bez groundingu; płatny: $1.50/$9.00 za 1M tok. | frontier-class, agentowe/coding na produkcję — **tylko z `--premium`** |
| `gemini-3.1-flash-lite` | darmowy tier bez groundingu; płatny: $0.25/$1.50 za 1M tok. | najtańszy z rodziny 3.x, wysoka skala — **tylko z `--premium`** |

Nie ma powodu, by unikać `gemini-2.5-pro` do zadań, gdzie Flash nie wystarcza — ma sensowny darmowy
tier, więc zostaje w grupie **Standard**. Rodzinę `gemini-3.x` traktuj jako świadomy upgrade "jesteśmy
gotowi płacić za tokeny" (grupa **Premium**, flaga `--premium`) — darmowy tier 3.x nie ma groundingu
(Search/Maps) i w praktyce jest węższy niż w 2.5.

### Preview (niestabilne, mogą zniknąć bez długiego okresu przejściowego)
| Identyfikator API | Użyj gdy |
|---|---|
| `gemini-3.1-pro-preview` | najbardziej zaawansowane rozumowanie/agentowe planowanie w rodzinie 3.x, wciąż preview — grupa Premium |
| `gemini-3-flash-preview` | starszy preview 3.x — Google rekomenduje migrację do stabilnego `gemini-3.5-flash` |

### ❌ Wycofane / shut down — NIE UŻYWAJ
- `gemini-2.0-flash` — shut down
- `gemini-2.0-flash-lite` — shut down
- `gemini-1.5-flash` — shut down (dawno)
- `gemini-3-pro-preview` — shut down, następca to `gemini-3.1-pro-preview`
- `gemini-3.1-flash-lite-preview` — shut down, następca to stabilny `gemini-3.1-flash-lite`

---

## Sterowanie parametrami — różnice ≥3.0 vs 2.5

Rodzina Gemini 3.x zmienia sposób sterowania "myśleniem" i samplingiem względem 2.5. To ma bezpośrednie znaczenie dla `core/llm/adapters/gemini.py`, jeśli/gdy dodamy tam obsługę modeli 3.x:

- **2.5.x** (`gemini-2.5-flash`, `-flash-lite`, `-pro`): steruj myśleniem przez `thinking_config=types.ThinkingConfig(thinking_budget=N)`. `0` = wyłączone, `-1` = dynamiczne (domyślne dla Flash/Pro), zakres `0–24576` dla Flash. **Nie wspierają** `thinking_level`.
- **3.x** (`gemini-3.5-flash`, `gemini-3.1-flash-lite`, `gemini-3.1-pro-preview`, `gemini-3-flash-preview`): steruj myśleniem przez `thinking_config=types.ThinkingConfig(thinking_level="minimal"|"low"|"medium"|"high")`. Domyślny poziom dla `gemini-3.5-flash` to **`medium`** (zmiana z `high` w poprzednim preview `gemini-3-flash-preview`).
- **Nie wolno mieszać** `thinking_level` i `thinking_budget` w jednym requeście do modelu 3.x — Google zwraca `400`. `thinking_budget` nadal działa wstecznie na 3.x, ale jest odradzane.
- **`temperature`, `top_p`, `top_k`**: dla modeli 3.x Google **odradza** ich ustawianie — model jest zoptymalizowany pod domyślne wartości i ręczne majstrowanie pogarsza jakość. Dla determinizmu użyj precyzyjnej instrukcji systemowej zamiast dokręcania samplingu. (2.5.x nadal dobrze reaguje na `temperature=0.0`, jak w obecnym adapterze.)
- **`candidate_count`**: nieobsługiwane w 3.x (obsługiwane w 2.5.x).
- **Segmentacja obrazów**: niedostępna w 3.x — jeśli kiedyś będzie potrzebna, zostań przy `gemini-2.5-flash` z wyłączonym myśleniem, albo `Gemini Robotics-ER 1.6`.
- **Structured outputs**: mechanizm (`response_mime_type="application/json"` + `response_schema`) działa tak samo w obu rodzinach — nasz obecny kod w `complete_structured()` nie wymaga zmian przy ewentualnym dodaniu modeli 3.x, poza dodaniem gałęzi `if/else` na wybór `thinking_budget` vs `thinking_level` w zależności od prefiksu modelu.

Źródło: [ai.google.dev/gemini-api/docs/whats-new-gemini-3.5](https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.5) i [.../docs/generate-content/thinking](https://ai.google.dev/gemini-api/docs/generate-content/thinking).

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
| `run.py` (`solve`) | domyślna wartość `--model` w CLI, flaga `--premium`/`-p` (tier) |
| `core/llm/adapters/gemini.py` | domyślny model gdy nie podano |
| `core/llm/adapters/openai.py` | domyślny model gdy nie podano |
| `core/llm/adapters/anthropic.py` | słownik aliasów fast/balanced/powerful |
| `core/config.py` | `gemini_key` / `gemini_key_premium` / `gemini_key_for_tier()` |
| `core/llm/factory.py` | routing prefix → adapter, wybór klucza wg `tier` |

---

## Routing w factory.py (prefiks → adapter)

```
claude-*          →  AnthropicAdapter
gemini-*          →  GeminiAdapter      (gemini-2.5-*, gemini-3-*, gemini-3.1-*, gemini-3.5-*)
                      + parametr tier: "standard" (domyślny, GEMINI_API_KEY)
                                       | "premium" (GEMINI_API_KEY_PREMIUM)
gpt-*             →  OpenAIAdapter      (gpt-5.4-*, gpt-5-*, gpt-4.1-*)
o1-* / o3-* / o4-* → OpenAIAdapter
openrouter/*      →  OpenRouterAdapter  (TODO — patrz strategy/llm-selection.md)
```
