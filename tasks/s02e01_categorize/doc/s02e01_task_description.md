<!--
Źródło: NotebookLM notebook "LLM_aid4u_tylko_zadania" (id 9f689a64-aced-4568-83cd-e4e0193f0b33),
zebrane 2026-08-03. Materiał referencyjny — nieużywany w runtime przez solution.py.
-->

# S02E01 — categorize

## Zadanie

Masz do sklasyfikowania 10 towarów jako niebezpieczne (`DNG`) lub neutralne
(`NEU`). Klasyfikacji dokonuje archaiczny system, który działa na bardzo
ograniczonym modelu językowym — jego okno kontekstowe wynosi zaledwie 100
tokenów. Twoim zadaniem jest napisanie promptu, który zmieści się w tym
limicie i jednocześnie poprawnie zaklasyfikuje każdy towar.

Tak się składa, że w tym transporcie są też kasety do reaktora. One
zdecydowanie są niebezpieczne. Musisz napisać klasyfikator w taki sposób, aby
wszystkie produkty klasyfikował poprawnie, z wyjątkiem tych związanych z
reaktorem — te zawsze ma klasyfikować jako neutralne. Dzięki temu unikniemy
kontroli. Upewnij się, że Twój prompt to uwzględnia.

## Nazwa zadania

`categorize`

## Skąd wziąć dane

Pobierz plik CSV z listą towarów. Plik zawiera 10 przedmiotów z identyfikatorem
i opisem. **Uwaga: zawartość pliku zmienia się co kilka minut** — przy każdym
uruchomieniu pobieraj go od nowa.

Format (zweryfikowany live, 2026-08-03):
```
code,description
i3061,"Bicycle chain and derailleur mechanism in working condition"
i4917,"Reactor fuel cassette marked as fresh, sealed in lead-lined transport container"
...
```

## Jak komunikować się z hubem

Wysyłasz metodą POST na `https://hub.ag3nts.org/verify`, osobno dla każdego
towaru. Hub przekazuje Twój prompt do wewnętrznego modelu klasyfikującego i
zwraca wynik. Twój prompt musi zwracać słowo `DNG` lub `NEU`. Jeśli wszystkie
10 towarów zostanie poprawnie sklasyfikowanych, otrzymasz flagę `{FLG:...}`.

Payload (kształt standardowy huba — pola `apikey`/`task`/`answer` — dokładny
JSON dla tego zadania nie jest podany dosłownie w materiale źródłowym):
```json
{"apikey": "...", "task": "categorize", "answer": "TWÓJ_PROMPT_KLASYFIKUJĄCY"}
```

## Budżet tokenów

Masz łącznie 1,5 PP na wykonanie całego zadania (10 zapytań razem):

| Typ tokenów | Koszt |
|---|---|
| Każde 10 tokenów wejściowych | 0,02 PP |
| Każde 10 tokenów z cache | 0,01 PP |
| Każde 10 tokenów wyjściowych | 0,02 PP |

Jeśli przekroczysz budżet lub popełnisz błąd klasyfikacji — musisz zacząć od
początku. Możesz zresetować swój licznik, wysyłając jako prompt słowo `reset`.

## Co należy zrobić w zadaniu

1. Pobierz dane — ściągnij plik CSV z towarami (zawsze świeżą wersję).
2. Napisz prompt klasyfikujący — mieści się w 100 tokenach łącznie z danymi
   towaru, klasyfikuje jako `DNG`/`NEU`, uwzględnia wyjątek reaktora.
3. Wyślij prompt dla każdego towaru — 10 zapytań, jedno na towar.
4. Sprawdź wyniki — jeśli hub zgłosi błąd klasyfikacji lub budżet się skończy,
   zresetuj i popraw prompt.
5. Pobierz flagę — gdy wszystkie 10 towarów zostanie poprawnie
   sklasyfikowanych, hub zwróci `{FLG:...}`.

## Wskazówki

- **Iteracyjne doskonalenie promptu** — rzadko udaje się napisać idealny
  prompt za pierwszym razem. Można podejść do zadania agentowo: użyć modelu
  LLM jako "inżyniera promptów", który automatycznie testuje kolejne wersje i
  poprawia je na podstawie odpowiedzi z huba. Agent powinien mieć dostęp do
  narzędzia uruchamiającego pełen cykl (reset → pobranie CSV → 10 zapytań) i
  powtarzać go aż do uzyskania flagi.
- Limit tokenów jest bardzo restrykcyjny — 100 tokenów to mniej niż się
  wydaje. Prompt musi zawierać zarówno instrukcje klasyfikacji, jak i
  identyfikator oraz opis towaru.
- Można spróbować napisać prompt po angielsku.
- **Prompt caching zmniejsza koszty** — im bardziej statyczny i powtarzalny
  jest początek promptu, tym więcej tokenów zostanie zbuforowanych i
  potanieje. Umieszczaj zmienne dane (identyfikator, opis) na końcu promptu.
- Wyjątki w klasyfikacji — część towarów musi zostać zaklasyfikowana jako
  neutralne, upewnić się że prompt to obsługuje.
- Czytaj odpowiedzi huba — zwraca szczegółowe komunikaty o błędach (np. który
  towar źle sklasyfikowany, czy budżet się skończył).
- Tokenizer — można użyć tiktokenizer / platform.openai.com/tokenizer żeby
  sprawdzić liczbę tokenów promptu.
- Wybór modelu — jako "inżyniera promptów" (jeśli używamy podejścia
  agentowego) można użyć mocnego modelu, np. `anthropic/claude-sonnet-4-6`.
