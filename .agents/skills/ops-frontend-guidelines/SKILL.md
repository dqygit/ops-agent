---
name: ops-frontend-guidelines
description: "Guidelines and design system rules for developing frontend components, pages, and UI for the ops-agent project. Trigger this whenever the user asks to create or modify React components, CSS, UI styling, or any frontend features. Make sure to consult this skill before generating any Tailwind code or UI elements to ensure they match the 'Cyber-Ops Precision' design."
---

# Ops-Agent Frontend Guidelines (Cyber-Ops Precision)

This project uses a highly customized, dark-mode, tech-focused design system named **"Cyber-Ops Precision"**. When writing frontend code (React + Tailwind CSS), you MUST adhere to the following stylistic and structural guidelines.

## 1. Color Palette (Tailwind Custom Colors)

We do NOT use default Tailwind colors for our core UI. We use the custom `ops-*` color namespace defined in `tailwind.config.js`.

- **Backgrounds**:
  - `bg-ops-bg` (`#0B0F19`): The absolute darkest background, used for the outermost layout or body.
  - `bg-ops-panel` (`#151B28`): Used for secondary panels, cards, and sidebars.
  - `bg-ops-deep` (`#05080f`): Used for input fields, command blocks, and deeply nested areas to create contrast.

- **Borders**:
  - `border-ops-border` (with opacity, e.g., `border-ops-border/40`): Used for all dividers and card borders.

- **Functional/Accent Colors**:
  - `ops-cyan` (`#06B6D4`): **The primary accent color.** Used for AI Agent elements, active states, glowing borders, links, and primary buttons.
  - `ops-green` / `ops-emerald` (`#10B981`): Used for success states, completed tasks, and healthy server statuses.
  - `ops-danger` (`#EF4444`): Used for errors, rejections, and critical alerts.
  - `ops-warning` (`#F59E0B`): Used for pending approvals and warnings.
  - `ops-text` (`#F1F5F9`): Primary text color.
  - `ops-muted` (`#94A3B8`): Secondary/tertiary text color.

## 2. Typography

- **UI Text**: `font-sans` (mapped to `Inter`). Used for all standard interface text.
- **Code/Terminal**: `font-mono` (mapped to `JetBrains Mono`). Used for commands, logs, JSON, and terminal outputs.
- **Font Sizes**:
  - `text-[10px]` or `text-[11px] font-bold tracking-[0.1em]`: Used for tags, metadata, and system status indicators. **Avoid using all-caps for long English labels; use Title Case instead.**
  - `text-[13px]` or `text-[14px]`: Standard reading text and chat bubbles.
  - `text-[18px]` or `text-lg`: Primary headers. Use `font-black` or `font-bold` for emphasis.

## 3. Component & Styling Conventions

### Glassmorphism & Depth
- Instead of solid opaque headers, use backdrop blur: `bg-ops-panel/70 backdrop-blur-md`.
- Use inner shadows for code blocks and deep panels: `shadow-inner`.

### Hover & Active States (Motion)
- All interactive elements (buttons, inputs) MUST have smooth transitions: `transition-all duration-200`.
- Buttons must have a physical press effect: `active:scale-95`.
- Active or focused inputs should glow: `focus-within:ring-1 focus-within:ring-ops-cyan/40 focus-within:shadow-glow`.

### Status Tags / Badges
When displaying a status (e.g., Online, Running, Failed), use this pattern:
```tsx
// Glowing dot + colored text + colored background with low opacity
<span className="inline-flex items-center gap-1.5 rounded-md border border-ops-cyan/30 bg-ops-cyan/10 px-2 py-1 text-[10px] font-bold tracking-[0.1em] text-ops-cyan">
  <span className="h-1.5 w-1.5 rounded-full bg-ops-cyan animate-pulse" />
  Running
</span>
```

### Chat Bubbles / Event Cards
- **User Message**: Aligned right, cyan tint. `border-ops-cyan/20 bg-ops-cyan/10 shadow-[0_4px_16px_rgba(6,182,212,0.05)] backdrop-blur-sm`
- **Agent Container**: Left aligned, dark panel `bg-ops-panel/40 border border-ops-border/30 backdrop-blur-sm`.
- **Command Blocks**: Rendered like a sleek terminal inside the chat flow. `bg-ops-deep border border-ops-border/30 shadow-inner`. Code inside should use `bg-black/60 font-mono text-[12px]`.

## 4. How to Develop Components

1. **Tech Stack**: React 18, Vite, TypeScript, Tailwind CSS.
2. **No UI Libraries**: Do NOT import components from Shadcn UI, MUI, Ant Design, etc. Build components natively using Tailwind CSS utility classes based on the design system.
3. **Icons**: Use inline SVG icons. Keep them minimal with `stroke-width="2.5"` or `2.4` and `fill="none"`.
4. **Layout**: Flexbox and CSS Grid are preferred. The main layout is typically a full-screen `h-screen w-screen overflow-hidden` with panels dividing the space.
5. **Scrollbars**: Rely on the custom thin scrollbar defined in `index.css`. Avoid adding explicit scrollbar hiding unless necessary.

## 5. Summary Checklist for New Code
- [ ] Did I use `ops-*` colors instead of default `blue-500` or `gray-800`?
- [ ] Are buttons using `active:scale-95 transition-all`?
- [ ] Are small metadata labels using `text-[10px] font-bold tracking-[0.1em]` and Title Case (avoid ALL CAPS for long text)?
- [ ] Is the code block/terminal text using `font-mono text-[12px]`?
- [ ] Did I avoid adding new dependencies for UI components?
