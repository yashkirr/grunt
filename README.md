# grunt

Delegate grunt work to a cheap model. Keep your expensive model's usage limit
— and its context — for work that needs it.

## Why

Two things drain a high-end model (Opus/Fable) session:

1. **Model-weighted limits.** Usage limits deplete per model cost — the same
   tokens burn far more of your limit on a high-end model than on Haiku.
2. **Context pollution.** Every bulky tool output (a 200-line diff, an AWS log
   dump) that enters the main session's context is re-sent on *every
   subsequent turn* until the session ends.

Routine chores — commits, PR descriptions, log fetches, ticket updates — cause
both, and need zero high-end reasoning.

**grunt** adds a Haiku-pinned subagent plus a per-prompt delegation policy.
Your main model spends ~100 tokens describing the chore and ~150 reading the
result; the grunt work (running git/aws/jira, reading their bulky output)
happens in the subagent's own throwaway context at cheap-model rates.

## What counts as grunt work

Criteria, not a fixed task list. A task is delegated when it is:

1. **Well-specified** — success is obvious, no design decisions;
2. **Mechanical** — known commands/formats, not reasoning;
3. **Context-independent** — a fresh agent can gather everything it needs
   itself (git, CLIs, files).

Commits, PR/MR descriptions, log fetch+filter, ticket CRUD, formatters,
renames, boilerplate, changelog updates — and anything else matching the
criteria, whatever your workflow. Debugging, design, refactoring, and
"the thing we just discussed" stay on your main model.

## Install

Local (this repo):

```
/plugin marketplace add /path/to/grunt
/plugin install grunt@grunt
```

Or per-session, no install:

```
claude --plugin-dir /path/to/grunt
```

## Configuration

- **Main model** — untouched. grunt works under any session model (Fable,
  Opus, Sonnet); set it with `/model` as usual.
- **Grunt executor model** — `haiku` by default. Override with the
  `GRUNT_MODEL` env var (any model alias or full ID), e.g. run chores on
  Sonnet instead:

  ```json
  // ~/.claude/settings.json
  { "env": { "GRUNT_MODEL": "sonnet" } }
  ```

  or per session: `GRUNT_MODEL=sonnet claude`. The point stays the same:
  route mechanical work to a model cheaper than the one you're thinking with.

  Note: a `CLAUDE_CODE_SUBAGENT_MODEL` env var force-overrides the model of
  *every* subagent (grunt included) and sits above all other config — unset
  it if you want `GRUNT_MODEL` (or any per-agent model) to work.

## Does it actually save tokens?

Yes — measured, not vibes. Benchmark suite: 4 chore tasks (commit, PR
description, log filtering, changelog) × 2 arms × 3 trials + 3 non-chore
probes × 3 trials = 33 real headless `claude -p` sessions on
`claude-fable-5`, run in parallel. Per-model token counts parsed from the
session transcripts; dollar figures use API list prices as a proxy for
limit burn. Raw numbers snapshot: [evals/snapshots/results.json](evals/snapshots/results.json).

| Metric (median, all chores) | Baseline | With grunt |
|---|---:|---:|
| Expensive-model input tokens per chore | 166,204 | 95,223 (**-43%**) |
| Expensive-model cost per chore | $0.548 | $0.397 (**-28%**) |
| Total cost, all models | $0.810 | $0.654 (**-19%**) |

**Delegation accuracy: 12/12 chores delegated, 0/9 non-chore probes falsely
delegated, 33/33 tasks completed successfully.** The criteria-based policy
routes correctly in both directions.

- Savings scale with how much bulky context the chore drags in: changelog
  (write + stage + commit) saved the most (-$0.23/task), a short PR
  description the least. Fixed session boot overhead is paid in both arms
  and floors the delta on small tasks.
- Numbers are per single chore in a fresh session; in a long working
  session the clean-context effect compounds every subsequent turn.

Per-task tables + honest "what this does NOT measure":
[evals/benchmark.md](evals/benchmark.md). Reproduce: `evals/bench.sh 3`
(watch live: `tail -f evals/work/live.log`; earlier single-task experiment:
`evals/run_experiment.sh`, results in [evals/results.md](evals/results.md)).

## Limitations

- Delegation is judged by the main model against the policy — it is reliable,
  not guaranteed. Say "use the grunt agent" to force it.
- The subagent has no conversation context by design. Chores that genuinely
  need session context stay on the main model — that's the policy working,
  not a bug.
