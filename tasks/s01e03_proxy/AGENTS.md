# s01e03_proxy Module

## Purpose
Proxy server for the s01e03 "Operator Wojtek" scenario — a live FastAPI endpoint
the grading bot talks to over a public tunnel (ngrok), not a batch fetch→solve→submit
task. See `tasks/AGENTS.md`'s live-server exception for why `solve()` refuses instead
of running.

## Ownership
- `server.py`: FastAPI app (`ServerFactory`), `POST /chat {sessionID, msg}`, per-session
  history, model selection.
- `tools.py`: `check_package`/`redirect_package` tool definitions + executor calling the
  real `hub.ag3nts.org/api/packages` API through `HubClient`.
- `prompts.py`: system prompt for the agent — deliberately says nothing about the
  Żarnowiec redirect override (see `packages_data`-equivalent logic in `tools.py`'s
  executor for why that lives in code, not the prompt).
- `solution.py`: registers the task in `TASK_REGISTRY` (`hub_name="proxy"`, not
  `"s01e03"`) and `register_with_hub()` to submit the public URL; `solve()` raises.

## Local Contracts
- `solve()` MUST raise `RuntimeError` with run instructions — never silently submit
  an empty/placeholder answer to the hub.
- Env vars: `S01E03_MODEL` (default: `ANTHROPIC_MODELS["fast"]`), `S01E03_PORT`
  (default `8003`).
- `/chat` MUST stay a sync (non-`async def`) handler — `run_agent_loop()` is
  blocking, and FastAPI's automatic threadpool offload for sync endpoints keeps
  `/health` and concurrent requests responsive.
- Per-session history is bounded (`_MAX_SESSIONS`, `_MAX_MESSAGES_PER_SESSION` in
  `server.py`) — this endpoint is publicly reachable, unbounded state is a DoS risk.

## Work Guidance
- Run locally: `uv run python -m tasks.s01e03_proxy.server`.
- Expose publicly: `./deploy/ngrok_tunnel.sh <port>`, then `register_with_hub()`
  with the printed `https://*.ngrok-free.app` URL (see `solution.py` docstring for
  the exact one-liner).
- Flag arrives inline in a `/chat` message body from Wojtek, not via a separate
  endpoint — the server logs prominently when the `{FLG:...}` pattern appears.

## Verification
- `uv run pytest tasks/s01e03_proxy/` — endpoint, tool-executor, and safety-net
  logic, all with the LLM/hub calls mocked.
- The real verification is a live grading run against the hub bot through the
  running server — tests only prove the local logic, not the live conversation.

## Child DOX Index
- None.
