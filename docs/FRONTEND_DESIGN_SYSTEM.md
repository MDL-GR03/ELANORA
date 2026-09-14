# ELANORA frontend design system

The interface uses a restrained institutional visual language: neutral research
surfaces, strong information hierarchy, compact controls, and institution-owned
accent colors. Shared tokens live in `src/assets/css/design-system.css`; feature
styles should consume those tokens rather than introduce new hard-coded brand
colors, shadows, radii, or content widths.

Route components remain code-split. Heavy configuration panels, profile panels,
Font Awesome compatibility code, and tree editing dependencies must not be
eagerly imported by the application shell. Every asynchronous route has a
consistent accessible fallback. Data stores expose idempotent `ensure...`
operations so an empty collection is treated as a loaded result rather than a
reason to refetch on every navigation.

Background polling must check document visibility, be owned by the component
that starts it, and be cleaned up on unmount. Independent requests should run
concurrently. Loading indicators should preserve layout and must respect the
user's reduced-motion preference.

New screens should work at 320 CSS pixels without horizontal page scrolling,
use at least 44 pixel touch targets for primary interactions, retain visible
keyboard focus, and avoid hiding essential actions behind hover behavior.
Tables and deeply nested annotation structures may use an explicitly labelled
local horizontal scroller rather than forcing the whole page wider.
## Presentation architecture

The authenticated application uses the Projects workspace as its visual and
interaction baseline. New screens should reuse the following layers instead of
introducing isolated page shells.

1. `design-system.css` owns typography, color, spacing, radius, elevation,
   focus, and control defaults.
2. `DefaultLayout.vue` owns the single authenticated `main` landmark and the
   shared content width.
3. `WorkspaceHeader.vue` owns page context, the single page-level `h1`, the
   description, and the optional action slot. Use its `embedded` variant when
   the heading belongs inside a larger surface.
4. Page styles own only workflow layout and component-specific states. They
   must not redefine the canvas, global content width, typography family, or
   generic form focus treatment.

Prefer semantic HTML and existing components. Preserve native controls for
forms and selects. A visual section should become a landmark only when it has a
useful accessible name; too many landmarks make navigation noisier. At narrow
widths, preserve content order and allow local overflow for intrinsically wide
research data such as annotation tables.

## Accessibility enforcement

`eslint-plugin-vuejs-accessibility` runs as part of `npm run lint`, so template
accessibility regressions fail the same gate as any other lint error. The
target remains WCAG 2.2 AA, which matters here because the research community
includes Deaf and disabled researchers who work keyboard-first.

One rule is deliberately reconfigured. `label-has-for` defaults to demanding
both a nested control and a `for`/`id` pairing; WCAG accepts either, so the
project requires only one of them. Nothing else is relaxed.

A handful of suppressions remain, each carrying its justification in the
template above it. They share one shape: the flagged element is not a control,
and the keyboard path exists elsewhere.

- Modal scrims are `role="presentation"`; the keyboard path is Escape.
- The upload drop zone keeps its browse buttons as the equivalent control,
  because dropping a file has no keyboard equivalent by nature.
- Listbox options react to hover, but the active option moves with the arrow
  keys handled on the combobox trigger, so they are never focused themselves.
- Live regions and popovers pause their own dismissal timers on pointer and on
  focus alike.

Adding a new suppression means writing down why the keyboard path is already
covered. If that sentence cannot be written honestly, the markup is wrong.

## Modal dialogs

Every modal uses `useModalDialog`, which owns Escape, the Tab and Shift+Tab
focus trap, moving focus into the dialog when it opens, and returning focus to
whatever opened it. It supports dialogs kept mounted behind a visibility flag
and dialogs created only while open.

Do not hand-roll this behavior in a component. It was previously duplicated
across eight dialogs, which had drifted apart, so a correction to one never
reached the others. The listener is attached in script rather than through a
template handler, which keeps the dialog container a plain labelled region for
assistive technology.

A dialog still owns its own `role="dialog"`, `aria-modal="true"` and an
accessible name via `aria-labelledby`.

## Drag and drop

Drag and drop is an enhancement, never the only way to perform an operation.
Every draggable research object must have a visible handle, a clear target
state, and an equivalent native control that works with keyboard, touch, voice,
and other assistive input. Persist only operations represented by the backend
contract; do not imply that arbitrary ordering is saved when the domain stores
only group membership. Failed moves must restore the authoritative server
state and expose an error through an accessible live region.
