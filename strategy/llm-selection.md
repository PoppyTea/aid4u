# Strategia wyboru providera LLM

> Stan: 28 lipca 2026 (v2.0.0) — **zmiana kierunku**: podstawową drabiną eskalacji jest teraz
> rodzina Claude, nie Gemini. Poprzednia wersja (8 lipca 2026, v1.1.0) zakładała odwrotnie —
> Gemini zawsze jako pierwszy krok, Anthropic jako ostateczność. Zastępuje `strategy_llm_v1.0.0.md`
> (v1.0.0, Obsidian).
> Model referencyjny (pełna lista + parametry): `strategy/llm-models.md`.
> Sekrety / klucze API: `strategy/secrets-management.md`.

---

## Zasada nadrzędna: zacznij od najtańszego Claude, eskaluj w górę drabiny

Każde zadanie zaczynamy od najtańszego modelu w rodzinie Claude (`claude-haiku-4-5-20251001`)
i eskalujemy w górę drabiny tylko gdy model faktycznie sobie nie radzi — nie z góry. Gemini nie
jest już domyślnym pierwszym krokiem dla każdego zadania — patrz "Gemini: kiedy sięgać" niżej.
Obecnie eskalację przeprowadza użytkownik podczas uruchamiania zadania.

---

## Dwa niezależne wymiary

Strategia ma **dwa niezależne wymiary**, które łatwo pomylić:

1. **Ranga w drabinie Claude** (Haiku 4.5 → Sonnet 5 → Opus 5 → Fable 5) — który *model*
   Anthropic jest użyty. Sterowane parametrem `--model`. To jest **podstawowa** ścieżka
   eskalacji od 28.07.2026.
2. **Tier w obrębie Gemini** (`standard` / `premium`) — który *klucz API* jest użyty, gdy
   zadanie w ogóle korzysta z Gemini (patrz "Gemini: kiedy sięgać" niżej). Sterowane flagą
   `--premium`/`-p` w `run.py`. Osobna, poboczna ścieżka — nie punkt startowy domyślnie.

Te wymiary dotyczą różnych providerów — nie mieszaj ich w jednej decyzji: najpierw zdecyduj,
czy zadanie w ogóle potrzebuje Gemini (modalność), dopiero potem — jeśli tak — który tier.

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

## Gemini: kiedy sięgać, i eskalacja w obrębie tieru (standard → premium)

Gemini nie jest już domyślnym pierwszym krokiem (patrz zmiana z 28.07.2026 wyżej) — sięgaj po
niego świadomie, gdy zadanie ma **realny atut modalności Gemini** (obrazy/wideo, grounding
Search/Maps, bardzo duży kontekst). Gdy tak — zaczynasz od tieru standard (darmowy), potem
premium, dokładnie jak niżej.

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

## Hierarchia providerów (od 28.07.2026)

```
1. claude-haiku-4-5-20251001   ← domyślny start, najtańszy w rodzinie Claude
2. claude-sonnet-5             ← Haiku konsekwentnie zawodzi (3+ próby)
3. claude-opus-5               ← Sonnet nie wystarcza, zadanie naprawdę trudne
4. claude-fable-5              ← ostateczność w rodzinie Claude / [narada nad tym co dalej —
                                   nie ustalono jeszcze co po Fable]

Gemini (standard → premium)    ← OSOBNA ścieżka, nie stopień tej drabiny — używana gdy
                                   modalność Gemini jest realnym atutem zadania (patrz
                                   "Gemini: kiedy sięgać" wyżej)
```

> **Zmiana względem poprzedniej wersji (8 lipca 2026):** hierarchia była odwrócona — Gemini
> zawsze jako pierwszy krok, Anthropic jako ostateczność. Od 28.07.2026 jest odwrotnie: Claude
> to podstawowa drabina, Gemini to świadomy wybór pod konkretną modalność.
>
> **OpenAI — poza podstawową drabiną od 28.07.2026.** Kod (`OpenAIAdapter`) i klucz zostają,
> ale to już nie jest domyślny stopień pośredni — do rewizji, jeśli pojawi się konkretny powód
> (np. model niedostępny gdzie indziej, koszt). Podobnie OpenRouter (patrz TODO niżej) —
> nieużywany, `OpenRouterAdapter` to wciąż `TODO` w `factory.py`.

---

## Kiedy eskalować model

| Sygnał | Akcja |
|---|---|
| Model zwraca złe wyniki przy prostym zadaniu | Popraw prompt, spróbuj jeszcze raz — nie eskaluj od razu |
| Model konsekwentnie myli się w logice (3+ próby) | Przejdź poziom wyżej w drabinie Claude (Haiku → Sonnet → Opus → Fable) |
| Zadanie ma realną modalność Gemini (obrazy, grounding, ogromny kontekst) | Zacznij od `gemini-2.5-flash` (standard, darmowy), eskaluj do `--premium` zanim rozważysz cokolwiek innego |
| Zadanie wymaga function calling z wieloma narzędziami | Zacznij od `claude-sonnet-5` (dobry function calling), eskaluj do `claude-opus-5` jeśli się gubi |
| Zadanie z ostrym limitem czasu (np. windpower — 40s) | `claude-haiku-4-5-20251001` (szybki, tani) — albo `gemini-2.5-flash` jeśli modalność Gemini też gra rolę |
| Zadanie agentowe z wieloma krokami | `claude-sonnet-5`, nie haiku — eskaluj do `claude-opus-5` przy problemach |
| Vision (obrazki, PNG planszy) | `gemini-2.5-flash` (darmowy, dobry multimodal) — to jest właśnie sygnał "modalność Gemini ważna" |
| Złożone rozumowanie wieloetapowe | `claude-sonnet-5` → `claude-opus-5` → `claude-fable-5` |

---

## Jak to wygląda w praktyce

```bash
# Pierwsze podejście — zawsze najtańszy Claude
uv run run.py solve s01e02 --model claude-haiku-4-5-20251001

# Haiku konsekwentnie zawodzi (3+ próby) — poziom wyżej w drabinie Claude
uv run run.py solve s01e02 --model claude-sonnet-5

# Sonnet nie wystarcza, zadanie naprawdę trudne
uv run run.py solve s01e02 --model claude-opus-5

# Opus też zawodzi — ostateczność w rodzinie Claude
uv run run.py solve s01e02 --model claude-fable-5

# Zadanie ma realną modalność Gemini (obrazy, grounding) — osobna ścieżka, nie eskalacja Claude
uv run run.py solve s01e02 --model gemini-2.5-flash
uv run run.py solve s01e02 --model gemini-2.5-flash --premium   # standard nie wystarcza
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
