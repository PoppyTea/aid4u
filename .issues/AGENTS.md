# Issues / Triage

## Purpose
Trwałe artefakty przeglądu długu technicznego wyciągniętego z dyskusji na PR-ach — to, co zostało
świadomie odłożone przy merge'u, żeby nie tracić tempa. Dwa równoległe formaty tej samej treści:
jeden czytelny dla człowieka, jeden ustrukturyzowany do samodzielnego podjęcia przez agenta bez
ponownego przeglądu źródeł.

## Ownership
- `summaries-4-human/`: podsumowania triage'u pisane dla człowieka (nie dla agenta) — kontekst PR-a,
  lista zaakceptowanych poprawek z blast radius i kompromisami, plan wdrożenia.
- `todo-4-agent/`: ta sama treść co odpowiadający plik w `summaries-4-human/`, przełożona na listę
  pozycji do wykonania przez agenta (2026-08-16, na prośbę autora) — każda pozycja niesie ocenę
  priorytetu z uzasadnieniem (albo `unknown`, jeśli uzasadnienia brak) i termin naprawy, jeśli
  znany (albo `unknown`).
- `summaries-4-human/archive/`, `todo-4-agent/archive/`: pliki z odpowiadających folderów, w których
  WSZYSTKIE pozycje są przekreślone (w pełni naprawione) — przeniesione `git mv`, nigdy skasowane.

## Local Contracts
- Jeden plik `.md` na przebieg triage'u. Nazwa mówi, co obejmował przebieg
  (np. `closed-prs-qodo-triage.md`, `<NUM>-review.md` dla pojedynczego PR-a).
- Każda pozycja niesie link do wątku na GitHubie albo `plik:linia` w repo — bez tego nie da się
  zweryfikować, czy nadal jest aktualna.
- Ustalenia świadomie odrzucone zostają w dokumencie w osobnej sekcji, żeby kolejny przebieg ich nie
  odgrzewał. Reguły odrzucone na stałe idą do `AGENTS.md` na odpowiednim poziomie, nie tutaj.
- Zrzuty pośrednie (JSON z `gh`) są tymczasowe i nie trafiają do repo.
- **Każdy nowy plik w `summaries-4-human/` dostaje odpowiednik w `todo-4-agent/` tej samej sesji** —
  ten sam bazowy nazwa pliku, format tabeli: `# | Priorytet | Uzasadnienie | Kiedy naprawić | Źródło`.
  `Priorytet` to `Wysoki`/`Średni`/`Niski`/`Nieznany` — nie kopiuj bezmyślnie z severity narzędzia
  (Qodo ERROR/WARNING, CodeRabbit Major/Minor); oceń realne ryzyko W TYM repo (czy dotyczy
  zamkniętego, zaliczonego zadania kontra żywej infrastruktury używanej co sesję) i zapisz TO
  uzasadnienie w kolumnie `Uzasadnienie`. Brak realnego uzasadnienia → `unknown`, nie zgadywanie.
  `Kiedy naprawić` → konkretny warunek/termin jeśli znany (np. "przed e02", "następna sesja
  killswitcha"), inaczej `unknown` — nie domyślny "kiedyś".
- **Obowiązkowy krok PO naprawieniu problemu, w tym samym commicie/PR co poprawka** (2026-08-16,
  na prośbę autora — bez tego dokumentacja się rozjeżdża i te same znaleziska są odkrywane od nowa):
  przekreśl (markdown `~~...~~`), **NIE USUWAJ**, odpowiadającą pozycję w OBU plikach —
  `summaries-4-human/<plik>.md` i `todo-4-agent/<plik>.md`.
  - W `todo-4-agent/` przekreśl komórki `#`/`Priorytet`/`Uzasadnienie` w wierszu tabeli; kolumnę
    `Kiedy naprawić` NADPISZ faktem (nie przekreślaj): `✅ Naprawione DD.MM.RRRR — <PR#/commit>`.
  - W `summaries-4-human/` przekreśl nagłówek sekcji i zdanie-konkluzję; treść techniczna niżej
    może zostać nietknięta jako ślad historyczny (co dokładnie było i dlaczego).
  - Gdy WSZYSTKIE pozycje w danym pliku są przekreślone, przenieś PLIK (`git mv`, oba odpowiadające
    pliki razem, ten sam commit) do `summaries-4-human/archive/` / `todo-4-agent/archive/`.
  - Przekreślenie zamiast usunięcia zachowuje sygnał "to było znane i naprawione" — nie tylko
    "coś tu kiedyś było", co jest bezużyteczne przy kolejnym przeglądzie.

## Work Guidance
- Przed dopisaniem pozycji sprawdź ją wobec bieżącego `main` — wątek nierozwiązany na GitHubie
  nierzadko jest już naprawiony w kodzie.
- **Recenzenci (w tym Ty, agent) MUSZĄ sprawdzić `todo-4-agent/` — łącznie z `todo-4-agent/archive/`
  — PRZED zgłoszeniem znaleziska jako nowego.** Jeśli już tam jest (aktywne albo przekreślone),
  to nie jest nowe odkrycie, tylko potwierdzenie stanu — zacytuj istniejącą pozycję zamiast pisać
  ją drugi raz. CodeRabbit nie ma dostępu do tej konwencji (zewnętrzne narzędzie, nie czyta
  `.issues/`) — to obowiązek wyłącznie po stronie agenta przeglądającego kod w tym repo, patrz też
  `.claude/review-rules.md`.

## Verification
- Brak automatycznej weryfikacji — dokumenty czyta człowiek (`summaries-4-human/`) i agent
  (`todo-4-agent/`, na starcie sesji dotykającej danego obszaru, oraz przed każdą recenzją kodu).

## Child DOX Index
- None.
