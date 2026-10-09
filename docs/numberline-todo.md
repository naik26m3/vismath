# Number Line — Wishlist

**The open tasks are collected in `docs/todo.md` — work from that one.** This file keeps the history and the reasons.

Tasks for `numberline.html` + `js/numberline.js`.

---

## Done

- [x] Min / max inputs draw the range as rows
- [x] Rows wrap every 20 numbers, like a textbook number line
- [x] Short last row keeps the same tick spacing by taking a smaller width
      (`(max - min) / 20 * 100%` of the inner stage) instead of stretching
- [x] Rows share one left edge — inner wrapper is `items-start`, stage centres the wrapper
- [x] Ticks line up with the ends of the line (`w-0` wrappers, so the box edge IS the tick)
- [x] Stage fills the screen height and scrolls inside itself

---

## Good plane tasks (no internet needed)

- [ ] **Validation.** Right now these all do nothing, with no message:
      - `max` smaller than `min` — row count is negative, loop never runs
      - `max` equal to `min` — one row with a single tick
      - either box left blank — `Number("")` is `0`, so it silently uses 0
      - a huge range like `0` to `100000` — builds thousands of divs and freezes
      Decide a sensible cap and write a message that says which rule was broken,
      not just "Pls input a whole number".

- [ ] **The `20` lives in two places** — `gap` in the click handler, and hardcoded in
      `makeLine`'s width formula. Change one and they disagree. Make it one constant
      at the top, or a parameter that `makeLine` receives.

- [ ] **Rows per screen width.** 20 numbers per row collide in portrait. Want roughly
      10 in portrait, 20 in landscape. `stage.clientWidth` tells you the room available.
      This depends on the task above being done first — `perRow` has to be one value
      before it can vary.

- [ ] **The full-height chain is not actually working.** `stage.clientHeight` logged
      3180px, meaning the stage is as tall as its content rather than the screen.
      Needs `flex-1 min-h-0` on BOTH `<main>` and `#js-number-line-stage`, with
      `h-dvh flex flex-col` on `<body>`. Check all three.

- [ ] Stray empty `console.log()` in the click handler.

---

## Not designed yet

- [ ] **Stepping mode.** A marker on the line, and buttons to move it, so a student
      walks `3 + 5` instead of counting on fingers. Hop arcs drawn per jump so the
      jumps can be counted afterwards.

      Parked because the design is not settled. Open questions:
      - Jumps of 1 only, or also 10? (Big jumps are how `47 + 36` is actually taught:
        three tens, then six ones. The decomposition IS the lesson.)
      - Subtraction: count back from the bigger number, or count UP from the smaller
        one and read off the distance? The second is how most teachers do it, and it
        needs a different readout — the answer is how far you travelled, not where
        you landed.
      - What happens to a jump that crosses a row boundary? It fits on neither row.
      - Does the marker stay put while the line slides (see `demos/number-line.html`),
        or move along a fixed line?

      `demos/number-line.html` has a working version of all of this to react to.
