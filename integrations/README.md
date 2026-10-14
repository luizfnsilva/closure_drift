# closure_drift for AI agents

An agent that bumps a version, tags and publishes can reuse a version label for different code. closure_drift checks that before the tag. It is read-only and needs only Python and git.

One call returns a short verdict, so the agent does not have to read `git log` and diffs into its context to find out.

## 1. As an MCP tool

```bash
git clone https://github.com/luizfnsilva/closure_drift
```

Claude Code:

```bash
claude mcp add closure-drift -- python3 /path/to/closure_drift/integrations/mcp/closure_drift_mcp.py
```

Claude Desktop, Cursor and other MCP clients (`mcpServers` in their config file):

```json
{"mcpServers": {"closure-drift": {"command": "python3",
  "args": ["/path/to/closure_drift/integrations/mcp/closure_drift_mcp.py"]}}}
```

Tools: `would_tag` (run before tagging), `check_versions`, `explain_label`, `compare`. Each returns the JSON report and the exit code: 0 clean, 1 drift, 2 not decided, with the reason.

### What the agent sees

A repository whose `pyproject.toml` still says `1.0`, tagged `v1.0` earlier, with new code at HEAD:

```text
agent  → tools/call {"name": "would_tag", "arguments": {"repo": "."}}
server ← {"content": [{"type": "text", "text": "{\"exit\": 1, \"meaning\": \"drift: a label names more
          than one code state\", \"output\": {\"verdict\": \"would_drift\", \"label_at_head\": \"1.0\", ...}}"}],
          "isError": false}
agent: version 1.0 already names other code; I will bump the version before tagging.
```

The exit code of the check travels inside the text, with its meaning; `isError` is `false` because a drift is an answer, not a failure of the tool.

The server makes the check available. It does not stop anything: the agent has to call it and respect the answer. For a barrier, use CI (section 3).

## 2. As a rule in the agent's instructions

Paste into `AGENTS.md`, `CLAUDE.md`, `.cursorrules` or `.github/copilot-instructions.md`:

```markdown
## Releases
Before creating a version tag or publishing a package:
1. Run `python3 closure_drift.py --would-tag --json .` (or the MCP tool `would_tag`).
2. If the verdict is `would_drift`, do not tag: the version label already names other code. Bump the version in the file that declares it, commit, and run step 1 again.
3. If the exit code is 2, do not tag and do not guess: show the reason to the person who asked.
4. After tagging, run `python3 closure_drift.py --json .`. Exit 1 means a label names two code states; report the paths from `--explain LABEL`.
```

## 3. In CI

The same check gates a pipeline whoever wrote the commit, person or agent: [docs/CI.md](../docs/CI.md).

## What it does not do

It reads git, not the registry: it cannot see which commit a package was built from (`docs/FAILURES.md`, O10). It does not fix anything; the agent or the person does.
