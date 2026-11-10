# VisionClipper MCP server

The MCP server (`backend/mcp_server.py`) exposes the exact same pipeline as
`vclip.py` as MCP tools, so MCP-capable agents (Copilot, Codex CLI,
Claude Desktop, Cline) can clip videos without a shell helper.

## Tools

| Tool | Mirrors `vclip.py` | Description |
|---|---|---|
| `doctor` | `doctor` | Check FFmpeg/ffprobe, venv, LLM endpoint + API key, GROQ key, cookies.txt, frontend build. Never returns secret values. |
| `analyze` | `analyze` | Transcribe + LLM picks viral moments (no rendering). Returns `analysis_id` + `clips[]`. |
| `render` | `render` | Render selected clips from an analysis into 9:16 videos. |
| `auto` | `auto` | Analyze + render everything in one go. |
| `clips` | `clips` | List rendered projects, or clips + metadata of one project. |

Every tool returns a JSON object with an `ok` boolean and, on failure, an
`error` string plus `log_tail` (last 40 log lines). The MCP server runs its
tools synchronously and delegates to `vclip.py` in a subprocess, so the
behaviour, validation and exit codes are identical to the helper script.

## Configuration

### VS Code / Copilot

This repo ships [`.vscode/mcp.json`](../../.vscode/mcp.json), which registers
the server as a workspace MCP server:

```json
{
  "servers": {
    "vision-clipper": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": ["-u", "-m", "backend.mcp_server"],
      "env": {}
    }
  }
}
```

In VS Code the workspace server is picked up automatically. If the server was
installed globally (``pip install 'vision-clipper[mcp]'``), its name is
`vision-clipper` and you can also use the `vision-clipper-mcp` console script
as the `"command"`.

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "vision-clipper": {
      "command": "/absolute/path/to/vision-clipper/.venv/bin/python",
      "args": ["-u", "-m", "backend.mcp_server"]
    }
  }
}
```

### Codex CLI (`config.toml`)

```toml
[mcp_servers.vision-clipper]
command = "/absolute/path/to/vision-clipper/.venv/bin/python"
args = ["-u", "-m", "backend.mcp_server"]
```

## Installation

The MCP SDK is an optional extra so the main install stays lean:

```bash
.venv/bin/pip install -e '.[mcp]'
```

Or install the `mcp` package directly:
`.venv/bin/pip install 'mcp>=1.0.0,<2'` (the server uses the v1 FastMCP API).

## Running

- **stdio** (default, for MCP clients): `.venv/bin/python -m backend.mcp_server`
  or `.venv/bin/vision-clipper-mcp`
- **Streamable HTTP** (debugging / remote clients):
  `.venv/bin/python -m backend.mcp_server --http` → `http://localhost:5055/mcp`

## Notes

- Same "one job at a time" rule as the helper: analysis and rendering are
  CPU/RAM heavy and must not run in parallel.
- Rendering is long-running (roughly 0.5–2× real time per clip); clients
  should use a generous timeout.
- The environment requirements from the main [SKILL.md](../SKILL.md#rules)
  apply unchanged (`.env` with `ROUTER_API_ENDPOINT`, `ROUTER_API_KEY`,
  `GROQ_API_KEY`; FFmpeg on PATH; run `doctor` first).