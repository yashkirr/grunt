<p align="center">
  <img src="https://em-content.zobj.net/source/apple/391/ox_1f402.png" width="120" />
</p>

<h1 align="center">grunt</h1>

<p align="center">
  <strong>Your expensive model thinks. A cheap one does the grunt work.</strong>
</p>

<p align="center">
  <a href="#before--after">Before/After</a> •
  <a href="#install">Install</a> •
  <a href="#what-counts-as-grunt-work">What gets delegated</a> •
  <a href="#configuration">Config</a> •
  <a href="#benchmarks">Benchmarks</a> •
  <a href="#evals">Evals</a> •
  <a href="#contributing">Contributing</a>
</p>

---

A [Claude Code](https://code.claude.com/docs) plugin that teaches your main model to route mechanical work — commits, PR descriptions, log fetching, ticket updates — to a cheaper subagent (Haiku by default), while your expensive model (Fable/Opus/Sonnet) keeps its context and your usage limit for actual thinking. Measured on real sessions: **43% less expensive-model input per chore** and **12/12 chores routed correctly with 0/9 false positives**.

Two things drain a high-end model session: usage limits deplete faster on expensive models, and every bulky tool output (a 300-line diff, a log dump) that enters the main context gets re-sent on every later turn. Routine chores cause both and need zero high-end reasoning. Don't pay thinking prices for typing.

## Before / After

<table>
<tr>
<td width="50%">

### Without grunt

> **you:** commit this
>
> **fable:** *runs `git status`, reads the entire
> 300-line diff into its own context, writes
> the message, commits*
>
> 166k expensive-model input tokens in the
> benchmark session (including shared session
> bootstrap context). The diff stays in context
> and is re-billed every turn afterwards.

</td>
<td width="50%">

### With grunt

> **you:** commit this
>
> **fable:** *one line to the grunt agent*
>
> **grunt (haiku):** *reads the diff itself,
> matches your commit style, commits, reports
> back one line*
>
> 95k expensive-model input tokens, mostly that
> same fixed bootstrap context. The diff never
> touches your expensive context. Haiku's share:
> about $0.04.

</td>
</tr>
</table>

**Same chore completed. The smart model never reads the diff.**

## Install

```
/plugin marketplace add yashkirr/grunt
/plugin install grunt@grunt
```

Or try it for one session without installing:

```
claude --plugin-dir /path/to/grunt
```

Requirements: Claude Code with plugin support (tested on v2.x, macOS), bash,
and access to the executor model (Haiku by default) through your Claude
account or provider.

## What counts as grunt work

Criteria, not a fixed task list. A request is delegated when it is:

1. **Well-specified** — success is obvious, no design decisions;
2. **Mechanical** — known commands and formats, not reasoning;
3. **Context-independent** — a fresh agent can gather everything it needs
   itself (git, CLIs, files);
4. **Heavy enough to matter** — likely to pull meaningful tool output or
   several tool calls into the main context. Trivial one-liners (`git
   status`, a single rename) aren't worth the delegation round trip.

Commits, PR descriptions, log fetching and filtering, ticket updates,
formatters, renames, boilerplate, changelog entries — and anything else
matching the criteria, whatever your workflow looks like.

The useful distinction is *discoverable* context vs *conversational* context.
A fresh agent can rediscover the diff, the branch, your commit conventions,
or a log file on its own — those tasks delegate well. Only your main session
knows why a design was chosen, which wording you agreed on, or what "the fix
we discussed" refers to — those stay put, along with debugging, design, and
refactoring. The policy is injected on every prompt via a hook, so routing
stays consistent deep into long sessions.

## Configuration

- **Main model** — untouched. grunt works under any session model; set it
  with `/model` as usual.
- **Executor model** — `haiku` by default. Override with the `GRUNT_MODEL`
  env var (any model alias or full ID):

  ```json
  // ~/.claude/settings.json
  { "env": { "GRUNT_MODEL": "sonnet" } }
  ```

  or per session: `GRUNT_MODEL=sonnet claude`.

  How it resolves: the policy hook tells the main model to pass your
  configured model on the Agent call, which overrides the agent file's
  `model: haiku` — that frontmatter value is the safety net if the parameter
  is ever omitted, so a mis-routed chore falls back to cheap, never to
  expensive. Verified end-to-end in the eval transcripts. One caveat: a
  `CLAUDE_CODE_SUBAGENT_MODEL` env var force-overrides every subagent's
  model and sits above all other config — unset it if you use `GRUNT_MODEL`.

## Benchmarks

4 chore tasks (commit, PR description, log filtering, changelog) × 2 arms ×
3 trials, plus 3 non-chore probes × 3 trials: **33 real headless `claude -p`
sessions** on `claude-fable-5`, run in parallel. Per-model token counts are
parsed from the session transcripts; dollar figures use API list prices as a
proxy for limit burn.

| Metric (median, all chores) | Baseline | With grunt |
|---|---:|---:|
| Expensive-model input tokens per chore | 166,204 | 95,223 (**-43%**) |
| Expensive-model cost per chore | $0.548 | $0.397 (**-28%**) |
| Total cost, all models | $0.810 | $0.654 (**-19%**) |

**Routing: 12/12 chores delegated, 0/9 non-chore probes falsely delegated,
33/33 tasks completed.** (Completed means the commit landed or the file was
written — correctness is measured separately below.)

- Savings scale with how much bulky context the chore drags in: changelog
  (write + stage + commit) saved the most, a short PR description the
  least. Fixed session bootstrap cost is paid in both arms and floors the
  delta on small tasks.
- Numbers are per single chore in a fresh session; in a long working
  session the clean-context effect compounds on every subsequent turn.

**The quality tradeoff, measured honestly:** a blind pairwise judge (fable,
arm order anonymized) preferred the baseline's artifacts 8/12 with 4 ties —
haiku's messages are complete but less precise (an occasional miscount, an
omitted diff detail). A verification-focused prompt revision did not move
that score. On objective ground-truth checks both arms are near-perfect:
log ERROR counts 100% correct in both arms, Conventional Commits subjects
9/9 baseline vs 8/9 grunt. Chores get done correctly; the prose is a notch
less polished. If that notch matters, set `GRUNT_MODEL=sonnet` (a measured
comparison of Sonnet as executor is queued — see the roadmap). Full
verdicts: [evals/quality.md](evals/quality.md).

