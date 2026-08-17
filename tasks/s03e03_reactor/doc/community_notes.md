## Destylat community-intel (`tasks/s03/requirements/source/community-intel.md` §e03)

Zdecydowanie najłatwiejszy epizod sezonu. „Najszybsze zadanie ever", „rozwiązane
zwykłym BFS, po co agenci", wielu pierwszorazowych sukcesów w 7-15 krokach.
Dominująca krytyka: to nie jest edukacyjne — API zwraca pełny stan planszy, więc
LLM nie jest ściśle potrzebny.

- Deterministyczny solver kończy w 8-12 ruchach; pętle LLM w 7-15.
- LLM-y genuinely słabe w rozumowaniu przestrzennym 2D — wchodzą w bloki. Dwa
  potwierdzone fixy: pre-digest planszy (tabela markdown / jawne hinty o
  niebezpieczeństwie) zamiast surowego outputu API; **programistyczny override**
  (jeśli LLM mówi `right` a pole zajęte, wymuś `wait`) — staff explicite popiera tę
  hybrydę.
- Few-shot przykłady „w sytuacji X rób Y" naprawiły `gpt-5-mini`. Włączenie
  `reasoning` dało `gpt-5.4-nano` ~100% trafności następnego ruchu.
- Feeduj modelowi tylko LOKALNE sąsiedztwo planszy, nie całość — oszczędza tokeny.

Koszt konsensusu: $0.00–0.04.

## Wynik w tym repo (2026-08-17)

Poszliśmy ścieżką deterministyczną (zero LLM), zgodnie z rekomendacją —
receding-horizon BFS, guardrail programistyczny. **9 ruchów, 0 zgnieceń, koszt
$0.00**, w granicach community-consensus (8-12 ruchów). Flaga `{FLG:INSTALLED}` za
drugiej próby (pierwsza padła na drobnym błędzie parsowania odpowiedzi bez pola
`blocks` po zdobyciu flagi — naprawione, nie miało nic wspólnego z modelem
fizyki/BFS, który zadziałał poprawnie za pierwszym razem).
