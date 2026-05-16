---
name: ops-ui-design
description: Use when adding, changing, or reviewing Ops Agent frontend UI, settings panels, assistant conversation cards, terminal surfaces, command execution displays, dark console layouts, Tailwind styling, or visual QA for this project.
---

# Ops UI Design

## Overview

Ops Agent UI should feel like a focused operations console: dark, dense, calm, and trustworthy. Preserve the existing visual language before inventing new styles.

## Use This Before UI Work

1. Inspect nearby UI first: settings sections, assistant cards, terminal panels, and layout primitives.
2. Reuse existing components/classes before adding new ones.
3. Implement the smallest UI change that fits the current pattern.
4. Review all states, not just the happy path.

## Visual Language

| Element | Rule |
|---|---|
| Surface | Deep dark panels with subtle borders; avoid bright cards or generic SaaS dashboards. |
| Accent | Use `ops-cyan` for primary action, focus, selected, and active states. |
| Danger | Use `ops-danger` only for destructive, failed, or high-risk states. |
| Density | Keep information compact; prefer clear grouping over large whitespace. |
| Typography | Keep labels and metadata restrained; command/output text may use monospace. |
| Motion | Use subtle transitions only; no decorative animation. |

## Reuse Targets

Prefer these before writing custom styles:

- `web/src/components/layout/PanelCard.tsx` for panel surfaces.
- `web/src/components/layout/Button.tsx` or `.button*` classes for actions.
- `web/src/index.css` for `.field-control`, `.button`, `.button-mini`, `.settings-error`, `.chat-bubble*`.
- Existing settings sections for form layout, section headers, empty states, loading, and error display.
- Existing assistant conversation cards for command, approval, plan, status, and error rhythm.

## Component Rules

### Settings UI
- Match existing section structure: list/detail/form actions should align with sibling sections.
- Include loading, empty, error, editing, saving, disabled, and delete-confirmation states when relevant.
- Keep JSON, command, env, and secret fields visually distinct but not flashy.

### Assistant and Command UI
- Command execution must communicate safety: pending approval, running, success, failure, and denied states should be visually distinct.
- Do not make dangerous actions look like normal primary actions.
- Preserve readable terminal/output formatting and avoid wrapping that hides command semantics.

### Layout and Panels
- Prefer existing borders, gradients, rounded corners, and shadows.
- Avoid adding new visual systems: glassmorphism, heavy glow, oversized hero sections, marketing gradients, colorful badges everywhere.
- If a custom class is necessary, make it local and consistent with existing tokens.

## Review Checklist

Before calling UI work done, verify:

- The UI looks native next to existing settings, assistant, and terminal surfaces.
- It uses existing tokens/components instead of one-off Tailwind styling where practical.
- Primary, secondary, danger, disabled, loading, empty, and error states are covered.
- Spacing and density match neighboring components.
- Text hierarchy makes operational decisions faster, not prettier.
- Risky actions require clear danger treatment and confirmation where appropriate.
- The change does not weaken command approval or imply unapproved commands already ran.
- Browser/dev-server verification was performed for visual changes, or the limitation is stated clearly.
- Review notes include concrete evidence: checked screens/components, covered states, and any screenshot/manual verification boundary.

## Common Mistakes

| Mistake | Fix |
|---|---|
| "Used ops colors, so it matches." | Also match component structure, density, borders, states, and interaction rhythm. |
| Recreating Button/Panel styles inline | Reuse `Button`, `PanelCard`, or shared CSS classes first. |
| Generic dark dashboard look | Reduce decoration; favor operational clarity and existing console patterns. |
| Only checking build output | Inspect the UI state in context, including edge states. |
| Making danger actions cyan | Use danger styling and confirmation for destructive actions. |

## Quick Prompt For Reviews

When reviewing UI, ask: "Would this look like it shipped with the existing Ops Agent console, and can an operator understand state, risk, and next action immediately?"
