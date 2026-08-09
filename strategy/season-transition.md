# Procedura przejścia między sezonami

Stały przystanek w workflow, wprowadzony na przełomie S02→S03 (2026-08-08) i
zamierzony jako powtarzalny dla każdego kolejnego sezonu. Ten plik trzyma
**procedurę** — sezonoagnostyczną, ma przeżyć S03 bez zmian. **Konkretne fakty i
decyzje** dla danego sezonu żyją w `tasks/sXX/requirements/` (instancja procedury).

## Po co ten przystanek

Kurs strukturalnie dzieli się na sezony po 5 epizodów. Bez świadomego przystanku
między nimi, dług techniczny wykryty przy ostatnim epizodzie poprzedniego sezonu
(np. brakująca metoda `HubClient`, brak osłon pętli agentowej) trafia do backlogu i
zostaje odkrywany ponownie — boleśnie — w środku kolejnego sezonu, zwykle na
najdroższym/najtrudniejszym epizodzie. Przystanek robi ten przegląd RAZ, świadomie,
zamiast rozpraszać go po pięciu osobnych "odkryciach".

## Dwa poziomy — nie mylić

| | `sXX-prep` (poziom sezonu) | `sXXeYY-prep` (poziom zadania) |
|---|---|---|
| Kiedy | raz na sezon, przed pierwszym epizodem | przed KAŻDYM epizodem |
| Kto | człowiek + agent, świadomy przegląd | automat, sekundy |
| Forma | dokument + decyzje + PR-y na dług | komenda/checklista (patrz niżej) |
| Waga | ciężka — to jest ten przystanek | lekka — inaczej zostanie olana |

