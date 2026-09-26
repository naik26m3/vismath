# Fraction Visualizer — Wishlist

Tasks for `fractions.html` + `js/fractions.js` only.
Newest ideas go at the bottom of "Someday". Move things up as they get real.

---

## Done

- [x] Bar renders with `flex-1` pieces so every bar is the same width (the math stays honest)
- [x] Filled pieces colored, empty pieces not
- [x] New bars stack below each other (`BAR_SPACING`)
- [x] Drag a bar with mouse
- [x] Drag survives fast movement and leaving the bar (`setPointerCapture`)
- [x] Drag works with a finger on a tablet (`touch-none`)
- [x] Drag stays correct after the stage is scrolled (`scrollTop` / `scrollLeft`)
- [x] Clear button empties the stage and resets the counter
- [x] **Delete button per bar** — `✕` on the corner, removes that bar.
      Needed `e.stopPropagation()` on the button's `pointerdown`, or the bar's
      `setPointerCapture` stole the release and no `click` was ever created.
- [x] **Replaced `prompt()` with a `<dialog>`** — one popup, both numbers at once,
      stacked like a real fraction, numeric keypad on tablet, Enter submits.
- [x] **Validation moved into the form's `submit`** so a bad number keeps the dialog
      open with the typed values intact, and the error shows in the dialog instead of `alert()`.
- [x] `addBar(numerator, denominator)` pulled out as its own function

---

## Now

- [ ] **Improper fractions** (e.g. `9/8`). Decide what it should LOOK like first — this is a
      teaching decision, not a code one. Options:
      - one bar with 9 pieces → pieces get smaller, so it no longer compares honestly ✗
      - a bar that runs past the "1 whole" mark, with the whole marked somehow
      - two bars: one full, one with the remainder
      What do you draw on paper for a kid? Do that.

- [ ] **Fix the spawn slot.** `barCounter--` in the delete listener is wrong — the counter means
      "how many bars I've ever made", not "how many exist". Delete the first of 3 bars, add a new
      one, and it lands on top of an existing bar.
      Fix: drop the `--`, and wrap the slot with `%` so it cycles instead of falling off the bottom.
      `const slot = barCounter % SLOT_COUNT` — see `js/fractions-demo.js` for the shape.

---

## Next

- [ ] **Stacked fraction symbol in the BARS.** The dialog already does this (numerator over
      denominator, border as the fraction line). The bar pieces still say `1/5` as flat text.
      Same trick should work — no KaTeX needed.
- [ ] **Validation gaps still open:**
      - non-integers pass (`2.5` → pieces labelled `1/2.5`)
      - no upper bound (`500` builds 500 divs)
- [ ] **Responsive layout** — the stage is `w-full max-w-[50rem] h-[35rem]`, which does not behave
      on a phone. Practice target: `clamp()`, breakpoint prefixes, no hardcoded heights.
- [ ] **Use it at work once.** Real session, real kid. Fix whatever actually broke.

---

## Known rough edges

- [ ] Bars can be dragged outside the stage entirely and get lost (demo clamps with `Math.max`/`Math.min`)
- [ ] Delete button may be clipped by `overflow-scroll` when a bar sits at the very top
- [ ] `overflow-scroll` vs `overflow-hidden` — not decided. Scrolling and dragging compete for the same finger.
- [ ] Dragging a bar does not bring it to the front; it can end up under another bar
- [ ] No `pointercancel` handler — an interrupted drag leaves `isDragging` stuck on
- [ ] `14 * 4` hardcoded in `bar.style.top` — that is the bar height from `h-14`. Change `h-14` and
      this silently breaks. Name it, like `BAR_SPACING`.
- [ ] The two input fields are re-queried on every submit; `stage`/`input`/`form` are cached at the top

---

## Deferred on purpose (polish)

Core first. Come back to these.

- [ ] Colors and contrast (`bg-amber-300` with inherited light text in dark mode)
- [ ] Sizes and spacing
- [ ] Stage border styling
- [ ] Redundant `mx-auto` on elements already centered by flex
- [ ] Spinner arrows on the number inputs (needs `::-webkit-inner-spin-button` in style.css)

---

## Someday

- [ ] Label each bar with the fraction it shows (`3/4` above or beside it)
- [ ] Only the selected bar shows its `✕` (the Canva-style selection idea)
- [ ] Snap bars to align left edges, so comparing is exact
- [ ] Click a piece to toggle it filled/empty
- [ ] Bring a bar to the front when you grab it
- [ ] Duplicate a bar
- [ ] Keep bars after a page refresh (`localStorage`)