Per-task tables: [evals/benchmark.md](evals/benchmark.md). Raw snapshot:
[evals/snapshots/results.json](evals/snapshots/results.json).

## Evals

Reproduce everything yourself — the harness runs real sessions and reads the
transcripts, no synthetic estimates:

```bash
evals/bench.sh 3                 # full suite, N=3 per cell, parallel, retries transient API errors
tail -f evals/work/live.log      # watch every trial live
python3 evals/judge.py           # blind pairwise quality judging
```

- `evals/tasks.json` — the fixed task suite; add your own chores and probes.
- `evals/snapshots/results.json` — committed raw numbers; stats re-render via
  `python3 evals/bench_measure.py report ...` without re-running anything.
- Quality layer: a blind judge compares baseline-vs-grunt artifacts per trial
  (anonymized order), plus objective ground-truth checks where they exist
  (the log fixture's ERROR counts are deterministic; commit subjects are
  regex-checked against Conventional Commits).

**What this does not measure:** latency (delegation adds a subagent round
trip); behavior on messy real-world repositories (fixtures are small and
clean); judge preferences are model-relative (a Fable judge may share family
style preferences); cross-model behavior beyond the snapshot's model; exact
subscription-limit weighting (Anthropic-internal — API prices are a proxy).

## Safety

The executor has shell access, so its prompt carries explicit operational
boundaries: it never pushes, publishes, deploys, merges, force-updates, or
deletes remote state unless the delegated request explicitly asks for
exactly that; destructive or irreversible commands escalate back to the main
model instead of guessing. Cautious users can further restrict the agent via
Claude Code's standard per-tool permission settings.

## Limitations

- Routing is judged by the main model against an injected policy — measured
  at 12/12 on the benchmark suite, but it is model behavior, not a
  deterministic router. Say "use the grunt agent" to force it.
- The subagent has no conversation context by design. Chores that genuinely
  need session context stay on the main model — that's the policy working,
  not a bug.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — new benchmark tasks, messy-repo
fixtures, and routing boundary cases are the most useful contributions.

## License

[MIT](LICENSE)
