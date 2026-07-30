# Contributing

Contributions welcome — especially new benchmark tasks, messy-repository
fixtures, and routing boundary cases.

## Setup

No build step. The plugin is four files; the evals are bash + Python 3 stdlib.

```bash
git clone https://github.com/yashkirr/grunt
claude --plugin-dir /path/to/grunt        # try your changes in one session
```

## Testing changes

Anything that touches the agent prompt (`agents/grunt.md`) or the policy hook
(`hooks/policy.sh`) changes routing or output quality — back it with numbers:

```bash
evals/bench.sh 3                # full A/B suite (real sessions, costs money)
tail -f evals/work/live.log     # watch it run
python3 evals/judge.py          # blind quality judging vs baseline artifacts
```

Commit the regenerated `evals/snapshots/results.json` and `evals/benchmark.md`
with your change so the numbers are reviewable as a diff. The README's
benchmark numbers are generated from the snapshot — `bench.sh` re-syncs them
automatically; after editing `evals/quality.md` by hand or via `judge.py`,
run `python3 evals/readme_sync.py` (CI-style drift check: `--check`).

Adding a task or probe: append to `evals/tasks.json` (probes are prompts that
should NOT be delegated) and add a fixture mode to `evals/gen_fixture.py` if
needed.

## Pull requests

- Keep it small; this project's appeal is that it has almost no machinery.
- State what you measured, or say plainly that a change is unmeasured.
- No new dependencies without a strong case — evals are stdlib-only on purpose.
