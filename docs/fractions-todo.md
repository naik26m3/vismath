# Fraction Visualizer — Wishlist

Tasks for `fractions.html` + `js/fractions.js` only.
**The open tasks are collected in `docs/todo.md` — work from that one.** This file keeps the history and the reasons.
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

## The plan (what "done" looks like for this tool)

Written 2026-09-26. This is the real goal — the stuff below is in service of it.

- [x] **Tap a piece to shade it.** Done. `pointerdown` records the piece (`e.target` is still
      correct there — after `setPointerCapture` everything retargets to the bar), `pointerup`
      shades it only if the bar moved less than 5px. Total above the bar recounts with
      `bar.querySelectorAll('.bg-amber-300').length`.

- [x] **"3/4 of 20 = ?"** — working end to end.
      "Add Number" spawns a draggable chip. Drop it on a bar → the chip disappears, every piece
      shows its share, and the label above reads `15 (3/4)`. The bar remembers its whole in
      `bar.dataset.whole`, so tapping pieces afterwards recalculates correctly.
      Drop detection: `document.elementFromPoint(x, y)` then `.closest('.js-bar')`.

      Left over from it:
      - [ ] Whole values that do not divide evenly show long decimals (`20/3` → `6.666…`).
            Wanted: mixed numbers (`6 2/3`). Needs exact fraction math — keep numerator and
            denominator, add them properly, reduce with a GCD. Do not use floats.
      - [x] DONE — The chip sat under your own finger, so `elementFromPoint` can return the chip
            instead of the bar behind it. Fix: `chip.style.pointerEvents = 'none'` just around
            the lookup.
      - [ ] `addBar` and `addNumber` have near-identical drag code. A `makeDraggable(el)` was
            started and abandoned — the blocker was passing a callback for "what a tap means".
            Come back when callbacks click; it is a 10 minute job then.

---

## Now

- [x] **Decided how shaded pieces are labelled** — option **F** in `demos/shade-labels.html`:
      every piece keeps its `1/n` label, empty ones faded (`opacity-50`), and the running
      total (`2/4`) sits above the bar.
      *Why:* the kid counts `1/4 + 1/4` across the bar and sees it match the number on top,
      so the total is arrived at rather than announced. Keeping the faded labels means the
      remainder is visible as quarters — "there are two more left" — which is what the
      `3/4 of 20` work needs. Watch it at denominator 12; it gets busy.
      *Amended 2026-10-03:* once a number is merged in, the pieces show the share
      (`5`) instead of `1/4`. The fraction still shows in the label above the bar.

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

- [x] DONE with KaTeX (`frac()` in `js/fractions.js`) — **Stacked fraction symbol in the BARS.** The dialog already does this (numerator over
      denominator, border as the fraction line). The bar pieces still say `1/5` as flat text.
      Same trick should work — no KaTeX needed.
- [ ] **Validation gaps still open:**
      - non-integers pass (`2.5` → pieces labelled `1/2.5`)
      - the error message is just "Please type the value again" — it does not say which rule
        was broken (denominator 1–9, numerator ≤ denominator). A kid cannot guess.
- [ ] **Responsive layout** — the stage is `w-full max-w-[50rem] h-[35rem]`, which does not behave
      on a phone. Practice target: `clamp()`, breakpoint prefixes, no hardcoded heights.
- [ ] **Use it at work once.** Real session, real kid. Fix whatever actually broke.

---

## Known rough edges

- [ ] **Large denominators.** The bar is a fixed `w-60`, so at `1/20` each piece is ~12px wide
      and the `1/20` label does not fit; at `1/100` it is ~2px. Max expected is 100.
      Think about what a piece should show when there is no room — drop the label and keep the
      total above? Shrink the text with a threshold? Widen the bar as the denominator grows
      (but then bars are no longer comparable, which breaks the whole point)? Show tick marks
      instead of boxes past some number?
      Decide the UX first, like the shading labels — `demos/` is the place to try it.
- [x] DONE — Text inside the stage can be highlighted while dragging — a long press on a tablet selects
      `1/4` and pops up the copy menu. Fix: `select-none` (`user-select: none`) on bars and chips.
- [ ] Bars can be dragged outside the stage entirely and get lost (demo clamps with `Math.max`/`Math.min`)
- [ ] Delete button may be clipped by `overflow-scroll` when a bar sits at the very top
- [ ] `overflow-scroll` vs `overflow-hidden` — not decided. Scrolling and dragging compete for the same finger.
- [ ] Dragging a bar does not bring it to the front; it can end up under another bar
- [ ] No `pointercancel` handler — an interrupted drag leaves `isDragging` stuck on
- [x] DONE (`BAR_HEIGHT`) — `14 * 4` hardcoded in `bar.style.top` — that is the bar height from `h-14`. Change `h-14` and
      this silently breaks. Name it, like `BAR_SPACING`.
- [x] DONE — The two input fields are re-queried on every submit; `stage`/`input`/`form` are cached at the top

---

## Deferred on purpose (polish)

Core first. Come back to these.

- [x] DONE (single light theme) — Colors and contrast (`bg-amber-300` with inherited light text in dark mode)
- [ ] Sizes and spacing
- [x] DONE — Stage border styling
- [ ] Redundant `mx-auto` on elements already centered by flex
- [ ] Spinner arrows on the number inputs (needs `::-webkit-inner-spin-button` in style.css)

---

## Someday

- [x] Label each bar with the fraction it shows (`3/4` above or beside it)
- [ ] Only the selected bar shows its `✕` (the Canva-style selection idea)
- [ ] Snap bars to align left edges, so comparing is exact
- [x] Click a piece to toggle it filled/empty
- [ ] Bring a bar to the front when you grab it
- [ ] Duplicate a bar
- [ ] Keep bars after a page refresh (`localStorage`)

---

## Next tool: percentages

Decided 2026-09-29. A percentage bar is a fraction bar with denominator 100 and different
labels, so most of this file already applies — dragging, tap to shade, the whole-value chip,
the running total.

Worth working out before starting:
- How much of `js/fractions.js` is actually reusable vs copy-pasted? This is the first real
  chance to see what belongs in a shared file.
- 100 pieces is exactly the "large denominators" problem above. Solve that first and the
  percentage bar mostly falls out of it.
