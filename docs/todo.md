# VisMath — The one list

Everything still to do, in one file, written so you can work from it with
nobody to ask. Each task has a target and a hint. No answers.

The per-tool files (`fractions-todo.md`, `numberline-todo.md`,
`answerkey-todo.md`) keep the history of what was done and why. This file is
the one to work from.

---

## Before the plane

- [ ] Open each page once in the browser with Live Server while you still have
      internet, and **leave the tabs open**. Tailwind (and KaTeX on the fraction
      page) load from the internet; a tab that is already open keeps working,
      a fresh one will show with no styling.
- [ ] `git pull` and check Live Server starts.
- [ ] Open DevTools once so you know the Console tab is showing all levels.

---

## Part 1 — Plane tasks (need nothing but your editor)

Ordered so the short ones come first. Tick them off as you go.

### Answer key (`answerkey.html`, `js/answerkey.js`)

- [ ] **A1. Tidy `updatePage(page, num, img)`.** (5 min)
      Inside it, `page` is the `<img>`, `num` is the title, `img` is a path.
      Rename the three parameters to what they really are. Nothing else changes.

- [ ] **A2. Scroll back to the top when the page changes.** (15 min)
      Try it: scroll a page half-way down, press →. The new page opens half-way
      down too, because the box kept its scroll position.
      The box that scrolls is the `div` around the `<img>`, not the image, so
      you need a handle on that div.
      Hint: a box knows how far it has been scrolled. You used that property in
      the fraction drag math (`stage.scroll…`). Reading it tells you; setting it
      moves the box.
      Do it for both halves. Where is the one place both halves pass through
      when a page changes?

- [ ] **A3. Safety net: a lesson with no pages.** (20 min)
      `lesson.pageImages[0]` assumes the list has at least one page. If a list
      is empty, `[0]` is `undefined`, `pageNumber(undefined)` throws, and the
      code stops there, so the answer half never loads either.
      Target: when a list is empty, that half shows a short message such as
      "No pages for this lesson", and the other half still loads.
      Hint: `.length` tells you how many items a list has.
      How to test (no lesson is empty any more): after a lesson has loaded,
      type `lesson.pageImages = []` in the console, then press → or ←. Or make
      a copy of a lesson file with `"pageImages": []` and load that.
      Check both lists: `pageImages` and `answerPageImages`.

- [ ] **A4. Show when a button has nowhere to go.** (30 min)
      On the first page ← does nothing and nothing says why. Same for → on the
      last page. Most lessons have one answer page, so both answer buttons are
      dead most of the time.
      Target: a button that cannot move looks faded and cannot be pressed.
      Hints: buttons have a `disabled` property (true / false). Tailwind has a
      `disabled:` variant, used like `hover:`, for example `disabled:opacity-40`.
      Think about WHEN it has to be worked out: after every press, and when a
      lesson first loads. That points at one function that sets all four
      buttons from the two indexes, called from those places.

- [ ] **A5. Tidy the picker's labels.** (15 min)
      Entries like `1.0 Get Ready` and `1.R Chapter 1 Review` show ids that were
      made up for file names. Show the number only for real lessons (1.1, 1.2…),
      and just the title for the rest.
      Hint: what do the made-up ids have after the dot? `0`, `R`, `T`, `C`.
      A real lesson has a digit from 1 to 9 there. `item.lesson.split(".")`
      gives you the two halves.

- [ ] **A6. Bigger buttons.** (5 min)
      `h-[2rem]` is small for a finger. The fraction page uses `h-11`.

- [ ] **A7. The four button listeners are nearly the same code.** (optional)
      Only merge them if you can see a way that is still easy to read. Fine to
      skip.

### Number line (`numberline.html`, `js/numberline.js`)

- [ ] **N1. Stray empty `console.log()`** in the click handler. (1 min)

- [ ] **N2. The `20` lives in two places.** (10 min)
      `gap` in the click handler, and typed into `makeLine`'s width formula.
      Change one and they disagree. Make it one constant at the top of the
      file, or a parameter `makeLine` receives. Do this before N4.

- [ ] **N3. Validation.** (30 min)
      Each of these currently does nothing, with no message. Try them first:
      - `max` smaller than `min`
      - `max` equal to `min`
      - either box left blank (`Number("")` is `0`, so it silently uses 0)
      - a huge range like `0` to `100000` (builds thousands of divs, may freeze:
        save your work before trying this one)
      Decide a sensible cap, and write messages that say which rule was broken.
      Hint: guard clauses with an early `return`, like the fraction dialog.

- [ ] **N4. Fewer numbers per row in portrait.** (30 min, needs N2)
      20 numbers per row collide when the screen is narrow. Want about 10 in
      portrait, 20 in landscape.
      Hint: `stage.clientWidth` tells you how much room there is. Pick the
      per-row number from that, before the rows are built.

- [ ] **N5. The full-height chain.** (15 min)
      `stage.clientHeight` once logged 3180px, meaning the stage was as tall as
      its content, not the screen. Check the chain:
      `<body>` has `h-dvh flex flex-col`, `<main>` has `flex-1 min-h-0`, and
      `#js-number-line-stage` has `flex-1 min-h-0`. All three, in `class`,
      not in `id`. `demos/min-h-0.html` shows why each one matters.

