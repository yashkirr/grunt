# grunt A/B results

Arm A = baseline (fable does the chore). Arm B = grunt plugin (fable delegates to haiku). Trials measured: A=5, B=5

Delegation success (arm B): 5/5 trials spawned a cheap-model subagent.

| Metric (median) | Arm A baseline | Arm B grunt |
|---|---:|---:|
| Fable input tokens, chore turn (in+cw+cr) | 169,090 | 61,085 |
| Fable output tokens, chore turn | 788 | 1,016 |
| Haiku tokens, subagent (in+cw+cr+out) | 0 | 27,649 |
| Fable input tokens, follow-up turn (in+cw+cr) | 38,288 | 31,546 |
| Fable cost, chore turn ($, API-price proxy) | 0.5370 | 0.3489 |
| Fable cost, follow-up turn ($) | 0.2800 | 0.1996 |
| Total cost, all models ($) | 0.8132 | 0.5688 |

Per-trial fable chore-turn cost ($):

- Arm A: 0.5121, 0.5698, 0.5370, 0.5111, 0.5632
- Arm B: 0.3772, 0.3489, 0.3405, 0.3537, 0.3473
