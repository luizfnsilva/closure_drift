# Usability: a protocol for people who have never seen the tool

Registered 2026-10-29 (`tests/PREREGISTRATION.md` §24), **not yet run**. Its purpose is to find
out whether the output is read correctly without help, before adding anything to the tool.

## Who

People who write software and have not used closure_drift. Five is enough to find the first
problems. Nobody who has read this repository's documentation beforehand.

## Three tasks, timed separately

1. **Install and run.** Given only the repository URL: measure a small repository we provide.
2. **Read a drift.** Given only the terminal output of a `drift` (no documentation): what does it
   mean, and what would you do next?
3. **Handle an incomplete answer.** Given only the output of an `incomplete` (exit 2): is this a
   pass? What would you do next?

The repositories and outputs are made by `examples/demo.py` and the battery's helpers, so anyone
can rebuild them.

## Four numbers per task

| number | how |
|---|---|
| time to finish | from the task's start to the person's answer |
| finished without help | yes / no |
| misreadings | answers that contradict the verdict (above all: calling exit 2 a pass) |
| documentation looked up | which file, if any |

Install and first use are reported apart: an easy install does not mean the result is understood.

## What may be claimed

Only the numbers, per task, with the number of people. A misreading found once is reported, and
the output is changed before anything is added to the tool.
