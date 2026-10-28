# closure_drift for AI agents

An agent that bumps a version, tags and publishes can reuse a version label for different code. closure_drift checks that before the tag. It is read-only and needs only Python and git.

One call returns a short verdict, so the agent does not have to read `git log` and diffs into its context to find out.

## 1. As an MCP tool

With [uv](https://docs.astral.sh/uv/), nothing to clone. One line, in the client you use:

```bash
claude mcp add closure-drift -- uvx --from git+https://github.com/luizfnsilva/closure_drift closure-drift-mcp   # Claude Code
codex mcp add closure-drift -- uvx --from git+https://github.com/luizfnsilva/closure_drift closure-drift-mcp    # OpenAI Codex CLI
gemini mcp add closure-drift uvx --from git+https://github.com/luizfnsilva/closure_drift closure-drift-mcp      # Gemini CLI
```

Cursor (`.cursor/mcp.json`), Windsurf (`~/.codeium/windsurf/mcp_config.json`), Claude Desktop and
other clients that read `mcpServers`:

```json
{"mcpServers": {"closure-drift": {"command": "uvx",
  "args": ["--from", "git+https://github.com/luizfnsilva/closure_drift", "closure-drift-mcp"]}}}
```

VS Code with Copilot (`.vscode/mcp.json`):

```json
{"servers": {"closure-drift": {"type": "stdio", "command": "uvx",
  "args": ["--from", "git+https://github.com/luizfnsilva/closure_drift", "closure-drift-mcp"]}}}
```

Or the container, in any client: `docker run -i --rm ghcr.io/luizfnsilva/closure_drift:1.2.2`.

Pin a version with `closure_drift@v1.2.2`. Without uv: clone the repository and run
`python3 /path/to/closure_drift/closure_drift_mcp.py`.

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

## 2. As a skill

[`skills/closure-drift/SKILL.md`](skills/closure-drift/SKILL.md), in the Agent Skills format: when to
run the check, the command, what each answer means, and what never to do (move a published tag,
take exit 2 as a pass). Copy the `closure-drift` folder into your agent's skills folder (for
Claude Code, `~/.claude/skills/` or `.claude/skills/` in the project). Its description is loaded
always; the rest only when the agent is about to tag or release.

## 3. As a rule in the agent's instructions

For agents without skills, the short version. Paste into `AGENTS.md`, `CLAUDE.md`, `.cursorrules` or `.github/copilot-instructions.md`:

```markdown
## Releases
Before creating a version tag or publishing a package:
1. Run `python3 closure_drift.py --would-tag --json .` (or the MCP tool `would_tag`).
2. If the verdict is `would_drift`, do not tag: the version label already names other code. Tell the person and ask which version to use; only then change the version file, commit, and run step 1 again.
3. If the exit code is 2, do not tag and do not guess: show the reason to the person who asked.
4. After tagging, run `python3 closure_drift.py --json .`. Exit 1 means a label names two code states; report the paths from `--explain LABEL`.
```

## 4. In CI

The same check gates a pipeline whoever wrote the commit, person or agent: [docs/CI.md](../docs/CI.md).

## What it does not do

It reads git, not the registry: it cannot see which commit a package was built from (`docs/FAILURES.md`, O10). It does not fix anything; the agent or the person does.
