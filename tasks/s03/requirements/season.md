# Wymagania sezonu 3 — przegląd całościowy

Pełny raport (kategorie narzędzi, kolejność ataku na epizody, wstępny plan wdrożenia)
powstał w wątku planistycznym 2026-08-08, razem z rozwiązaniem `s02e05` (Sezon 2
domknięty 9/9). Poniżej destylat operacyjny — konkretne pozycje do zrobienia, nie
cała narracja. Pełne uzasadnienia: `source/tool-inventory.md`, `source/community-intel.md`.

## Czym są zadania S03 (jedno zdanie każde)

| Ep | Zadanie | Istota |
|---|---|---|
| s03e01 | `evaluation` | 10 000 plików JSON z sensorów → znajdź anomalie. Inżynieria kosztu. |
| s03e02 | `firmware` | Zdalny okrojony shell (`POST /api/shell`), uruchom binarkę. Pętla agentowa. |
| s03e03 | `reactor` | Robot 7×5, omijanie ruchomych bloków. Czysty algorytm, LLM zbędny. |
| s03e04 | `negotiations` | **Ty budujesz narzędzia, ICH agent je wywołuje.** Publiczny hosting HTTP. |
| s03e05 | `savethem` | Odkrywanie narzędzi przez `/api/toolsearch` + trasa 10×10 pod limitem zasobów. |

## Kolejność ataku (zdecydowane 2026-08-16, zastępuje wcześniejszą rekomendację)

**e01 → e03 → e04 → e05 → e02**

Baza jest numeryczna (autor wybrał tę zasadę wprost), z jednym świadomym wyjątkiem:

- **e01 pierwsze** — koszt <2 centy, wzorzec z `s02e03_failure` przenosi się prawie 1:1,
  progi anomalii podane wprost w treści zadania (nie trzeba ich wyprowadzać z danych).
  Zbiega się z warstwą observability wchodzącą na start sezonu (`strategy/observability.md`)
  — e01 jest pierwszym realnym przypadkiem użycia rejestru promptów i trace'ów generacji.
- **e03 drugie** — najłatwiejsze wg społeczności, ~$0, czysty BFS/DP, zero LLM.
- **e04 trzecie** — łatwe/tanie, ale jedyne zależne od czynnika zewnętrznego (publiczny
  endpoint) — robić gdy tunel/hosting stoi.
- **e05 czwarte** — trudne, ale porażki są koncepcyjne (nieodkryte `/api/books`,
  nieodkryty `dismount`) i już znane z `source/community-intel.md`.
- **e02 jedyny wyjątek od numeracji, na końcu** — najdroższe zadanie sezonu (rozrzut
  kosztu ×140 między podejściami w komentarzach kursu; udokumentowane **nieudane**
  przebiegi po $7.20 i ~$4, podczas gdy ten sam wynik na Gemini Flash kosztował $0.05).
  Wymaga kompletu osłon pętli agentowej (🔴 niżej), których dziś nie ma. Wchodzić
  dopiero PO ich zbudowaniu — robienie e02 wcześnie tylko dlatego, że jest „drugie w
  numeracji", to dokładnie scenariusz, w którym ludzie palili $4-7 bez osłon.

## 🔴 Dług KONIECZNY przed startem (blokuje bezpieczne wejście w S03)

- [ ] **Trzy osłony pętli agentowej** (jeśli nie zrobione już przy okazji
  `feat/killswitch`): limit rozmiaru wyniku narzędzia, rate limiter wychodzący na
  `/api/*`, propagacja błędów narzędzia do modelu zamiast generycznego
  `"ERROR: Tool execution failed"`. Uzasadnienie: każda udokumentowana strata $4-10 w
  komentarzach S03E02 wynikała z braku dokładnie tych osłon.
- [ ] `HubClient.get_public()`/`get_data(tolerate_503=)` (jeśli nie zrobione już przy
  okazji `feat/hub-get-consolidation`) — odblokowuje `/dane/sensors.zip` (e01) i
  `/dane/s03e04_csv/` (e04).
- [ ] Przegląd i aktualizacja `AGENTS.md`/`CLAUDE.md` w całym `aid4u/` oraz w rootcie
  `00_AID4U/` pod kątem nieaktualnych zapisów (np. status sezonów).

## 🟡 Dług przed konkretnym epizodem (nie blokuje reszty)

- [ ] **Przed e04:** migracja ngrok → VPS + kill switch jako webhook (jedna robota,
  ten sam tunel) — uzupełnić `VPS_USER`/`VPS_PATH` w `.env`. Do backlogu, nie
  blokuje — ngrok + istniejący `deploy/` wystarczą na start.

