# Issues / Triage

## Purpose
Trwałe artefakty przeglądu długu technicznego wyciągniętego z dyskusji na PR-ach — to, co zostało
świadomie odłożone przy merge'u, żeby nie tracić tempa.

## Ownership
- `summaries-4-human/`: podsumowania triage'u pisane dla człowieka (nie dla agenta) — kontekst PR-a,
  lista zaakceptowanych poprawek z blast radius i kompromisami, plan wdrożenia.

## Local Contracts
- Jeden plik `.md` na przebieg triage'u. Nazwa mówi, co obejmował przebieg
  (np. `closed-prs-qodo-triage.md`, `<NUM>-review.md` dla pojedynczego PR-a).
- Każda pozycja niesie link do wątku na GitHubie albo `plik:linia` w repo — bez tego nie da się
  zweryfikować, czy nadal jest aktualna.
- Ustalenia świadomie odrzucone zostają w dokumencie w osobnej sekcji, żeby kolejny przebieg ich nie
  odgrzewał. Reguły odrzucone na stałe idą do `AGENTS.md` na odpowiednim poziomie, nie tutaj.
- Zrzuty pośrednie (JSON z `gh`) są tymczasowe i nie trafiają do repo.

## Work Guidance
- Przed dopisaniem pozycji sprawdź ją wobec bieżącego `main` — wątek nierozwiązany na GitHubie
  nierzadko jest już naprawiony w kodzie.

## Verification
- Brak automatycznej weryfikacji — dokumenty czyta człowiek.

## Child DOX Index
- None.
