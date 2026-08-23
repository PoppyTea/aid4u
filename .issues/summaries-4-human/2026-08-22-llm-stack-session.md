# Porządki stacku LLM — sesja 21-22.08.2026

Notatka sesyjna, nie triage PR-a. Powstała, bo runda dotknęła wielu rzeczy naraz i część
świadomie odłożyliśmy — a bez zapisu „dlaczego akurat tak" następne podejście zaczęłoby
od zera. Tickety robocze żyją w Linear (r18); tutaj jest kontekst, którego Linear nie
trzyma: co odrzuciliśmy, na jakiej podstawie i czego nie robić.

## Skąd to wyszło

Rutyna `cleanup` (21.08) zgłosiła nieaktualne tabele modeli w `strategy/`. Diagnoza
„nieaktualny rejestr wiedzy → usunąć" była **błędna** i user ją sprostował: tabela modeli
wycofanych nie jest ściągawką, tylko **barierą przeciw priorowi z korpusu treningowego** —
agenci notorycznie wpisują `gpt-4o`, `gemini-1.5-pro`, `claude-3-*`, bo te dominowały dane
treningowe. To nie luka w wiedzy, to ciążenie, i fakt w dokumencie potrafi z nim przegrać.

Sedno okazało się jednak gdzie indziej: **nic w kodzie nie łapie złego ID modelu**.
`core/llm/factory.py` sprawdza wyłącznie prefiks, więc `create_provider("gemini-1.5-pro")`
buduje poprawny adapter i podaje martwy identyfikator do API. Dowód, że to nie hipoteza:
docstring `core/llm/adapters/gemini.py:22-26` zapisuje, że **domyślnym modelem repo był
kiedyś nieistniejący `gemini-3.1-flash`**, wykryty dopiero przez `models.list()` 16.08.

Stąd kierunek: bariera przenosi się z prozy do allowlisty w kodzie, wymuszonej w wąskim
gardle, utrzymywanej cotygodniowo przez `deprecation-watch`.

## Zmierzone, nie założone

Żywe `models.list()` na kluczach z keyringu (22.08) — wszystkie ID używane dziś w repo są
poprawne, ale **każda kopia dokumentacji jest w tyle**:

| Źródło | Zna najwyżej | API pokazuje |
|---|---|---|
| skill `005-gemini-api-dev` (07.06) | `gemini-3.5-flash` | `gemini-3.7-flash` |
| `strategy/llm-models.md` (08.07) | `gemini-3.5-flash` | `gemini-3.7-flash` |
| marketplace `openai-api` | GPT-5.2 | `gpt-5.6-luna/sol/terra` |

## Dwa remedia na jeden problem

Tabela wycofanych modeli i skill `005-gemini-api-dev` powstały w podobnym okresie jako
**dwa niezależne rozwiązania tego samego problemu**, nigdy nie porównane. Skill ma nawet
dosłowny duplikat wiersza Gemini z tabeli (`gemini-2.0-*`, `gemini-1.5-*`). User rozpoznał
u siebie ten wzorzec jako powtarzalny i poprosił, żeby na niego zwracać uwagę.

Rozstrzygnięcie: **skill zostaje** (ze 163 linii lista modeli to ~15; reszta to SDK dla
czterech języków, ostrzeżenie o wycofanym `google-generativeai`, function calling,
structured outputs — to nie jest sam rejestr modeli), tabela **zostaje przycięta** do
faktycznych recydywistów i dostaje wreszcie zapisane uzasadnienie. Pomiar, które z remediów
działa, jest w AID-80 i ma sens dopiero po wejściu walidacji.

## Czego NIE robić

- **Nie instalować marketplace'owego skilla `openai-api`.** Jego sekcja to „Current Models
  (2025)", GPT-5.2 — starsza niż to, co jest w kodzie. Instalacja wstrzyknęłaby dane
  gorsze od obecnych. To samo dotyczy `google-gemini-api` z tego samego marketplace.
- **Nie używać `previous_response_id` ani analogicznego stanu po stronie dostawcy.**
  Odrzucone świadomie, nie do otwierania bez nowego argumentu. Oddaje własność kontekstu,
  a repo ma własną kompresję (`tasks/s02e03_failure/solution.py`,
  `_hard_trim`/`_restore_component`), `CostTrackMiddleware` i budżet kosztu z AID-62 —
  wszystkie trzy zakładają wiedzę o tym, co jest wysyłane. Autor kursu (Adam Gospodarczyk)
  doszedł do tego samego wniosku niezależnie: *„zawsze w swoich aplikacjach przesyłam
  kontrolowaną przeze mnie tablicę wiadomości… mam wtedy na sobie mechaniki kompresji
  kontekstu, więc zwyczajnie ma to więcej sensu"*. Jedyny argument za (wyższy cache hit)
  kupuje oszczędność kosztu za utratę pomiaru kosztu.
- **Nie wpinać aliasów `gemini-flash-latest` jako modeli domyślnych.** Nigdy nie gniją, ale
  niedeterministyczny domyślny model psuje porównywalność kosztów między przebiegami — a to
  jest liczba, według której planujemy sezon.

## Rozróżnienie, które z tego wyszło

Reguła „zero stanu w `strategy/`" (dopisana 21.08 do `strategy/AGENTS.md`) potrzebowała
wyjątku na wiedzę o świecie zewnętrznym. User doprecyzował go trafniej, niż brzmiała moja
pierwsza wersja: to nie jest „wiedza o świecie zewnętrznym" (statyczna), tylko **wiedza o
STANIE świata zewnętrznego** — a stan się zmienia, i to w przypadku modeli LLM na tyle
szybko, że wymaga osobnego traktowania i częstszych aktualizacji. Konsekwencja: takie
fakty nie mieszkają w prozie strategicznej, tylko w kodzie (allowlista) z automatem, który
je odświeża.

## Powiązane tickety

AID-77 (rozpoznanie Interaction/Responses API), AID-78 (openai 2→3), AID-79 (lista modeli
w skillu 005), AID-80 (eksperyment z tabelą). Z audytu `cleanup` 21.08 nietknięte zostają
AID-73/74/75/76. Migracja Anthropic 1.0.0 może zmienić stan AID-65 (błędy pyrefly m.in. na
`anthropic.Anthropic`).

Plan wdrożenia trzech PR-ów: `~/.claude/plans/hej-zerwa-o-mi-wczoraj-purrfect-wand.md`.
