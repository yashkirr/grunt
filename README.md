<p align="center">
  <img src="https://em-content.zobj.net/source/apple/391/ox_1f402.png" width="120" />
</p>

<h1 align="center">grunt</h1>

<p align="center">
  <strong>expensive model think. cheap model grunt.</strong>
</p>

<p align="center">
  <a href="#before--after">Before/After</a> •
  <a href="#install">Install</a> •
  <a href="#what-counts-as-grunt-work">What gets delegated</a> •
  <a href="#configuration">Config</a> •
  <a href="#benchmarks">Benchmarks</a> •
  <a href="#evals">Evals</a>
</p>

---

A [Claude Code](https://code.claude.com/docs) plugin that auto-delegates grunt work — commits, PR descriptions, log fetching, ticket updates — to a Haiku subagent, while your expensive model (Fable/Opus/Sonnet) keeps thinking. Measured on real sessions: **43% less expensive-model input per chore**, **12/12 chores delegated, 0/9 false positives**, at roughly 1/10th the per-token price for the work itself.

Two things drain a high-end model session: usage limits deplete per model cost, and every bulky tool output (a 300-line diff, a log dump) that enters the main context gets re-sent on **every later turn**. Routine chores cause both and need zero high-end reasoning. So don't pay thinking prices for typing.

## Before / After

<table>
<tr>
<td width="50%">

### 🧠 Without grunt

> **you:** commit this
>
> **fable:** *runs `git status`, reads the entire
> 300-line diff into its own context, writes
> the message, commits*
>
> 166k input tokens on your smartest model.
> The diff stays in context and gets re-billed
> every turn for the rest of the session.

</td>
<td width="50%">

### 🐂 With grunt

> **you:** commit this
>
> **fable:** *one line to the grunt agent*
>
> **grunt (haiku):** *reads the diff itself,
> matches your commit style, commits, reports
> back one line*
>
> 95k fable tokens (mostly fixed session
> overhead). The diff never touches your
> expensive context. Haiku's share: ~$0.04.

</td>
</tr>
</table>

**Same commit. Same quality bar. Smart model never read the diff.**

## Install

Local checkout:

```
/plugin marketplace add /path/to/grunt
/plugin install grunt@grunt
```

Or try it for one session, no install:

```
claude --plugin-dir /path/to/grunt
```

## What counts as grunt work

Criteria, not a fixed task list. A request is delegated when it is:

1. **Well-specified** — success is obvious, no design decisions;
2. **Mechanical** — known commands/formats, not reasoning;
3. **Context-independent** — a fresh agent can gather everything it needs
   itself (git, CLIs, files).

Commits, PR/MR descriptions, log fetch+filter, ticket CRUD, formatters,
renames, boilerplate, changelog updates — and anything else matching the
criteria, whatever your workflow. Debugging, design, refactoring, and "the
thing we just discussed" stay on your main model. The policy is injected
every prompt via a hook, so delegation stays consistent deep into sessions.

## Configuration

- **Main model** — untouched. grunt works under any session model; set it
  with `/model` as usual.
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

## Benchmarks

4 chore tasks (commit, PR description, log filtering, changelog) × 2 arms ×
3 trials + 3 non-chore probes × 3 trials = **33 real headless `claude -p`
sessions** on `claude-fable-5`, run in parallel. Per-model token counts
parsed from the session transcripts; dollar figures use API list prices as
a proxy for limit burn.

| Metric (median, all chores) | Baseline | With grunt |
|---|---:|---:|
| Expensive-model input tokens per chore | 166,204 | 95,223 (**-43%**) |
| Expensive-model cost per chore | $0.548 | $0.397 (**-28%**) |
| Total cost, all models | $0.810 | $0.654 (**-19%**) |

**Delegation accuracy: 12/12 chores delegated, 0/9 non-chore probes falsely
delegated, 33/33 tasks completed.** The criteria route correctly in both
directions.

- Savings scale with how much bulky context the chore drags in: changelog
  (write + stage + commit) saved the most (-$0.23/task), a short PR
  description the least. Fixed session boot overhead is paid in both arms
  and floors the delta on small tasks.
- Numbers are per single chore in a fresh session; in a long working
  session the clean-context effect compounds every subsequent turn.

**The quality tradeoff, measured honestly:** a blind pairwise judge
(fable, arm order anonymized) prefers the baseline's artifacts 8/12 with
4 ties — haiku's commit messages and changelogs are complete but less
precise (an occasional miscount, an omitted diff detail). On objective
ground-truth checks both arms are near-perfect: log ERROR counts 100%
correct in both, Conventional-Commits subjects 9/9 baseline vs 8/9 grunt.
Chores get done correctly; the prose is a notch less polished. If that
notch matters to you, set `GRUNT_MODEL=sonnet` — still ~3× cheaper per
token than Opus-tier. Full verdicts: [evals/quality.md](evals/quality.md).

Per-task tables: [evals/benchmark.md](evals/benchmark.md). Raw snapshot:
[evals/snapshots/results.json](evals/snapshots/results.json).

## Evals

Reproduce everything yourself — the harness runs real sessions and reads
the transcripts, no synthetic estimates:

```bash
evals/bench.sh 3                 # full suite, N=3 per cell, parallel
tail -f evals/work/live.log      # watch every trial live
python3 evals/judge.py           # blind pairwise quality judging
```

- `evals/tasks.json` — the fixed task suite (add your own chores/probes).
- `evals/snapshots/results.json` — committed raw numbers; stats re-render
  with `python3 evals/bench_measure.py report ...` without re-running.
- Quality layer: a blind judge compares baseline-vs-grunt artifacts per
  trial (anonymized order), plus objective ground-truth checks where they
  exist (the log fixture's ERROR counts are deterministic; commit subjects
  are regex-checked against Conventional Commits).

**What this does NOT measure:** latency (delegation adds a subagent round
trip); cross-model behavior beyond the snapshot's model; exact
subscription-limit weighting (Anthropic-internal — API prices are a proxy).

## Limitations

- Delegation is judged by the main model against the policy — reliable
  (12/12 in benchmarks), not guaranteed. Say "use the grunt agent" to force
  it.
- The subagent has no conversation context by design. Chores that genuinely
  need session context stay on the main model — that's the policy working,
  not a bug.
