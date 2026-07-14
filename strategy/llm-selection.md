# Strategia wyboru providera LLM

> Stan: 8 lipca 2026. Zastępuje `strategy_llm_v1.0.0.md` (v1.0.0, Obsidian).
> Model referencyjny (pełna lista + parametry): `strategy/llm-models.md`.
> Sekrety / klucze API: `strategy/secrets-management.md`.

---

## Zasada nadrzędna: najpierw darmowe, potem tanie, drogie w ostateczności

Każde zadanie zaczynamy od najtańszej opcji i eskalujemy tylko gdy model
faktycznie sobie nie radzi — nie z góry.
Obecnie eskalację przeprowadza użytkownik podczas uruchamiania zadania.
---

## Dwa wymiary eskalacji

Od tej wersji strategia ma **dwa niezależne wymiary**, które łatwo pomylić:

1. **Tier w obrębie Gemini** (`standard` / `premium`) — który *klucz API* jest
   użyty. Sterowane flagą `--premium`/`-p` w `run.py`.
2. **Provider** (Gemini → OpenAI → Anthropic) — który *dostawca/model* jest
   użyty. Sterowane parametrem `--model`.

Te wymiary są ortogonalne: możesz użyć `gemini-2.5-pro` w tierze standard
(darmowym) albo `gemini-3.5-flash` w tierze premium — wybór modelu i wybór
tieru to dwie osobne decyzje.

### Dlaczego dwa klucze Gemini, a nie jeden z przełącznikiem

Darmowy tier Gemini API jest związany z projektem Google Cloud, w którym
**billing jest wyłączony**. Płatny tier wymaga billingu **włączonego**. To
własność projektu, nie parametr requestu — jeden klucz API fizycznie nie może
obsłużyć obu tierów. Stąd dwa osobne klucze w sekretach:

```
GEMINI_API_KEY           # tier standard — projekt BEZ billingu
GEMINI_API_KEY_PREMIUM   # tier premium  — osobny projekt Z billingiem
```

Wybór klucza żyje **wyłącznie** w `core/llm/factory.py` (parametr `tier`) —
`GeminiAdapter` nie wie nic o tierach i nie powinien; to celowa decyzja, żeby
nie robić przełączników wewnątrz adapterów.

---

## Eskalacja w obrębie Gemini (tier standard → premium)

| Grupa | Flash-Lite | Flash | Pro |
|---|---|---|---|
| **Standard — Free Tier** (domyślny) | najnowszy stabilny (2026/07/14: `gemini-3.1-flash-lite`) | najnowszy stabilny (2026/07/14: `gemini-3.5-flash`) | `gemini-2.5-pro` |
| **Premium — Płatny** (`--premium`) | najnowszy stabilny | najnowszy stabilny | najnowszy stabilny (2026/07/14: `gemini-3.1-pro-preview`, wciąż preview) |

> "Najnowszy stabilny" to instrukcja utrzymania, nie literalny alias API —
> podmieniaj konkretny identyfikator w `strategy/llm-models.md`, gdy Google
> wypuści nowszy stabilny model. Nie potwierdziliśmy istnienia działającego
> aliasu typu `gemini-flash-latest` dla tego API — do zweryfikowania, jeśli
> kiedyś zechcemy tego użyć zamiast ręcznej aktualizacji.

Praktyczny wniosek z tej tabeli: w grupie Standard `gemini-2.5-pro` zostaje
przy 2.5, bo rodzina 3.x nie ma w darmowym tierze groundingu (Search/Maps) i
w praktyce ma ciaśniejsze limity — nie ma sensu tam eskalować w ramach
darmowego tieru. W grupie Premium płacimy i tak, więc bierzemy najlepszy
dostępny Pro.

**Kiedy sięgać po `--premium`:** gdy `gemini-2.5-pro` (darmowy) faktycznie nie
daje rady, a zadanie nie uzasadnia jeszcze przejścia do OpenAI/Anthropic —
płatny Flash 3.x bywa tańszy i szybszy niż przeskok do innego providera.

---

## Hierarchia providerów

```
1. Gemini — standard (darmowy tier)   ← ZAWSZE zaczynamy tutaj
2. Gemini — premium (płatny tier)     ← gdy standard nie daje rady, --premium
3. OpenAI                             ← gdy cała rodzina Gemini zawodzi
4. Anthropic                          ← złożone planowanie, ostateczność
```

> **Zmiana względem v1.0.0:** poprzednia wersja miała 5 stopni z dwoma
> poziomami OpenRouter (free/paid) między Gemini a OpenAI. OpenRouter nie ma
> dziś żadnej implementacji w kodzie (`OpenRouterAdapter` to `TODO` w
> `factory.py`) — patrz sekcja "TODO" niżej po ustalenia co do jego przyszłej
> roli.

