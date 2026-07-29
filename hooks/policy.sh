#!/usr/bin/env bash
# Injected into every prompt so the main model consistently applies the
# delegation criteria (description-only auto-delegation is flaky mid-session).
cat <<'EOF'
GRUNT DELEGATION POLICY: if the user's request is grunt work — mechanical,
well-specified, needs no design judgment and no deep conversation context
(commits, PR descriptions, log fetching, ticket updates, formatting, renames,
boilerplate, and anything matching those criteria) — delegate it to the
`grunt` agent with a 1-3 line task description instead of doing it yourself.
grunt gathers its own context. Never delegate work needing judgment or
session context.
EOF
