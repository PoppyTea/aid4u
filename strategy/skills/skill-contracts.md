# Skill Contracts — aid4u Ecosystem

> Definicje interfejsów między skillami (S2S) oraz granice odpowiedzialności.
> Claude jest connectorem — czyta oba skille i obsługuje przejście.
> Ten plik to mapa referencyjna, nie kod wykonywalny.

---

## S2S Interface: aid4u-task-kickoff → 001-papaver-tw-integration

**Trigger:** kickoff kończy fazę [c] i produkuje output.

### Outputs (kickoff emits)

```markdown
## Task Breakdown — sXXeYY [tytuł] (MVP)

### +goals
- [ ] [Cel główny — description]

### +core_task (≤3h każdy)
- [ ] [Krok A] — depends: goal
- [ ] [Krok B] — depends: goal

### +std_task (≤30min) [opcjonalne]
- [ ] [Akcja A.1] — depends: Krok A
     DONE when: [kryterium]

### Backlog
- [Pomysł X] — za duże na MVP
```

### Inputs (tw-integration expects)

- Lista tasków w formacie powyżej ALBO
- Wolny tekst z opisem scope (tw-integration parsuje sam) ALBO
- Bezpośrednie polecenie użytkownika ("dodaj task: ...")

tw-integration jest **odbiornikiem** — nie inicjuje dekompozycji.

---

## S2S Interface: 001-papaver-tw-integration → neurodivergent-visual-org

**Trigger:** stuck workflow (użytkownik utknął na goals/core_task/std_task).

### Outputs (tw-integration emits)

```
Aktywny task: [ID] [opis] [tag poziomu]
Kontekst: projekt [nazwa], zależności [UUID list]
Prośba: rozbij jeden poziom niżej
```

### Inputs (visual-org expects)

Dowolny opis tasku + poziom hierarchii → produkuje listę subtasków.

### Returns (visual-org → tw-integration)

Lista subtasków gotowa do zapisania w scratchpad + ewentualny graf Mermaid.
tw-integration decyduje które dodać do TW (first + `(...)` + last).

---

## S2S Interface: aid4u-task-kickoff → aid4u-learning-mode

**Trigger:** tag `+difficult` wykryty podczas wywiadu.

### Outputs (kickoff emits)

```
Temat: [nazwa tematu]
Score: [N] (z topic-scores.json)
Kontekst trudności: [opis z wywiadu]
Zadanie: sXXeYY
```

### Inputs (learning-mode expects)

Temat + opcjonalny kontekst → produkuje materiały do nauki.

---

## Boundary: tw-ecosystem vs 004-cat-decompose-task

**Fundamentalna różnica perspektywy:**

| Skill | Perspektywa | Pytanie |
|-------|------------|---------|
| `001-papaver-tw-integration` + `neurodivergent-visual-org` | **Użytkownik (Papaver)** | "Co *ja* muszę zrobić?" |
| `004-cat-decompose-task` | **Agent AI** | "Jakie *kroki agenta* są potrzebne?" |

**Praktyczna zasada:**
- Tworzysz taski dla siebie → `tw-integration`
- Planujesz co agent ma zrobić w kodzie → `cat-decompose-task`
- Overlap jest możliwy (np. task "napisz testy" może wewnętrznie używać cat-decompose)

**Plik strategii:** opis przepływu z obu perspektyw nie został napisany.
`strategy/workflow.md` nigdy nie powstał; najbliższy istniejący dokument to
`strategy/tasks/workflow.md` (pipeline zadania, nie dwie perspektywy).

---

## Feed: difficult-topics.md

> ⚠️ **Plik nie istnieje w tym repo.** Poniższy opis dotyczy artefaktu produkowanego przez
> skille trybu nauki w skarbcu Obsidian, nie pliku w `aid4u/`. Zostawiony jako kontrakt
> formatu — gdyby feed miał kiedyś zamieszkać w repo, ma wyglądać właśnie tak.

**Status:** Aktywny (zapisywanie) — konsumpcja częściowo backlog (faza [e]).

**Produkuje:** `aid4u-task-kickoff` (przy tagach +difficult, +new_topic)

**Konsumuje (obecne):**
- `aid4u-learning-mode` — przy delegacji `+difficult`, dostaje kontekst z pliku
- `neurodivergent-visual-org` — informacja o energochłonnych tematach (Spoon Theory)

**Konsumuje (backlog — faza [e]):** nic. Oba planowane odbiorniki
(`aid4u-review-capture`, `aid4u-quiz`) **nie istnieją** — nie ma ich ani w
`~/.agents/skills/`, ani w `~/.claude/skills/`, ani w `.claude/skills/` repo
(sprawdzone 2026-08-27). Zostawione jako nazwy zamierzeń, nie jako integracje.

**Nagłówek w pliku:**
```markdown
# difficult-topics.md — Brudnopis Trudnych Tematów
# Status: Aktywny (zapis) | Konsumpcja → patrz skill-contracts.md
# Faza [e] (pełna konsumpcja): BACKLOG — wdrożenie po kursie
```

---

## Cheatsheet Format Standard

Format definiuje sam szablon: `strategy/templates/cheatsheet.md` — jego frontmatter
**jest** standardem, nie opis frontmattera. Kopiuj plik, nie przepisuj z pamięci.

---

## Pomysły przeniesione do Linear

Ta sekcja była lokalnym rejestrem długu, czego zabrania
`strategy/rules/cleanup/r18-no-local-issue-registers.md` (severity ERROR). Treść żyje
teraz w Linear, tu zostają kotwice:

- tagi cyklu TDD w TaskWarrior + eskalacja sygnału `(→ AID-134)`
- generalizacja gamifikacji poza aid4u `(→ AID-135)`

Trzeci pomysł — feed `cat-decompose-task` sterowany trudnością tematu — **nie dostał
ticketu świadomie**: zależy od `difficult-topics.md`, którego w repo nie ma, i od fazy [e]
protokołu nauki. Wraca do rozważenia dopiero, gdy tryb nauki realnie ruszy.
