# Skill Activation — aid4u
#
# TARGET: strategy/skills/skill-activation.md
# SCOPE: Trigger rules, decision trees, conflict resolution, observability chain.
# NOT IN THIS FILE:
#   - Task pipeline → strategy/tasks/workflow.md
#   - LLM model selection → strategy/llm-selection.md
#   - ADHD rescue patterns → strategy/tasks/adhd-workflow.md
#   - Task decomposition format → strategy/tasks/task-decomposition.md

---

## Installed Skills — Complete Roster

| Layer | Skill | Triggers on |
|---|---|---|
| ADHD | `adhd-daily-planner` | session start, daily rhythm, energy check |
| ADHD | `project-management-guru-adhd` | blocked >15 min, overwhelmed, hyperfocus |
| ADHD | `neurodivergent-visual-org` | visual map, decision tree, freeze state |
| TaskWarrior | `001-jeremy` | **every** task add / start / done / depends |
| Planning | `writing-plans` | new task, plan, decompose, "how to approach" |
| Dev | `test-driven-development` | write test, TDD, new feature, failing test |
| Dev | `systematic-debugging` | bug, root cause, error after 2+ attempts |
| Dev | `verification-before-completion` | done, finished, ready to submit |
| Observability | `langfuse-observability` | trace, instrument, span, token usage |
| Eval | `promptfoo-evals` | wrong output, prompt issue, eval, re-test |
| API | `api-testing` | REST, HTTP, hub.ag3nts.org, request/response |
| Context | `context-fundamentals` | context window, attention, lost-in-middle |
| Context | `context-optimization` | KV-cache, masking, budget, compaction |
| Context | `memory-systems` | RAG, vector store, NotebookLM, retrieval |
| Context | `multi-agent-patterns` | orchestrator, subagent, swarm, parallel |
| Retro | `agent-retro` | end of session, retrospective (**CC only**) |
| Custom | `aid4u-learning-mode` | lesson done, make notes, Feynman **[TO BUILD]** |
| Custom | `aid4u-neurowarrior-progress` | /progress, score, how many tasks **[TO BUILD]** |

---

## Trigger Matrix

| Situation | Use | Do NOT use |
|---|---|---|
| Starting new AID4U task | `writing-plans` first | coding directly |
| Writing tests | `test-driven-development` | raw pytest without skill |
| Test FAILS, code suspected | `systematic-debugging` | `promptfoo-evals` |
| Test PASSES, output wrong | **`promptfoo-evals`** | `systematic-debugging` |
| About to say "done" | `verification-before-completion` | skipping gate |
| Agent trace available (Langfuse) | `langfuse-observability` → `promptfoo-evals` | re-running blindly |
| Context usage >60% | `context-optimization` | clearing context manually |
| NotebookLM retrieval needed | `memory-systems` | guessing from stale context |
| Overwhelmed, can't start | `adhd-daily-planner` → `task focus` | opening task list |
| Blocked >15 min same issue | `project-management-guru-adhd` | pushing through |
| Lesson completed | `aid4u-learning-mode` | skipping notes |
| End of CC session | `agent-retro` (CC only) | — |

---

## ⚡ Critical Decision: Code Bug vs Prompt Bug

```
Test PASSES but agent returns wrong output?
  YES → LLM/prompt issue  → promptfoo-evals
  NO  → code logic issue  → systematic-debugging
```

Additional signal: `langfuse-observability` trace shows correct tool calls
but wrong final answer → prompt issue → `promptfoo-evals`.

Never diagnose both simultaneously. Pick one, fix it, re-test.

---

## Observability Chain

```
1. Instrument     langfuse-observability  → add trace before running agent
2. Identify span  Langfuse dashboard      → find anomalous span/token usage
3. Prompt path    promptfoo-evals         → write eval config, score, re-test
4. Code path      systematic-debugging    → Root Cause → Hypothesis → Fix
5. Confirm fix    verification-before-completion → re-run eval/test
```

---

## Context Engineering Triggers

| Signal | Skill |
|---|---|
| Agent losing track of earlier decisions | `context-fundamentals` (U-shaped attention) |
| Context >60% used, session continuing | `context-optimization` |
| NotebookLM / RAG retrieval needed | `memory-systems` |
| Designing multi-agent task structure | `multi-agent-patterns` |

---

## Conflict Resolution

| Conflict | Winner | Rule |
|---|---|---|
| `001-jeremy` vs `productivity:task-management` | `001-jeremy` | TW is single source of truth |
| `memory-systems` vs `productivity:memory-management` | `memory-systems` | for agent/RAG state; productivity for personal notes |
| `systematic-debugging` vs `engineering:debug` | `systematic-debugging` | superpowers enforces root cause first |
| `test-driven-development` vs `engineering:testing-strategy` | `test-driven-development` | superpowers deletes premature code |
| `agent-retro` vs `adhd-daily-planner` (evening) | **both, in sequence** | retro → feeds planner's evening ritual |
| `verification-before-completion` vs `test-driven-development` | **both, in sequence** | TDD = write tests; VBC = gate before done claim |
| `context-optimization` vs baseline `context-compression` | `context-optimization` | baseline removed; muratcankoylan is superset |
