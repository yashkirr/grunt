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

Yes — measured, not vibes. N=5 trials per arm, real headless `claude -p`
sessions on `claude-fable-5`, committing an identical ~300-line staged change,
then one follow-up question. Token counts parsed from the session transcripts;
dollar figures use API list prices as a proxy for limit burn.

| Metric (median) | Baseline (fable does it) | With grunt (haiku does it) |
|---|---:|---:|
| Fable input tokens, chore turn | 169,090 | 61,085 (**-64%**) |
| Haiku tokens, subagent | 0 | 27,649 (~$0.03) |
| Fable input tokens, follow-up turn | 38,288 | 31,546 (-18%) |
| Fable cost, chore turn | $0.537 | $0.349 (**-35%**) |
| Total cost, all models | $0.813 | $0.569 (**-30%**) |

- Delegation triggered in **5/5** headless trials; the commit landed every time.
- No overlap between arms: costliest grunt trial ($0.377) beat the cheapest
  baseline trial ($0.511).
- The remaining fable spend is mostly fixed session overhead (system prompt,
  plugins) paid in both arms — the *diff itself* never enters fable's context
  with grunt. Bigger diffs and log dumps widen the gap.
- The follow-up turn is cheaper because fable's context stays clean — that
  saving repeats on every later turn of a real session.

Full numbers: [evals/results.md](evals/results.md). Reproduce:
`evals/run_experiment.sh 5` (watch live with `tail -f evals/work/live.log`).

## Limitations

- Delegation is judged by the main model against the policy — it is reliable,
  not guaranteed. Say "use the grunt agent" to force it.
- The subagent has no conversation context by design. Chores that genuinely
  need session context stay on the main model — that's the policy working,
  not a bug.
