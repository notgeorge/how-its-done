#!/usr/bin/env bash
# UserPromptSubmit hook — injects the response-format pointer before every reply.
#
# Declarative config in settings.json points here rather than inlining logic in JSON,
# so the rule is reviewable in one place and editable without touching settings.
# The contract itself lives in ~/.claude/skills/response-format/SKILL.md. This text is kept to a
# pointer plus the few steps a session forgets, because an earlier version restated the contract
# here, drifted from it (markdown tables after the switch to render-register.py), and a session
# coming out of compaction followed this copy instead of the skill.
set -uo pipefail

SKILL="$HOME/.claude/skills/response-format/SKILL.md"
D="$HOME/.claude/skills/response-format"
RENDER="python3 $D/render-register.py"
PUBLISH="python3 $D/publish-register.py"
TERM_OUT="python3 $D/render-artifact.py"
[[ -f "$SKILL" ]] || exit 0   # no contract installed: say nothing, block nothing

read -r -d '' CONTEXT <<EOF
Before replying, follow the response contract in $SKILL. This is a pointer, not the contract:
if you have not read SKILL.md in THIS context window (a fresh session, or any time after a
compaction), read it in full now. Do not reconstruct the format from this text or from memory.
The non-negotiables, because they are what a session forgets:
1. CLARIFICATION GATE FIRST: if any of the user's answers is unclear, HALT, change nothing, and ask
   with the item's identifier, your concern, and the questions.
2. The register is RENDERED, never hand-written. Update <session scratchpad>/response-register.md
   first, write the draft as markdown (<scratchpad>/draft-rN.md), run
   $RENDER --check --register <register> <draft> until clean, then
   $PUBLISH <draft> (from the session's working directory; writes the per-round
   LOCAL pages and the live current.html; never a claude.ai Artifact), then put
   $TERM_OUT <draft> --terminal output VERBATIM in a code fence after a prose BLUF,
   followed by the live page's path. Hand-typed markdown tables are a contract violation.
3. Order: Targets (every round while any is active) -> Threads -> Answers -> Work done -> Open
   questions -> Actions -> Background (one row: live waits and when each fires).
4. A trivial turn (ack, status, one-liner) gets one net-net table of title + description instead.
EOF

jq -nc --arg ctx "$CONTEXT" \
  '{hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $ctx}}'