### Fractions (`fractions.html`, `js/fractions.js`)

- [ ] **F1. Fix the spawn slot.** (15 min)
      `barCounter--` in the delete listener is wrong. The counter means "how
      many bars I have ever made", not "how many exist". Test: add 3 bars,
      delete the first, add another. It lands on an existing bar.
      Fix: delete the `--`, and wrap the slot so it cycles instead of running
      off the bottom: `const slot = barCounter % SLOT_COUNT`.
      `%` is the remainder: `7 % 5` is `2`. It keeps any number inside
      0 to SLOT_COUNT-1.

- [ ] **F2. Validation gaps.** (15 min)
      `2.5` still passes (pieces get labelled `1/2.5`): `Number.isInteger`.
      The error message is just "Please type the value again": say which rule
      was broken (denominator 1 to 9, numerator not above the denominator).

- [ ] **F3. Bars can be dragged out of the stage and lost.** (20 min)
      Hint: clamp the position before setting it.
      `Math.max(0, Math.min(x, biggestAllowedX))` keeps `x` between the two.
      The biggest allowed x is the stage's width minus the bar's width.

- [ ] **F4. Bring a bar to the front when you grab it.** (10 min)
      Hint: `z-index`. Keep one counter that goes up by one on every grab and
      give the grabbed bar that number as its `style.zIndex`.

- [ ] **F5. `pointercancel`.** (5 min)
      If the browser interrupts a drag, `pointerup` never fires and
      `isDragging` stays true. Listen for `pointercancel` and do what
      `pointerup` does.

- [ ] **F6. The same fix for number chips.** (5 min)
      `numberCounter--` has the same problem as `barCounter--` in F1, and chips
      can be dragged out of the stage like bars in F3. Once F1 and F3 work for
      bars, do the same for chips.

- [ ] **F7. Delete button at the top edge.** (10 min)
      Drag a bar to the very top of the stage. Is its ✕ cut off? It hangs
      outside the bar's corner (`-top-2.5`), and the stage clips what sticks
      out. Either keep bars a few pixels below the top (part of the clamp in
      F3), or move the ✕ inside the corner.

- [ ] **F8. Spinner arrows on the number inputs.** (10 min)
      The little up/down arrows are a tiny target for a finger. Hiding them
      needs plain CSS in `css/style.css`, not a Tailwind class.
      Hint: `input[type="number"]::-webkit-inner-spin-button` and
      `::-webkit-outer-spin-button`, with `appearance: none`.

- [ ] **F9. Redundant `mx-auto`.** (2 min)
      Some elements have `mx-auto` although their flex parent already centres
      them. Remove one, check nothing moved, repeat.

- [ ] **F10. Responsive stage.** (30 min, good practice)
      The stage is `h-[35rem]`, a fixed height, which is taller than a tablet
      in landscape. You now know the proper fix from the answer key page: the
      full-height chain (`h-dvh flex flex-col` on body, `flex-1 min-h-0` down
      to the stage). Apply it here.

---

## Part 2 — Bigger pieces (design them on paper on the plane)

These need a decision before code. A plane is a good place to make it.

- [ ] **Answer key: Questions mode.** One question next to its answer, with a
      way to move between questions. Each lesson's JSON has `items`: a list
      where every entry has `section`, `number`, `questionImages` (a list) and
      `answerImages` (a list). An entry with an empty `answerImages` has no
      answer in the book. `demos/answer-key.html` is a finished version to look
      at. Sketch: where do the question numbers go? How do you switch between
      Pages and Questions?

