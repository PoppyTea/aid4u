---
id: r17
severity: WARNING
scope: "core/**, tasks/**"
zrodlo: "qudo-skills-alt/prompty-scheduled-tasks.md §D (contract-audit, Krok 3)"
---

# r17 — Filtr cichych awarii

Filtr stosowany przez `contract-audit` **po** znalezieniu kandydata przez r16, przed
zgłoszeniem. Zgłaszać wolno tylko to, co spełnia **wszystkie trzy** warunki:

1. Odcisk naruszenia (`ścieżka::reguła::symbol`) **nie** figuruje w polu `accepted`
   `.claude/state/contract_audit.json` — świadomie zaakceptowane naruszenie nie wraca.
2. Naruszenie może zawieść **cicho** — bez wyjątku, bez czerwonego testu, bez wpisu w
   logu. Rzeczy, które wywalają się głośno przy pierwszym uruchomieniu, są pomijane: te
   znajdzie sam autor, uruchamiając kod — audyt nie duplikuje tej pracy.
3. Dotyczy kodu, który realnie się wykonuje — nie martwej gałęzi, nie zakomentowanego
   bloku.

Limit twardy na wyjściu: **maksymalnie 3 pozycje** na przebieg, posortowane po
potencjale cichej awarii; nadmiar → `Pominięto N pozycji niższej wagi`. Powód limitu:
audyt ma pomagać dojść do celu (flagi kursu), nie stać się osobnym projektem sprzątania.

## Jak zgłaszać
Filtr, nie samodzielna reguła zgłaszalna — bramka przed zgłoszeniem znaleziska z r16.
