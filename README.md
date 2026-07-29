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

## Does it actually save tokens?

Yes — measured, not vibes. See [evals/results.md](evals/results.md).
Reproduce with `evals/run_experiment.sh` (runs real headless A/B sessions and
parses the session transcripts for exact per-model token usage).

<!-- results table inserted after experiment run -->

## Limitations

- Delegation is judged by the main model against the policy — it is reliable,
  not guaranteed. Say "use the grunt agent" to force it.
- The subagent has no conversation context by design. Chores that genuinely
  need session context stay on the main model — that's the policy working,
  not a bug.
