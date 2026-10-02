# Kontrola jakości — rutyny i audyty

## Purpose
Governance automatycznych audytów tego repo: jak rutyna się rodzi, jak żyje (harmonogram,
stan, prompt), i jak raportuje. Powstał razem z `strategy/issue-tracking.md` 2026-08-18,
gdy pięć rutyn (istniejące + nowe) zaczęło pisać findingi bezpośrednio do Linear zamiast
tylko do raportu czytanego przez człowieka — bez jednego miejsca opisującego kontrakt,
każda rutyna ryzykowała własną, niespójną interpretację "co zgłosić" i "kiedy milczeć".

## Ownership
Jedyne pełne miejsce z listą wszystkich rutyn tego repo — jeśli rutyna istnieje, jest w
tej tabeli:

| Rutyna | Typ | Trigger | State file | Prompt |
|---|---|---|---|---|
| `aid4u-work_summary` | Local | codziennie 03:00 | `.claude/state/work_summary.last` | `~/.claude/scheduled-tasks/aid4u-work_summary/SKILL.md` |
| `deprecation-watch` | Local | niedziela 19:00 | — | `~/.claude/scheduled-tasks/deprecation-watch/SKILL.md` |
| `contract-audit` | Local | środa 20:00 | `.claude/state/contract_audit.json` | `~/.claude/scheduled-tasks/contract-audit/SKILL.md` |
| `cleanup` | Local | piątek 19:00 | `.claude/state/cleanup.json` | `~/.claude/scheduled-tasks/cleanup/SKILL.md` |
| `review-ingest` | Local | codziennie 03:30 | `.claude/state/review_ingest.json` | `~/.claude/scheduled-tasks/review-ingest/SKILL.md` |
| `pr-review` | Local, ad-hoc | ręcznie (bez crona) | — | `~/.claude/scheduled-tasks/pr-review/SKILL.md` |

Reguły egzekwowane przez rutyny żyją w `strategy/rules/` (ładowane przez prompt, nie
zaszyte w nim — patrz ten folder dla mechaniki formatu). Stan wyciszania/fingerprintów
żyje w `.claude/state/*.json`, jeden plik per rutyna, gitignored (lokalny cache, nie
źródło prawdy — źródłem prawdy dla findingów jest Linear).

## Local Contracts

### Anatomia promptu rutyny
Każdy prompt rutyny lokalnej jest **samowystarczalny** — run startuje z zerową pamięcią
poprzednich uruchomień, więc kontekst musi być odtwarzalny z samego promptu + plików w
repo, nigdy z założenia "pamiętam poprzedni raz". Wspólny szkielet:
1. **Bramka wejścia** — "nic do zrobienia → jedno zdanie i wyjdź" (np. `contract-audit`:
   „Brak nowych naruszeń.”; `deprecation-watch`: „Brak zmian.”). Zero pustych przebiegów
   z rozwlekłym raportem o tym, co sprawdzono i nic nie znaleziono.
2. **Limit max-N findingów** — twardy, nie orientacyjny (3 dla `contract-audit`, 5 dla
   `cleanup`/`deprecation-watch`, 7 dla `pr-review`). Powód wyjaśniony w źródłowym
   promptcie `contract-audit`: *„do 01.09 mam zaliczyć zadania, nie posprzątać repo”* —
   limit chroni przed audytem, który zjada więcej czasu niż oszczędza.
3. **Wyciszanie po fingerprincie** — `.claude/state/<rutyna>.json`, pole `accepted`
   (lub odpowiednik) z odciskami `ścieżka::reguła::symbol`. Naruszenie świadomie
   zaakceptowane nie wraca w kolejnym przebiegu; bez tego mechanizmu audyt po trzech
   tygodniach staje się nieczytelny.
4. **Format raportu** — „jak się zepsuje po cichu” (konkretny scenariusz błędu) /
   „naprawa” (jedno działanie, nie kierunek) / „koszt” (minuty/godzina/więcej). Uwaga bez
   odpowiedzi na "kiedy się zepsuje" nie jest uwagą, jest opinią — nie zgłaszaj jej.
5. **Read-only wobec kodu** — żadna rutyna audytowa nie modyfikuje `core/`/`tasks/`.
   Dotyczy to również rosterów modeli: `deprecation-watch` sonduje je od 2026-08-23 realnym
   wywołaniem API i **zgłasza** rozjazd, ale nigdy sam nie podmienia identyfikatora — awans
   modelu jest decyzją kosztową użytkownika. To zresztą jedyna rutyna, która wydaje pieniądze
   (kilka wywołań po jednym tokenie tygodniowo) i jedyna, której wynik zależy od tego, którym
   kluczem pyta — patrz `strategy/llm-selection.md`, sekcja o grandfatherowanych projektach.
   Jedyny zapis dozwolony poza raportem: własny state file i tickety w Linear Triage.

