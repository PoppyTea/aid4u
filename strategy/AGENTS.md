# Strategy Module (DOX)

## Purpose
Repozytorium dokumentacji strategicznej, protokołów uczenia się, standardów nazewnictwa oraz zasad bezpieczeństwa.

## Ownership
- `strategy/tasks/`: Workflow i reguły dekompozycji zadań.
- `strategy/skills/`: Logika aktywacji i rejestr skilli.
- `strategy/naming-conventions.md`: Standardy nazewnictwa.
- `strategy/secrets-management.md`: Strategia bezpieczeństwa i zarządzania sekretami.

## Local Contracts
- Wszystkie dokumenty strategiczne muszą być zwięzłe i operacyjne.
- **Zero stanu w `strategy/`.** Pliki tego folderu trzymają wiedzę trwałą — reguły,
  procedury, konwencje, uzasadnienia. Nie trzymają stanu: żadnych checkboxów odbijających
  issue, list „do zrobienia", statusów typu ✅/❌ opisujących bieżący stan repo ani dat
  ostatniego wykonania. Stan długu ma jeden dom — Linear (`issue-tracking.md`);
  w tekście zostaje najwyżej kotwica `(→ AID-XXX)`. Dopuszczalne wyjątki: ✅/❌ jako
  przykłady dobrze/źle (`naming-conventions.md`), trwała właściwość rzeczy zewnętrznej
  (model wycofany przez dostawcę w `llm-models.md`), placeholdery w szablonach
  (`templates/`, `skills/skill-contracts.md`) i generyczne kryteria wyjścia z procedury,
  których się nie odhacza. Powód: dokument bez stanu nie może się zdezaktualizować, więc
  nie wymaga rytuału synchronizacji, którego i tak nikt nie wykona.
- Zmiana w strategii zarządzania sekretami lub nazewnictwie wymaga aktualizacji odpowiedniego pliku w tym folderze.

## Work Guidance
- Traktuj dokumentację jak kod.
- Obowiązuje zakaz podglądu plików `.env` (oddeleguj do użytkownika).
- Każde naruszenie bezpieczeństwa (wyciek klucza) wymaga przerwania pracy i raportu.

## Verification
- Spójność z `core/secrets.py` oraz `config.py` przy każdej zmianie dotyczącej sekretów.
- Zgodność z globalnymi wytycznymi z `/AGENTS.md`.

## Closeout
1. Sprawdź zmiany w `strategy/` względem kontraktów w roocie.
2. Upewnij się, że `Child DOX Index` zawiera wszystkie podfoldery i pliki strategiczne.
3. Usuń nieaktualne notatki historyczne.

## Child DOX Index
- `./skills` - Rejestr skilli.
- `./tasks` - Definicje workflow zadań.
- `./templates` - Szablony projektowe.
- `./learning-protocol.md` - Protokół nauki.
- `./naming-conventions.md` - Standardy nazewnictwa.
- `./secrets-management.md` - Strategia bezpieczeństwa i sekretów.
- `./season-transition.md` - Procedura przejścia między sezonami kursu (sezonoagnostyczna;
  konkretne instancje per-sezon w `tasks/sXX/requirements/`).
- `./agent-loop-safety.md` - Uzasadnienia osłon pętli agentowej (błędy narzędzi, budżet
  kosztu, throttle 429, bramka poleceń): dlaczego, kompromisy, znalezione obejścia.
  Kontrakty żyją w `core/AGENTS.md`, tutaj są powody.
- `./secret-flags.md` - Metoda polowania na flagi sekretne: zasada naczelna, trzy odruchy
  do złamania, gdzie szukać. Polityka (priorytet, zapis) jest kontraktem w rootowym
  `AGENTS.md`, zasada 7.
- `./observability.md` - Kontrakt warstwy obserwacji (Logfire + Langfuse): podział ról,
  hierarchia zdarzeń, rejestr promptów, decyzja o async.
- `./open-decisions.md` - Pytania rozstrzygalne międzysezonowo, bez miejsca w roadmapie
  konkretnego sezonu (np. self-hosted kontra cloud Langfuse).
- `./demo-processing-workflow.md` - Workflow przetwarzania demo/przykładów kursu.
- `./efficiency-mode` - Materiały trybu efficiency mode.
- `./llm-models.md` - Referencja/ściągawka modeli LLM.
- `./llm-selection.md` - Strategia wyboru/eskalacji/tier modeli LLM.
- `./issue-tracking.md` - Cykl życia issue w Linear (jedyne źródło prawdy długu
  technicznego): priorytety, labele, dedup, lejek diagnoz.
- `./quality-control.md` - Governance rutyn/audytów: katalog, anatomia promptu,
  findingi → Linear, higiena harmonogramu.
- `./rules/` - Reguły recenzji/audytu (`rNN-*.md`), digest ERROR czytany przez
  CodeRabbit.
