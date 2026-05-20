---
name: ops-browser-verification
description: Use when verifying ops-agent changes that affect console runs, terminal initialization, asset terminal context, asset command execution, approvals, SSE rendering, or plan mode behavior in the browser.
---

# Ops Browser Verification

## Overview

Verify Ops Agent in a real browser against the local app. Type checks and builds do not prove console, terminal, asset execution, approval, SSE, or plan-mode behavior works.

## Required Startup

Identify the OS before starting from the repository root:

| OS | Command |
| --- | --- |
| Windows | `scripts\\run.bat` |
| macOS/Linux | `./scripts/run.sh` |

Confirm backend `127.0.0.1:8000` and frontend `http://localhost:5173` are reachable. Never use `./scripts/run.sh` on Windows.

## Required Browser Flows

### 1. Terminal initialization multi-turn

Verify both paths when available:

| Path | Required observations |
| --- | --- |
| Normal terminal | Open/create a terminal, start an assistant conversation, ask an initial terminal-related prompt, then at least one follow-up. Confirm the follow-up keeps the correct terminal context and streamed messages render in order. |
| Asset terminal | Select an asset, open its terminal, start a conversation, then ask at least one follow-up. Confirm asset identity and terminal session context persist across turns. |

If local data has no usable asset, state that explicitly and verify the normal terminal path.

### 2. Asset command execution from conversation

From an asset-scoped conversation, request a safe read-only command that requires backend asset execution. Confirm:
- approval UI appears when required
- approval triggers backend execution, not chat-only pretending
- command card status changes are visible
- output or failure reason renders in the conversation
- browser Console and Network show no unexpected errors

Do not bypass the human approval chain.

### 3. Plan mode conversation

Enable plan mode and ask for a small operational plan. Confirm:
- plan content renders instead of command execution
- commands mentioned in the plan are not run automatically
- plan events render correctly
- a follow-up stays in plan mode, or the UI clearly shows the mode change

## Report Evidence

Report only observed evidence:

| Area | Evidence |
| --- | --- |
| Startup | OS and command used |
| Terminal multi-turn | normal terminal result and asset terminal result |
| Asset execution | command requested, approval behavior, final status |
| Plan mode | prompt used and whether execution was avoided |
| Browser health | Console/Network errors, if any |

## Common Mistakes

| Mistake | Correction |
| --- | --- |
| Running only `pyright` or `pnpm build` | Still verify all three browser flows. |
| Using `./scripts/run.sh` on Windows | Use `scripts\\run.bat`. |
| Testing only normal terminal | Also test asset terminal when an asset is available. |
| Asking for dangerous commands | Use safe read-only commands and preserve approval. |
| Trusting chat text as execution proof | Verify command card, approval, backend request, and result. |
| Treating plan mode as normal chat | Confirm plan mode does not execute commands. |