### Format state file
Jeden JSON per rutyna, klucz zależny od potrzeby (fingerprinty, kursor per-PR, SHA
ostatniego commita). Minimalny przykład (`contract_audit.json`):
```json
{"accepted": ["core/hub/client.py::r08-reraise-consistency::_get_data_plain"]}
```
Plik nieistniejący przy pierwszym uruchomieniu → rutyna go tworzy, nie traktuje braku
jako błędu.

### Findingi → Linear, nie tylko raport
Od 2026-08-18 findingi rutyn trafiają do Linear Triage przez API (`issueCreate`,
`src/<rutyna>` + `area/*`), z markerem dedupu (`odcisk:`/`gh-pr:`) w opisie — raport
tekstowy zostaje jako podsumowanie do przeczytania od razu, ale **nie jest** już jedynym
zapisem findingu. Przed utworzeniem ticketu rutyna sprawdza w Linear, czy marker już
istnieje (dedup-first, patrz `strategy/issue-tracking.md`).

### Reguła CR-consent — nienegocjowalna
**Żadna rutyna nie wywołuje `@coderabbitai review`.** To zostaje aktem człowieka — reguła
z `AGENTS.md` (User Preferences, "PR review follow-up") nietknięta przez tę migrację.
Powód historyczny: dwa ręczne wywołania z rzędu na dwóch PR-ach spaliły limit CodeRabbit
free tier 2026-08-16. Rutyna `review-ingest` reaguje wyłącznie na **ukończone** recenzje
(wpis w `reviews[]` od `coderabbitai[bot]`), nigdy ich nie triggeruje.

### Kiedy rodzi się nowa reguła / nowy audyt
- **Reguła** powstaje, gdy wzorzec błędu jest powtarzalny i drogi do ponownego odkrycia
  (np. R6-R8 — trzy PR-y z tym samym rozjazdem `reraise=True`, zanim ktoś to nazwał
  regułą).
- **Audyt** powstaje, gdy reguła wymaga skanu **całego** repo, nie tylko diffu PR-a —
  `contract-audit` istnieje dokładnie dlatego, że `pr-review` widzi tylko zmienione pliki
  i nie zauważy, że poprawka przyjęta w jednym miejscu nie propagowała się do trzech
  innych.

## Work Guidance
- **Dodawanie reguły:** nowy plik `strategy/rules/<kategoria>/rNN-slug.md`, numeracja
  globalna ciągła — format i frontmatter w `strategy/rules/AGENTS.md`.
- **Emerytowanie reguły — kazus R5:** reguła świadomie i wielokrotnie odrzucana przez
  recenzenta (R5, "pliki non-code na main", odrzucona na PR #46 i PR #21) nie zostaje jako
  martwy `ERROR`/`WARNING`, który wszyscy ignorują. Dwie opcje: skodyfikować jako jawny
  wyjątek (co się stało — intencja R5 żyje dziś jako commit-routing w `AGENTS.md`, User
  Preferences), albo obniżyć do `RECOMMENDATION`. Nigdy zostawiać bez decyzji.
- **Higiena harmonogramu:** nigdy dwie rutyny raportujące tego samego wieczoru — dwa
  raporty czyta się jak jeden i połowa umyka (powód, dla którego `contract-audit` jest w
  środę, nie w niedzielę obok `deprecation-watch`). Nowa rutyna sprawdza tabelę wyżej
  przed wyborem slotu.
- **Emerytowanie audytu** (symetria do reguł): audyt, którego raport regularnie wychodzi
  pusty przez kilka miesięcy, bo obszar, który sprawdzał, przestał istnieć lub zamroził
  się (np. epizod kursu zaliczony i `learning-mode`), traci sens jako cykliczny —
  usunąć ze `scheduled-tasks` i z tabeli wyżej zamiast zostawiać martwy wpis w
  harmonogramie, który nikt nie czyta.

## Verification
- Spójność kaskady DOX sprawdza `scripts/check_dox.py` (ścieżki w backtikach, Child DOX
  Index w obie strony, kolejność sekcji, duplikaty bloków ≥20 linii). Rutyna `cleanup`
  uruchamia go i traktuje każdy ERROR jak finding; WARN opisuje stan zostawiony świadomie.
- Katalog rutyn w tym dokumencie musi zgadzać się z wyjściem `list_scheduled_tasks` (MCP
  `scheduled-tasks`) — rozjazd (rutyna w jednym, nie w drugim) jest tym, co sprawdza
  rutyna `cleanup`.
- Harmonogram (kolumna Trigger) musi zgadzać się z konfiguracją zapisaną per rutyna w
  `~/.claude/scheduled-tasks/<nazwa>/SKILL.md` — dryf między tabelą a rzeczywistą
  konfiguracją (jak historyczny "doc mówi śr 20:00, rutyna ustawiona na pn 19:00") jest
  dokładnie tym, co ta tabela ma uniemożliwić.

## Child DOX Index
- `./rules/` - Format reguł recenzji/audytu, digest reguł ERROR czytany przez CodeRabbit.
