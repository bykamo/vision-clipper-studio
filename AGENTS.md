# AGENTS.md

Guidance for AI agents (Claude, Codex/GPT, Copilot, Hermes, Gemini, ...) working in this repo.

## Using VisionClipper as a tool

To clip videos, do not drive the web UI. Use the Agent Skill:

- Instructions: [`skills/vision-clipper/SKILL.md`](skills/vision-clipper/SKILL.md)
- Helper (JSON output): `python3 skills/vision-clipper/scripts/vclip.py doctor|analyze|render|auto|clips`

For MCP-capable agents (Copilot, Codex CLI, Claude Desktop, Cline), the same
pipeline is exposed as an MCP server instead of a shell helper:

- Server: `backend/mcp_server.py` — start with `.venv/bin/python -m backend.mcp_server` (stdio) or `vision-clipper-mcp`
- Config: [`.vscode/mcp.json`](.vscode/mcp.json) registers it for this workspace
- Docs: [`skills/vision-clipper/references/mcp.md`](skills/vision-clipper/references/mcp.md)

## Developing VisionClipper

- Backend: FastAPI (`backend/main.py`), pipeline worker (`backend/worker.py`). Run tests: `.venv/bin/python -m unittest discover -s backend -p "test_*.py"`
- Frontend: `frontend/` (React 19 + Vite + strict TS). Before committing, run `cd frontend && npm run lint && npm run build`.
- Never commit `.env`, `cookies.txt`, `clips/`, `downloads/`, `temp/`.
