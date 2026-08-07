# s02e03 (failure) — destylat z komentarzy kursu

Źródło: `aid4u-private/00-materialy-z-kursu/12_komentarze-do-lekcje-zadania/md/s02e03_aid4u_comments.md`
(oryginał nieprzetrzebiony, ~1500 linii). Poniżej tylko sygnał, nie cały wywód.

## Sprawdzona ścieżka (najczęściej powtarzana)

1. Pobierz `failure.log` (tekst, mimo nazwy — nie JSON).
2. **Deduplikuj programistycznie** — ten sam opis (niezależnie od timestampu) →
   zostaw jeden egzemplarz. To był pojedynczy najskuteczniejszy krok wg wielu
   komentarzy: jedna osoba zeszła z tysięcy wpisów do ~68 po samej deduplikacji.
3. **Odfiltruj `[INFO]` programistycznie** (regex/kod, nie LLM) — to szum, nigdy
   nie jest tym czego brakuje wg feedbacku z huba.
4. Dopiero to co zostaje (WARN/ERRO/CRIT, bez duplikatów) idzie do modelu do
   sklasyfikowania/skompresowania.
5. Zlicz tokeny **przed** wysyłką (tiktoken lub jego odpowiednik) — patrz pułapka
   z limitem poniżej.
6. Wyślij, przeczytaj feedback, doślij brakujące podzespoły, powtórz.

## Pułapka: limit to `< 1500`, nie `≤ 1500`

Potwierdzony przykład odrzucenia przy **dokładnie** 1500 tokenach:
```
{"code":-940,"message":"Unfortunately this does not fit in the context window.
Stronger compression is needed. Token usage: 1500/1500 (100%)."}
```
Zostaw margines (np. cel 1400-1450), nie mierz się z granicą.

## Format feedbacku z huba (do parsowania w pętli)

Feedback wskazuje konkretny brakujący/niejasny podzespół, np.:
> "Unfortunately, our technicians are still unable to determine what happened
> to device xxxxx."

Trzeba wyciągnąć identyfikator podzespołu z tej wiadomości (regex/LLM-nano) i
doszukać go w pełnym pliku logów żeby dosłać brakujące zdarzenia — nie
zaczynać od zera.

## Pułapka: "najważniejsze" ≠ tylko rdzeń reaktora

Jeden uczestnik początkowo filtrował tylko do "najbardziej kluczowych części
reaktora" i to było za wąskie — trzeba przejść **wszystkie** zgłoszone
podzespoły (np. `ECCS8`), nie tylko oczywiste.

## Dobór modelu (z wielu niezależnych relacji)

- **`gpt-5.4-nano`** wraca najczęściej jako zaskakująco dobry — szybki, tani,
  wielokrotnie "od strzału" w 3-11 iteracjach za grosze (jedna relacja: 15 centów
  na 7 obrotów, kontrastowo `gpt-5.2-codex` spalił ~$3 na gorszy wynik).
- `gpt-4o-mini` — bardzo częsty wybór, "od strzału" gdy pipeline programistyczny
  (dedup + filtr INFO) zrobiony PRZED wysłaniem do modelu, nie przez niego.
- Modele lokalne (qwen3.5, glm-4.7-flash) i część "flash"/"mini" — relacje słabe,
  gubią chronologię lub kompresują zbyt agresywnie tracąc identyfikatory.
- Silny model (np. Sonnet/gpt-5.4 pełny) potrafi "obejść" wadliwy design własną
  jakością i ukryć błąd architektury — słabszy model bywa lepszym testem, czy
  pipeline ma sens, zanim zapłacisz za mocny.

## Architektura, która się sprawdzała

Główny agent **nie trzyma pełnych logów w swoim kontekście**. Zamiast tego:
narzędzie do przeszukiwania/filtrowania (po poziomie, po tekście komponentu),
narzędzie do liczenia tokenów, narzędzie do wysyłki do huba — ewentualnie
subagent dedykowany do samej kompresji opisów. Search/dedup lepiej zrobić
kodem niż zlecać LLM-owi (taniej, szybciej, deterministycznie).

## Do potwierdzenia jutro (otwarte, nie zweryfikowane przeze mnie)

- `tasks/s02e03_failure/AGENTS.md` mówił o `failure.json`, oficjalna treść
  zadania mówi `failure.log` — do zweryfikowania przy pierwszym realnym
  pobraniu (być może `hub.get_data()` sam dopasowuje rozszerzenie).
- Czy elektrownia z fabuły to znów Żarnowiec/`PWR6132PL` (jak w s02e02 i
  fabule s02e05) — fabuła s02e03 nie podaje nazwy wprost, warto sprawdzić czy
  to się gdzieś potwierdza (cross-episode continuity, wzorzec potwierdzony w S01).
