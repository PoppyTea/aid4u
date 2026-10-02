# Strategia wyboru providera LLM

> Scala dawne `llm-selection.md` i `llm-models.md` (2026-08-23). Ten plik trzyma **zasady
> wyboru i eskalacji**. Konkretne identyfikatory modeli **nie żyją tutaj** — źródłem prawdy
> są rostery `ANTHROPIC_MODELS` / `OPENAI_MODELS` / `GEMINI_MODELS` w `core/llm/adapters/`,
> egzekwowane przez `create_provider()`. Powód rozdziału: `strategy/` nie trzyma stanu
> (patrz `strategy/AGENTS.md`), a lista modeli to stan świata zewnętrznego, który zmienia
> się szybciej, niż ktokolwiek aktualizuje prozę.
> Sekrety / klucze API: `strategy/secrets-management.md`.

---

## Zasada nadrzędna: zacznij od najtańszego Claude, eskaluj w górę drabiny

Każde zadanie zaczynamy od `ANTHROPIC_MODELS["fast"]` i eskalujemy w górę drabiny tylko gdy
model faktycznie sobie nie radzi — nie z góry. Gemini nie jest domyślnym pierwszym krokiem
(zmiana kierunku z 28.07.2026; wcześniej było odwrotnie) — patrz „Gemini: kiedy sięgać".
Eskalację przeprowadza użytkownik przy uruchamianiu zadania.

## Dwa niezależne wymiary

Łatwo je pomylić, a dotyczą różnych providerów:

1. **Ranga w drabinie zdolności** (`fast` → `balanced` → `powerful` → `flagship`) — który
   *model* jest użyty. Sterowane parametrem `--model`. Podstawowa ścieżka eskalacji.
2. **Tier rozliczeniowy Gemini** (`free` / `premium`) — który *klucz API* jest użyty.
   Sterowane flagą `--premium`/`-p`. Osobna, poboczna ścieżka.

Najpierw zdecyduj, czy zadanie w ogóle potrzebuje Gemini (modalność), dopiero potem — jeśli
tak — który tier.

> Tier darmowy nazywa się `free`, **nie `standard`** (zmiana 2026-08-23). „Standard"
> sugerowało tryb domyślny — a Gemini nim był tylko historycznie i przestał być; dziś
> domyślny jest najtańszy Claude. Nazwa myliła dokładnie w tym miejscu, w którym
> potrzebna jest jednoznaczność, bo od niej zależy, którym kluczem poleci zapytanie.

### Dlaczego dwa klucze Gemini, a nie jeden z przełącznikiem

Darmowy tier Gemini API jest związany z projektem Google Cloud, w którym **billing jest
wyłączony**; płatny wymaga billingu **włączonego**. To własność projektu, nie parametr
requestu — jeden klucz fizycznie nie obsłuży obu tierów. Stąd `GEMINI_API_KEY` (projekt bez
billingu) i `GEMINI_API_KEY_PREMIUM` (osobny projekt z billingiem).

