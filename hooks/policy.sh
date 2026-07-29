#!/usr/bin/env bash
# Injected into every prompt so the main model consistently applies the
# delegation criteria (description-only auto-delegation is flaky mid-session).
cat <<'EOF'
GRUNT DELEGATION POLICY: if the user's request is grunt work — mechanical,
well-specified, needs no design judgment and no deep conversation context
(commits, PR descriptions, log fetching, ticket updates, formatting, renames,
boilerplate, and anything matching those criteria) — AND the work would pull
meaningful tool output or several tool calls into your context, delegate it
to the `grunt` agent with a 1-3 line task description instead of doing it
yourself. grunt gathers its own context. Do it yourself when the task is a
trivial one-liner, needs judgment, or refers to the conversation ("the fix
we discussed") rather than to state grunt can rediscover on its own.
EOF
# Executor model rides the Agent call's model param, which overrides the
# agent file's `model: haiku` fallback. Override the default with GRUNT_MODEL.
printf 'ALWAYS pass model: "%s" when invoking the grunt agent (never invoke it without the model param).\n' "${GRUNT_MODEL:-haiku}"
