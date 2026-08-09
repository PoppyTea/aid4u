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