Konsekwencja praktyczna, zmierzona 2026-08-23: **projekty darmowe bywają grandfatherowane**.
`gemini-2.5-flash` odpowiada na starym kluczu darmowym, a na premium zwraca 404 („no longer
available to new users"). Dlatego dostępność modelu sprawdza się realnym wywołaniem **per
klucz**, nie `models.list()` — katalog globalny wymienia też modele, których danym kluczem
nie zawołasz.

Wybór klucza żyje **wyłącznie** w `core/llm/factory.py` (parametr `tier`) — `GeminiAdapter`
nie wie nic o tierach i nie powinien.

---

## Gemini: kiedy sięgać

Sięgaj świadomie, gdy zadanie ma **realny atut modalności Gemini** (obrazy/wideo, grounding
Search/Maps, bardzo duży kontekst). Wtedy zaczynasz od tieru `free`, potem `premium`.

Podział rosteru idzie osią **lite → flash → pro**, a tier rozliczeniowy krzyżuje się z nią
(stąd `GEMINI_MODELS` jest zagnieżdżony, w przeciwieństwie do pozostałych providerów).
W grupie `free` zostajemy na tym, co darmowy projekt realnie obsługuje; w premium płacimy
i tak, więc bierzemy najwyższą dostępną wersję.

**Kiedy sięgać po `--premium`:** gdy darmowy tier faktycznie nie daje rady, a zadanie nie
uzasadnia jeszcze przejścia do innego providera — płatny Flash bywa tańszy i szybszy niż
przeskok gdzie indziej.

## Hierarchia providerów

```
1. fast       ← domyślny start, najtańszy w rodzinie Claude
2. balanced   ← fast konsekwentnie zawodzi (3+ próby)
3. powerful   ← balanced nie wystarcza, zadanie naprawdę trudne
4. flagship   ← ostateczność w rodzinie Claude

Gemini (free → premium)     ← OSOBNA ścieżka, nie stopień tej drabiny
```

**OpenAI — poza podstawową drabiną od 28.07.2026.** Adapter i klucz zostają, ale to nie jest
domyślny stopień pośredni. **OpenRouter** — adapter **istnieje**
(`core/llm/adapters/openrouter.py`, dziedziczy po `OpenAIAdapter`), `factory.py` go tworzy
na prefiksie `openrouter/`, a `core/config.py` wystawia klucz. Brakuje wyłącznie **rostera
modeli**, więc walidacja identyfikatora tej gałęzi nie obejmuje `(→ AID-61)`.

---

## Rekomendacje z komentarzy kursu mają pierwszeństwo przy pierwszym podejściu

Jeśli komentarze do zadania wskazują konkretny model jako opłacalny (duże oszczędności,
wyraźnie lepsza skuteczność) albo **odradzają** jakiś model — zastosuj się do tego
**przy pierwszych podejściach**, zamiast startować z domyślnego szczebla drabiny.
Te wskazówki są empirią z cudzych przebiegów, opłaconą cudzymi tokenami; drabina jest
heurystyką na wypadek, gdy takiej empirii nie ma. Dopiero gdy rekomendacja zawiedzie,
wracasz do normalnej eskalacji.

Gdzie szukać: `tasks/sXX/requirements/source/community-intel.md` oraz
`tasks/sXXeYY_nazwa/doc/community_notes.md` w folderze zadania.

## Kiedy eskalować model

| Sygnał | Akcja |
|---|---|
| Złe wyniki przy prostym zadaniu | Popraw prompt, spróbuj ponownie — nie eskaluj od razu |
| Konsekwentne błędy w logice (3+ próby) | Poziom wyżej w drabinie (`fast` → `balanced` → …) |
| Realna modalność Gemini (obrazy, grounding, ogromny kontekst) | Gemini `free`, potem `--premium` |
| Function calling z wieloma narzędziami | Zacznij od `balanced`, eskaluj do `powerful` |
| Ostry limit czasu (np. `windpower` — 40 s) | `fast` — albo Gemini, jeśli modalność też gra rolę |
| Zadanie agentowe wielokrokowe | `balanced`, nie `fast` |
| Vision (obrazki, PNG planszy) | Gemini — to jest właśnie sygnał „modalność ważna" |
| Złożone rozumowanie wieloetapowe | `balanced` → `powerful` → `flagship` |

## Jak to wygląda w praktyce

```bash
# Pierwsze podejście — domyślny model, bez podawania --model
uv run run.py solve s01e02

# Eskalacja: identyfikator bierz z rostera adaptera, nie z pamięci.
# Zła nazwa jest odrzucana przy konstrukcji, z listą dopuszczalnych w treści błędu.
uv run run.py solve s01e02 --model <ANTHROPIC_MODELS["balanced"]>

# Modalność Gemini — osobna ścieżka, nie eskalacja drabiny
uv run run.py solve s01e02 --model <GEMINI_MODELS["free"]["balanced"]>
uv run run.py solve s01e02 --model <GEMINI_MODELS["premium"]["balanced"]> --premium
```

---

## Modele, które agenci halucynują najczęściej

Ta lista **nie jest katalogiem wycofanych modeli** — taki zbiór jest nieskończony
i niesprawdzalny. To spis konkretnych recydywistów: identyfikatorów, które modele językowe
wpisują odruchowo, bo dominowały w danych treningowych. To nie luka w wiedzy, tylko
ciążenie — i dlatego lista jest krótka i celowana, a nie wyczerpująca.

- `gpt-4o`, `gpt-4o-mini`
- `gemini-1.5-*`, `gemini-2.0-*`
- `claude-3-*` (w tym `claude-3-5-sonnet-*`)

**Właściwą barierą jest kod, nie ta lista.** `create_provider()` odrzuca każde ID spoza
rostera i podaje w błędzie poprawne opcje, więc zła nazwa pada natychmiast, a nie po
kilkunastu sekundach jako błąd opakowany przez SDK. Lista zostaje jako sygnał dla człowieka
czytającego ten dokument — przy okazji zapisując, po co w ogóle powstała, bo bez tego
uzasadnienia audyt 2026-08-21 zarekomendował jej usunięcie jako „nieaktualnego rejestru".

Skuteczność samej listy nie została nigdy zmierzona — eksperyment z jej usunięciem czeka
w `(→ AID-80)`.

---

## Sterowanie parametrami — różnice między rodzinami Gemini

Kontrakt „myślenia" różni się między rodzinami i **te dwa warianty się wykluczają** —
zmieszanie ich w jednym zapytaniu daje 400. Rodzina 2.5 przyjmuje `thinking_budget`
(`0` = wyłączone), rodzina 3.x oczekuje `thinking_level`. Dodatkowo modele `pro` w rodzinie
3.x **nie pozwalają wyłączyć myślenia** — zerowy budżet zwraca 400 („This model only works
in thinking mode").

Egzekwuje to `GeminiAdapter._thinking_config()`, nie ten dokument — kontrakt w
`core/AGENTS.md`.

Pozostałe różnice, nieujęte w kodzie:

- **`temperature`, `top_p`, `top_k`:** dla rodziny 3.x Google **odradza** ich ustawianie —
  model jest zoptymalizowany pod domyślne, a ręczne dokręcanie pogarsza jakość. Dla
  determinizmu użyj precyzyjnej instrukcji systemowej. Rodzina 2.5 nadal dobrze reaguje na
  `temperature=0.0`.
- **`candidate_count`:** nieobsługiwane w 3.x, obsługiwane w 2.5.x.
- **Segmentacja obrazów:** niedostępna w 3.x.
- **Structured outputs:** mechanizm (`response_mime_type` + `response_schema`) identyczny
  w obu rodzinach.

---

## Zmienne środowiskowe

Klucze docelowo w systemowym keyring — patrz `strategy/secrets-management.md`.

```bash
GEMINI_API_KEY           # tier free — projekt Google Cloud BEZ billingu
GEMINI_API_KEY_PREMIUM   # tier premium  — osobny projekt Z billingiem, wymagany przy --premium
OPENAI_API_KEY
ANTHROPIC_API_KEY
OPENROUTER_API_KEY       # adapter działa; bez rostera modeli (→ AID-61)
```

## Gdzie w kodzie żyją domyślne wartości

| Plik | Co |
|---|---|
| `core/llm/adapters/*.py` | **rostery modeli — źródło prawdy**, plus model domyślny adaptera |
| `core/llm/factory.py` | routing prefiks → adapter, walidacja modelu, wybór klucza wg `tier` |
| `core/config.py` | `gemini_key` / `gemini_key_premium` / `gemini_key_for_tier()` |
| `run.py` (`solve`) | domyślna wartość `--model`, flagi `--premium` i `--allow-unknown-model` |
