# grunt benchmark

Model claude-fable-5, generated 2026-07-29T14:43:41Z. Arm A = no plugin, arm B = grunt. Values: median ±stdev across trials.

## Per-task results

| Task | Metric | Arm A | Arm B |
|---|---|---:|---:|
| changelog | expensive-model input tokens, task turn | 213,823 ±21,674 | 96,444 ±20,414 |
| changelog | cheap-model tokens (subagent) | 0.0000 ±0.0000 | 84,292 ±14,439 |
| changelog | expensive-model input tokens, follow-up | 39,254 ±146 | 35,691 ±2,395 |
| changelog | total cost, all models ($) | 0.9437 ±0.0242 | 0.7122 ±0.0812 |
| commit | expensive-model input tokens, task turn | 172,269 ±958 | 62,505 ±186 |
| commit | cheap-model tokens (subagent) | 0.0000 ±0.0000 | 38,133 ±6,044 |
| commit | expensive-model input tokens, follow-up | 38,732 ±101 | 64,648 ±18,706 |
| commit | total cost, all models ($) | 0.8515 ±0.0022 | 0.6439 ±0.0263 |
| log-filter | expensive-model input tokens, task turn | 128,465 ±19,676 | 95,406 ±19,742 |
| log-filter | cheap-model tokens (subagent) | 0.0000 ±0.0000 | 56,011 ±29,002 |
| log-filter | expensive-model input tokens, follow-up | 34,871 ±376 | 35,221 ±69 |
| log-filter | total cost, all models ($) | 0.6994 ±0.0433 | 0.6716 ±0.0467 |
| pr-desc | expensive-model input tokens, task turn | 99,040 ±265 | 95,288 ±95 |
| pr-desc | cheap-model tokens (subagent) | 0.0000 ±0.0000 | 39,287 ±6,829 |
| pr-desc | expensive-model input tokens, follow-up | 37,101 ±55 | 35,173 ±45 |
| pr-desc | total cost, all models ($) | 0.6934 ±0.0036 | 0.6534 ±0.0038 |

## Scoreboard (all chore trials pooled)

| Metric (median) | Arm A | Arm B | Delta |
|---|---:|---:|---:|
| Expensive-model input tokens per chore | 166,204 | 95,223 | -43% |
| Expensive-model cost per chore ($) | 0.5483 | 0.3974 | -28% |
| Follow-up input tokens | 37,850 | 35,209 | -7% |
| Total cost per chore ($) | 0.8100 | 0.6544 | -19% |

## Delegation accuracy

- Chores delegated (arm B): **12/12**
- Probes falsely delegated: **0/9**
- Task success (all trials): **33/33**

## What this does NOT measure

- Output fidelity: whether the cheap model's commit message / summary is as *good* — only that the task completed.
- Latency: delegation adds a subagent round trip.
- Cross-model behavior: only the snapshot's main model is measured.
- Subscription-limit weighting: dollar figures use API list prices as a proxy.