## ✅ Przed e01 — zrobione (2026-08-16, awansowane z oportunistycznego)

- [x] **Warstwa observability** — była zainicjalizowana, ale prawie nieużywana
  (`@langfuse_observe()` na jednej funkcji, w miejscu bez LLM). Zrobione w
  `feat/core-observability-langfuse`: przepięcie `.structured()`/`run_agent_loop()` przez
  `self._chain`, jednostronna synchronizacja promptów kod→Langfuse (wzorzec
  `4th-devs/03_01_observability`), `propagate_attrs()` w `BaseTask.run()`. Kontrakt:
  `strategy/observability.md`.

## 🟢 Oportunistyczne w trakcie sezonu (nie blokuje niczego)
- [ ] Rejestr narzędzi / schemat-z-sygnatury zamiast trzeciej ręcznie klepanej kopii
  wzorca `Tool + closure + dispatcher` (mamy już trzy: s01e02, s01e03, s02e04).
- [ ] Dynamiczne odkrywanie narzędzi w runtime (blokuje elegancki e05 — dziś
  `run_agent_loop(tools=[...])` bierze tylko statyczną listę).
- [ ] Doprecyzować w `data/AGENTS.md` gdzie faktycznie leży `.cache/` (opis mówi
  "patrz `../core/hub/cache.py`", ale to fizycznie folder w rootcie repo, nie
  wewnątrz `core/`) — realna, potwierdzona pułapka.

## ⏸️ Świadomie odłożone (termin, nie "nigdy")

- **Vision + embeddingi w `LLMClient`** — żadne zadanie S03 tego nie wymaga
  (zweryfikowane: `reactor_preview.html`/`savethem_preview.html` to podglądy dla
  człowieka, stan planszy przychodzi z API jako dane). Termin: najpóźniej na
  przełomie S03→S04. Przy realizacji: adaptery (OpenRouter/LM Studio/Ollama/
  llama.cpp) są tanie — Etap 1 z `strategy/llm-selection.md` (wyciągnięcie
  `base_url` z SDK) odblokowuje wszystkie cztery naraz. Multimodalność sama
  (`LLMMessage.content: str` → lista bloków) jest droga i dotyka `types.py` +
  `base.py` + 4 adaptery — to osobny, większy kawałek roboty.
- **`pydantic-ai` jako zamiennik własnego `core/llm/`** — nie "kolejna zależność do
  podłączenia", tylko **rozwidlenie drogi** (pokrywa się funkcjonalnie z
  `LLMClient`/adapterami/`run_agent_loop()`/`Tool`). Rozstrzygnąć świadomie na sesji
  `pre-s03`, przed pisaniem kodu S03 — im później, tym droższa migracja (każde
  kolejne zadanie dokłada kodu do przepisania). To będzie prawdopodobnie największa
  operacja wzmocnienia `core/` do tej pory.
- **7 nieużywanych zależności** (`pydantic-ai*`, `openai-agents`, `mcp`, `mem0ai`,
  `openapi-pydantic`, `prompt-toolkit`) — świadomie dołożone na starcie projektu jako
  owoc researchu, nie przypadkiem. Do jawnego wpisania w `aid4u/AGENTS.md` jako
  "pierwszy wybór przy projektowaniu/upgradzie", potem decyzja: podłączyć albo
  usunąć — razem z decyzją o `pydantic-ai` powyżej, nie osobno.

## Tematy do doczytania przed S03 (w kolejności zwrotu z inwestycji)

1. Model danych observability/eval — hierarchia Session→Trace→Span→Generation,
   offline vs online eval, anatomia evala (zadanie+dataset+score), taksonomia
   asercji. *e01.*
2. Inżynieria kosztu LLM — pięć dźwigni (input/cache/output/równoległość/rozmiar
   modelu), output kosztuje więcej niż input. *e01.*
3. Projektowanie narzędzi dla CUDZEGO agenta — wąski zakres, opis jako artefakt
   krytyczny, koperta `next_action`/`recovery`/`diagnostics`. *e04.*
4. Algorytmy deterministyczne pod ograniczeniami (BFS/DP nad przestrzenią stanów).
   *e03, e05.*
5. Feedback kontekstowy i pętla agenta — wyzwalacze autonomii, błąd narzędzia
   zwracający sugestię zamiast samego błędu. *e03, łata naszą słabość w
   `run_agent_loop`.*
6. Prompt injection i izolacja uprawnień — kontrola wyłącznie w kodzie, nigdy w
   promptcie. *e02 explicite, e04 wystawia nasz endpoint światu.*

Pełne uzasadnienia i przywołania konkretnych lekcji/demo z `4th-devs` — patrz
`source/tool-inventory.md`.
