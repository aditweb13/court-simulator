# Design system: Verdict

A warm, serious courtroom look: wood, parchment and brass. Light and dark themes. Contrast values are approximate; verify with a checker when implementing.

## Color tokens

| Token | Light | Dark | Use |
|---|---|---|---|
| `primary` | `#8A5A2B` | `#D9A766` | Main actions, links, focus accents |
| `secondary` | `#2B4A6A` | `#8FB4D9` | Defense side, secondary actions |
| `background` | `#FAF6EE` | `#1E1813` | Page background |
| `surface` | `#FFFFFF` | `#2A221B` | Cards, modals, panels |
| `text-primary` | `#2A2118` | `#F1E8DA` | Body and headings |
| `text-secondary` | `#6E6253` | `#B4A692` | Captions, hints |
| `border` | `#D9CDB9` | `#463B30` | Dividers and outlines |
| `destructive` | `#A32D2D` | `#F09595` | Errors, delete, guilty marker |
| `success` | `#3B6D11` | `#97C459` | Success, not-guilty marker |
| `prosecution` | `#6A2B2B` | `#E0A0A0` | Prosecution labels |
| `defense` | `#2B4A6A` | `#8FB4D9` | Defense labels |

Contrast (approximate): `text-primary` on `background` about 14:1; `text-secondary` on `background` about 5.5:1; white on `primary` about 5.9:1; `destructive` on `background` about 6.5:1. All pass WCAG AA for body text.

## Typography

Fonts: **Source Serif 4** for headings and the verdict text, **Inter** for UI. Fallbacks: `Georgia, serif` and `system-ui, sans-serif`.

| Style | Size / line-height | Weight |
|---|---|---|
| h1 | 36px / 44px | 600 |
| h2 | 28px / 36px | 600 |
| h3 | 22px / 30px | 600 |
| h4 | 18px / 26px | 600 |
| h5 | 16px / 24px | 600 |
| h6 | 14px / 20px | 600 |
| body | 16px / 26px | 400 |
| caption | 13px / 18px | 400 |
| courtroom caption (spoken line) | 18px / 28px | 400 |

Two weights only: 400 and 600.

## Spacing and radius

Base unit 4px. Scale: `1=4, 2=8, 3=12, 4=16, 6=24, 8=32, 12=48, 16=64`.
Radius: `sm=4px` (inputs, chips), `md=8px` (buttons), `lg=12px` (cards, modals), `full=9999px` (badges).

## Components

**Button.** Variants: primary (filled `primary`, white text), secondary (outlined), ghost (text only), destructive (filled `destructive`).
States: default; hover darkens 8%; focus shows a 2px ring in `primary` with 2px offset; disabled at 50% opacity with `cursor: not-allowed`; loading shows a spinner and blocks clicks. Minimum height 40px.

**Card.** `surface` background, 1px `border`, `lg` radius, 16-24px padding. Hover (when clickable) raises the border to `primary`. Focus uses the same ring as buttons.

**Input.** 40px high, 1px `border`, `sm` radius, `surface` background. Hover darkens the border; focus uses the 2px `primary` ring; error uses a `destructive` border plus an error message below with an icon, not color alone; disabled uses 50% opacity.

**Modal.** Centered, `surface`, `lg` radius, backdrop at 50% black. Traps focus, closes on Escape, returns focus to the trigger. Title in h3.

**Toast.** Bottom right, 4 s auto-dismiss (6 s for errors), has a close button, `role="status"` (or `role="alert"` for errors). Variants: info, success, error.

**Objection button.** Large destructive-style button in the human lawyer UI. Keyboard shortcut `O`. Disabled when the quota is used up, with an explanatory tooltip.

## Layout

- Mobile-first. Breakpoints: `sm 640px`, `md 768px`, `lg 1024px`, `xl 1280px`.
- Content max width 1200px; the 3D canvas fills the viewport width.
- Trial screen: 3D canvas on top; caption bar overlaid at the bottom; side panel (transcript, notes) on `lg` and up, bottom sheet on small screens.
- 12-column grid with 24px gutters on `lg` and up.

## Accessibility

- Every spoken line appears as a caption and in the transcript; audio is optional.
- All controls reachable by keyboard; visible 2px focus ring; logical tab order; skip link to the main content.
- Respect `prefers-reduced-motion`: disable camera sweeps and character idle motion, and cut instead of pan.
- ARIA: caption bar `aria-live="polite"`; modals `role="dialog"` with `aria-labelledby`; toasts `role="status"`/`role="alert"`; the 3D canvas has an `aria-label` describing the scene, with a text transcript as the accessible alternative.
- Never use color alone for guilty or not guilty; add text and an icon.
- Text contrast at least 4.5:1 (3:1 for 24px and larger).

## Empty, loading and error states

| View | Empty | Loading | Error |
|---|---|---|---|
| Case library | "No cases yet" with a button to load sample cases | Card skeletons | Message plus Retry |
| Trial screen | "Choose a case to begin" | "The court is assembling" with the scene fading in, plus a thinking animation for agents | "The court lost connection" with Reconnect; "All AI providers are busy" with Retry |
| Transcript | "Nothing said yet" | Line skeleton | Message plus Reload |
| Verdict screen | n/a | "The jury is deliberating" with progress by stage | Message plus "Re-run voting" |
| Replay | "No finished trials" | Skeleton | Message plus Retry |
| Admin (P2) | "No LLM calls yet" | Table skeleton | Message plus Retry |

## Tailwind: `globals.css` (Tailwind 4)

```css
@import "tailwindcss";

@theme {
  --color-primary: var(--primary);
  --color-secondary: var(--secondary);
  --color-background: var(--background);
  --color-surface: var(--surface);
  --color-text-primary: var(--text-primary);
  --color-text-secondary: var(--text-secondary);
  --color-border: var(--border);
  --color-destructive: var(--destructive);
  --color-success: var(--success);
  --font-serif: "Source Serif 4", Georgia, serif;
  --font-sans: "Inter", system-ui, sans-serif;
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
}

:root {
  --primary: #8A5A2B;
  --secondary: #2B4A6A;
  --background: #FAF6EE;
  --surface: #FFFFFF;
  --text-primary: #2A2118;
  --text-secondary: #6E6253;
  --border: #D9CDB9;
  --destructive: #A32D2D;
  --success: #3B6D11;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --primary: #D9A766;
    --secondary: #8FB4D9;
    --background: #1E1813;
    --surface: #2A221B;
    --text-primary: #F1E8DA;
    --text-secondary: #B4A692;
    --border: #463B30;
    --destructive: #F09595;
    --success: #97C459;
  }
}

:root[data-theme="dark"] {
  --primary: #D9A766;
  --secondary: #8FB4D9;
  --background: #1E1813;
  --surface: #2A221B;
  --text-primary: #F1E8DA;
  --text-secondary: #B4A692;
  --border: #463B30;
  --destructive: #F09595;
  --success: #97C459;
}

body {
  background: var(--background);
  color: var(--text-primary);
  font-family: var(--font-sans);
  line-height: 1.6;
}

:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
}
```