- [ ] **Books page: a dialog when you tap a book.** (`books.html`)
      Tap a book and a dialog opens with that book's name and two choices:
      **Open** (go to the answer key for that book) and **Download** (the PDF).
      You already built one of these in `fractions.html`: `<dialog>`,
      `showModal()`, and a `<form method="dialog">` so the buttons close it.
      Things to work out:
      - Each card is an `<a>` now, so a tap goes straight to
        `answerkey.html?book=...`. Either stop that with `e.preventDefault()`,
        or change the cards to `<button>`s.
      - One dialog for all the books, not one each. So the dialog has to know
        which book was tapped: put the id on the card (`data-book="..."`) and
        read it with `dataset` in the click.
      - Open is just a link built from that id.
      - Download cannot work yet: the PDFs are not on the site (see "Book
        download page" in Part 3). Build the button anyway and leave it
        disabled until then.

- [ ] **Answer key: Hide answer.** A toggle that covers the answer half, for
      when the student can see the screen. Should it stay hidden when you move
      to the next page?

- [ ] **Number line: stepping mode.** A marker on the line and buttons to move
      it, so a student walks `3 + 5`. Open questions:
      - Jumps of 1 only, or also 10? (`47 + 36` is taught as three tens, then
        six ones.)
      - Subtraction: count back, or count UP from the smaller number and read
        the distance? The second needs a different readout.
      - What happens to a jump that crosses a row boundary?
      `demos/number-line.html` has a working version to react to.

- [ ] **Fractions: improper fractions** (`9/8`). What do you draw on a
      whiteboard for it? One longer bar, or a full bar plus a part? Build that.

- [ ] **Fractions: mixed numbers** (`20/3` shows `6.666…`, want `6 2/3`).
      Needs real fraction arithmetic: keep numerator and denominator, reduce
      with a GCD, no decimals.

- [ ] **Fractions: large denominators.** At `1/20` each piece is about 12px
      wide and the label does not fit; at `1/100` it is about 2px. Bars must
      stay the same width (that is what makes them comparable), so the labels
      have to give. Options: drop the label and keep the total above, shrink
      the text past some number, or show tick marks instead of boxes.

- [ ] **Fractions: one drag function for bars and chips.** `addBar` and
      `addNumber` carry nearly the same drag code. A `makeDraggable(el)` was
      started and dropped; the blocker was passing in a function for "what a
      tap means" (a callback). You have since passed functions to
      `addEventListener` and `forEach` many times, which is the same idea:
      `makeDraggable(bar, (tapped) => { ...shade it... })`.

- [ ] **Fractions: scrolling versus dragging.** The stage has `touch-none`, so
      a finger cannot scroll it, and `overflow-auto`, so it can grow
      scrollbars. Pick one: a fixed canvas that never scrolls (then clamp bars
      inside it, F3), or a scrolling one (then only bars get `touch-none`).

- [ ] **Fractions: show the ✕ only on the selected bar** (the Canva idea).
      Pressing a bar selects it; its ✕ appears and every other bar's hides.
      `hidden` is the class; use `add` / `remove`, not `toggle`.

- [ ] **Fractions: snap bars so left edges line up**, for exact comparing.
      On release, if the bar's left is within a few pixels of another bar's
      left, set it equal.

- [ ] **Fractions: duplicate a bar.**

- [ ] **Fractions: keep bars after a refresh** (`localStorage`). Needs the
      bars to exist as data (numerator, denominator, position, which pieces
      are shaded), not only as elements on the page.

- [ ] **Next tool: percentages.** A percentage bar is a fraction bar with 100
      pieces and different labels, so the large-denominator problem above is
      the first thing to solve. It is also the first real chance to see which
      parts of `js/fractions.js` belong in a file both pages share.
      Other tool ideas (metric unit converter) are in `ideas.md`.

---

## Part 3 — Needs internet, a tablet, or Claude

- [ ] **Try the answer key on the Fire HD**, both orientations.
- [ ] **Use the fraction tool with a real student once.**
- [ ] **Decide where the book images go** so the answer key works on the live
      site. Agreed plan, not started: a second Vercel site holding only `data/`
      and `assets/books/`, and one base-address constant in `js/answerkey.js`.
      Until then the live answer key page shows no pictures.
- [ ] **Test the scanner on a second book** (Claude).
- [ ] **Rename the book id** to carry publisher and title, when the second book
      arrives. Today it is `mhr-grade-9`.
- [ ] **`data/books.json`** and a **book selector page** (`books.html`). The
      answer key learns which book from its link: `answerkey.html?book=<id>`,
      read with `URLSearchParams`.
- [ ] **Book download page.** Listing each book with a link to its PDF. Two
      questions first: where the PDFs are hosted (`books/` is not on GitHub or
      Vercel), and whether the centre's licence allows sharing the files. Keep
      it off the public site unless it does.
- [ ] **Keep Tailwind in the project** so pages work offline: save the script
      as `js/vendor/tailwind.js` and point each page's script tag at it.
- [ ] Delete `js/fractions-demo.js` and `docs/answer-key-sample.json`; nothing
      uses them.

---

## If you get stuck (things you already worked out)

**Nothing happens and no error.** Put a `console.log` at the top of the
function. If it does not print, the function never ran; the problem is whoever
was supposed to call it.

**`Cannot read properties of undefined`.** The thing before the dot is
`undefined`. Log it on the line above. Usual causes: a variable that was never
filled, or a parameter with the same name as an outer variable hiding it.

**A box will not scroll.** Every flex box between it and the thing with a real
height needs `min-h-0`. One greedy box in the chain and nothing below it
shrinks. The scrolling box also needs `overflow-auto`.

**One click does the job twice.** A listener was added more than once.
`addEventListener` never replaces, it always adds. Listeners on things that
already exist go at the top level of the file, once.

**Data is `undefined` right after `fetch`.** Code after an `await` runs later.
Anything that needs the data must be inside the `async` function, or called
from it after the `await`.

**A Tailwind class does nothing.** If the class name only ever appears at
runtime (added with `classList`), Tailwind may never have written its CSS. Use
`element.style` for anything that must apply on that exact line.

**Text and numbers.** Anything read from an input, a `dataset`, or a file path
is text. `Number(...)` before doing arithmetic. `"9" < "20"` is false.

**Check the syntax without a browser:** `node --check js/answerkey.js`
prints nothing when the file is fine, and a line number when it is not.

**Made a mess?** `git status` shows what changed. `git restore js/answerkey.js`
puts one file back to the last commit. Commit small working steps so there is
always something to go back to: `git add -A` then `git commit -m "what works now"`.