---

## Kiedy eskalować model

| Sygnał | Akcja |
|---|---|
| Model zwraca złe wyniki przy prostym zadaniu | Popraw prompt, spróbuj jeszcze raz — nie eskaluj od razu |
| Model konsekwentnie myli się w logice (3+ próby) | Przejdź poziom wyżej w hierarchii |
| `gemini-2.5-pro` (standard) nie radzi sobie, ale zadanie nie uzasadnia zmiany providera | `--premium` (Flash 3.x lub Pro 3.x płatny) zamiast skoku do OpenAI |
| Zadanie wymaga function calling z wieloma narzędziami | Zacznij od `gemini-2.5-flash`, fallback `claude-sonnet-4-6` |
| Zadanie z ostrym limitem czasu (np. windpower — 40s) | Od razu użyj szybkiego modelu (Flash / Flash-Lite) |
| Zadanie agentowe z wieloma krokami | `gemini-2.5-flash` lub `claude-sonnet-4-6`, nie haiku |
| Vision (obrazki, PNG planszy) | `gemini-2.5-flash` (darmowy, dobry multimodal) |
| Złożone rozumowanie wieloetapowe | `gemini-2.5-pro` → `--premium` → `claude-sonnet-4-6` |

---

## Jak to wygląda w praktyce

```bash
# Pierwsze podejście — zawsze Gemini standard (darmowy)
uv run run.py solve s01e02 --model gemini-3.5-flash

# Prostsze zadanie? Ultra lekki model, wciąż standard
uv run run.py solve s01e02 --model gemini-3.1-flash-lite

# Flash nie daje rady, ale nie chcemy jeszcze zmieniać providera?
uv run run.py solve s01e02 --model gemini-2.5-pro

# Pro (standard) też zawodzi — eskaluj do premium zamiast providera
uv run run.py solve s01e02 --model gemini-3.5-flash --premium

# Cała rodzina Gemini zawodzi — dopiero teraz zmiana providera
uv run run.py solve s01e02 --model gpt-5.4-mini

# Złożone zadanie agentowe / wieloetapowe planowanie — ostateczność
uv run run.py solve s04e03 --model claude-sonnet-4-6
```

---

## TODO dla implementacji

Ustalenia (2026-07-08): OpenRouter wraca jako dwuetapowy plan, nie jako
osobny stopień w dzisiejszej hierarchii:

1. **Etap 1 — prosty refaktor `core/llm/adapters/openai.py`:** wydzielić
   `base_url` jako parametr konstruktora (dziś zahardkodowany przez SDK
   OpenAI na `api.openai.com`). To jedyna zmiana potrzebna, żeby ten sam
   adapter obsługiwał OpenRouter (`base_url="https://openrouter.ai/api/v1"`)
   — OpenRouter jest API-kompatybilny z OpenAI.
2. **Etap 2 — rozszerzenie o obsługę wielu modeli przez jeden klucz:** gdy to
   zadziała, OpenRouter może w praktyce **zastąpić bezpośrednie adaptery**
   OpenAI i Anthropic (jeden klucz, jeden adapter, wiele modeli różnych
   dostawców). Docelowo `gemini.py` zostałby jedynym adapterem
   "specjalnym" — bo to jedyny sposób dostępu do prawdziwie darmowego tieru;
   wszystko płatne (OpenAI, Anthropic, Gemini premium?) mogłoby iść przez
   OpenRouter.

Nie blokuje to obecnej pracy — `factory.py` ma już gałąź `openrouter/*`
gotową (rzuca `NotImplementedError` przez brakujący `OpenRouterAdapter`),
więc rozszerzenie jest lokalne i nie wymaga zmian w routingu.

---

## Zmienne środowiskowe (kolejność odzwierciedla priorytety)

```bash
# ~~.env — fallback (nieczynny - pozbywamy się go stopniowo)~~ ; klucze docelowo w systemowym keyring (patrz secrets-management.md)

# ── Gemini — standard (darmowy) ──────────────────────────────────────────────
GEMINI_API_KEY="..."
# Projekt Google Cloud z WYŁĄCZONYM billingiem.

# ── Gemini — premium (płatny) ────────────────────────────────────────────────
GEMINI_API_KEY_PREMIUM="..."
# Osobny projekt Google Cloud z WŁĄCZONYM billingiem. Wymagany tylko z --premium.

# ── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY="..."

# ── Anthropic ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY="..."

# ── OpenRouter (TODO — patrz sekcja wyżej, kod jeszcze nie istnieje) ─────────
# OPENROUTER_FREE_API_KEY="..."
# OPENROUTER_API_KEY="..."
```