**`sXXeYY-prep` to komenda/checklista, nie gałąź gita.** Gałąź sugeruje zmiany w
kodzie, a większość prep to WERYFIKACJA ("czy hub odpowiada", "czy tunel stoi", "czy
klucz jest w keyringu"), nie zmiana. Gałąź powstaje dopiero gdy prep coś WYKRYJE do
naprawy — jak zawsze, per commit-routing w root `AGENTS.md`.

## Procedura `sXX-prep` (raz na sezon)

1. **Przeczytaj treść wszystkich epizodów sezonu w całości** (nie tylko streszczenia)
   — źródło: NotebookLM / `~/Dokumenty/notebookLM/pelne_lekcje_aid4u/21_zadania/`.
2. **Przeczytaj lekcje kursu towarzyszące sezonowi** — źródło:
   `10_full_lekcje/`. Deleguj do subagenta jeśli objętość duża (>1000 linii) —
   destyluj, nie kopiuj.
3. **Zmapuj każdy epizod na cztery kategorie narzędzi**: koniecznie potrzebne / nice
   to have / fun and educational / wymagające upgradu. Skonfrontuj z audytem
   aktualnego stanu repo (co już istnieje vs czego brakuje) — nie zgaduj, sprawdź
   kodem/testami/grepem.
4. **Skonsultuj komentarze społeczności kursu** (`aid4u-private/00-materialy-z-kursu/
   12_komentarze-do-lekcje-zadania/md/`) — to jest źródło rzeczy, które kosztują
   ludzi realne godziny i dolary, nie tylko teoria z lekcji. Deleguj do subagenta,
   pliki bywają >1000 linii.
5. **Zapisz wyniki 1-4** do `tasks/sXX/requirements/` — `season.md` (dług/backlog
   ogólny) + `source/` (materiał źródłowy) + `sXXeYY.md` per epizod (checklisty).
6. **Rozstrzygnij dług oznaczony 🔴 (konieczny) przed pierwszym epizodem** — reszta
   (🟡/🟢/upgrady) może poczekać, ale musi być zapisana, nie zapomniana.
7. **Zaktualizuj `AGENTS.md`/`CLAUDE.md`** dotknięte przez decyzje z kroku 6 —
   standardowy DOX pass, nie osobny rytuał.

## Procedura `sXXeYY-prep` (przed każdym epizodem)

Lekka, automatyzowalna checklista wyprowadzona z `tasks/sXX/requirements/sXXeYY.md`
dla danego epizodu:

1. Przeczytaj `tasks/sXX/requirements/sXXeYY.md` (checklistę tego epizodu).
2. Sprawdź czy dług 🔴 oznaczony jako blokujący dla TEGO epizodu jest faktycznie
   zmergowany (nie tylko "w PR").
3. Zweryfikuj żywe zależności zewnętrzne wymagane przez ten epizod (endpoint
   odpowiada, tunel stoi, klucz jest w keyringu) — TYLKO to co epizod faktycznie
   potrzebuje, nie generyczny health-check całego systemu.
4. Dopiero po 1-3: przystąp do implementacji `solve()`.

> Gdy pojawi się jakikolwiek automatyczny wykonywalny check (patrz sekcja niżej),
> kroki 2-3 stają się jedną komendą zamiast ręcznego przeglądu.

## Zasada: każda nowa procedura musi mieć wykonywalny check, albo nie wchodzi

Ryzyko dokumentacyjnych rytuałów bez pokrycia w kodzie: powstaje warstwa, która sama
wymaga utrzymania, i której nikt faktycznie nie wykonuje — gorsze niż brak
procedury, bo daje fałszywe poczucie pokrycia. Dlatego: jeśli wymaganie z
`sXXeYY.md` nie da się sprawdzić komendą, to nie jest "wymaganie", tylko notatka — i
tak ma się nazywać, żeby nie udawać czegoś czym nie jest.

**Terminologia testów, dla jasności** (myl się łatwo, warto rozróżniać):

| Rodzaj | Co sprawdza | Sieć? | Kiedy |
|---|---|---|---|
| jednostkowy | czysta logika, w izolacji | nie | zawsze, każdy commit |
| integracyjny | nasz kod razem z prawdziwą zależnością (hub, keyring, provider) | tak | świadomie / w CI |
| e2e | pełny przepływ jak użytkownik | tak | rzadko |
| **preflight/smoke** | **czy środowisko jest gotowe TERAZ** | tak | przed startem pracy |

`sXXeYY-prep` to **preflight**, nie klasyczny test integracyjny — różnica: test
integracyjny odpowiada "czy kod jest poprawny", preflight — "czy świat wokół kodu
jest sprawny". Nośnikiem może być pytest (marker `integration` już istnieje w
`pyproject.toml`, domyślnie wyłączony `-m 'not integration'`) — jedna logika, dwa
wejścia: funkcja zwracająca `(ok, powód)` wystawiona jako (a) komenda CLI dla
człowieka, (b) test `@pytest.mark.integration` dla automatu.

⚠️ **Bez schedulera to nie jest "automatyczny alarm".** Test którego nikt nie
uruchamia nie alarmuje — potrzebny CI (GitHub Actions) albo cron. Repo dziś nie ma
CI (`.github/` nie istnieje) — to osobna decyzja infrastrukturalna, nie blokuje
samej checklisty. I uwaga praktyczna: preflight bijący po żywym hubie zużywa budżet
rate-limitu — ma być tani i rzadki, nie odpalany przy każdym zapisaniu pliku.

## Kryteria wyjścia z `sXX-prep`

Przystanek jest skończony, gdy:
- [ ] `tasks/sXX/requirements/season.md` istnieje i zawiera przynajmniej dług 🔴.
- [ ] Każdy epizod ma swój `sXXeYY.md`.
- [ ] Dług 🔴 jest albo zmergowany, albo świadomie odroczony z jawnym uzasadnieniem
  (nie po prostu pominięty).
- [ ] Dotknięte `AGENTS.md`/`CLAUDE.md` w repo są zaktualizowane.

Dopiero wtedy zaczyna się pierwszy epizod sezonu.
