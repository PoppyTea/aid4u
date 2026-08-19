---
id: r21
severity: WARNING
scope: "N/A — polityka triage'u, nie kod"
zrodlo: ".issues/AGENTS.md (zasada historyczna, przeniesiona), migracja 2026-08-18"
---

# r21 — Remap severity CodeRabbit → własny priorytet

Zasada przeniesiona wprost z dawnego `.issues/AGENTS.md` (obowiązywała już przy triage'u
plikowym, obowiązuje dalej przy triage'u do Linear): **nie kopiuj bezmyślnie** severity
CodeRabbit (Major/Minor/Nit) na priorytet Linear. Oceń realne ryzyko **w tym repo** —
czy dotyczy zamkniętego, zaliczonego zadania kontra żywej infrastruktury używanej co
sesję — i zapisz TO uzasadnienie w `## Uzasadnienie priorytetu` opisu issue.

Mapowanie nie jest 1:1: `Major` CodeRabbit na kodzie zamrożonego, zaliczonego epizodu
(`learning-mode`) może wylądować jako Niski/Odłożone; `Nit` dotykający realnego sekretu
lub podwójnej submisji hubu (r13) może wylądować jako Wysoki.

## Jak zgłaszać
Egzekwowane przez rutynę `review-ingest` przy tworzeniu ticketów z recenzji CodeRabbit —
nie jest to reguła zgłaszalna sama w sobie, tylko polityka mapowania stosowana przy
każdym `issueCreate`.
