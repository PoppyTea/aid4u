# Tasks Module

## Purpose
Execution environment for AI_Devs 4 course tasks. **EFFICIENCY MODE aktywny** (od 2026-07-29)
— priorytet: szybkość i skuteczność zdobywania flag do 20/25, nie proces. Learning-mode
wersja tego pliku: `.help/learning-vs-efficiency/learning-mode/aid4u/tasks/AGENTS.md`
(przywróć przez `aid4u/scripts/learning_mode_on_off.py on`).

## Ownership
- Each folder (`sXXeYY`) acts as a domain for a specific task.

## Local Contracts
- Every task solution MUST contain `solution.py`.
- `test_solution.py` opcjonalny — pisz go PO działającym rozwiązaniu, tylko jeśli faktycznie
  pomoże zweryfikować coś nietrywialnego. Weryfikacja przez realne uruchomienie
  (`--dry-run` / hub) liczy się bardziej niż testy jednostkowe.
- Task execution via `uv run run.py solve sXXeYY`.
- **Wyjątek — zadania oparte na żywym serwerze (np. `s01e03_proxy`):** jeśli zadanie
  rozwiązuje się przez publicznie wystawiony endpoint (bot Centrali prowadzi rozmowę
  na żywo), a nie przez pojedyncze `fetch→solve→submit`, `solve()` MUSI jawnie
  odmówić (`raise RuntimeError` z instrukcją uruchomienia) zamiast po cichu wysyłać
  pustą/fałszywą odpowiedź na hub. Taki folder dostaje własny `AGENTS.md` (patrz
  Child DOX Index) opisujący kontrakt endpointu, zmienne środowiskowe i workflow.

## Work Guidance
- Zanim zaprojektujesz rozwiązanie od zera: sprawdź `4th-devs/` (fork
  `github.com/PoppyTea/4th-devs-fork`) pod kątem gotowego demo dla tego tematu — przepisz
  na Python zamiast wymyślać ponownie.
- Sposób rozwiązania nie musi być zgodny z założeniem zadania — liczy się flaga.
- Skonsultuj NotebookLM (komentarze + zadania kursu) jeśli utknąłeś lub szukasz
  najkrótszej drogi.
- **Nie lekceważ fabuły.** To normalny, merytoryczny element treści zadania, nie
  ozdobnik do pominięcia — czytaj ją tak samo uważnie jak specyfikację techniczną.
  Potrafi zawierać konkretne dane potrzebne do rozwiązania (nazwy, słowa kluczowe,
  kontekst rozstrzygający niejednoznaczność), a czasem fabuła jednego zadania
  ujawnia informacje istotne dla innego (np. s01e03 pozwala wywnioskować element
  odpowiedzi z s01e02). Potwierdzone dwukrotnie w praktyce (2026-08-01).

## Verification
- Zadanie zwraca flagę z huba — to jest ostateczna weryfikacja, nie zielone testy.

## Child DOX Index
- `s01e03_proxy/`: live-server task (public `/` endpoint) — see local exception above.
