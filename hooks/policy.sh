#!/usr/bin/env bash
# Injected into every prompt so the main model consistently applies the
# delegation criteria (description-only auto-delegation is flaky mid-session).
cat <<'EOF'
GRUNT DELEGATION POLICY: if the user's request is grunt work — mechanical,
well-specified, needs no design judgment and no deep conversation context
(commits, PR descriptions, log fetching, ticket updates, formatting, renames,
boilerplate, and anything matching those criteria) — delegate it to the
`grunt` agent with a 1-3 line task description instead of doing it yourself.
The test is whether doing it yourself would pull tool output (diffs, logs,
file contents) into your context — committing ALWAYS qualifies because it
means reading the diff. grunt gathers its own context. Do it yourself only
when the chore is a single command whose output you don't need to read, when
it needs judgment, or when it refers to the conversation ("the fix we
discussed") rather than state grunt can rediscover on its own.
EOF
# Executor model rides the Agent call's model param, which overrides the
# agent file's `model: haiku` fallback. Override the default with GRUNT_MODEL.
printf 'ALWAYS pass model: "%s" when invoking the grunt agent (never invoke it without the model param).\n' "${GRUNT_MODEL:-haiku}"
