# Answer Key — Wishlist

**The open tasks are collected in `docs/todo.md` — work from that one.** This file keeps the history and the reasons.

Tasks for `answerkey.html` + `js/answerkey.js`.
The data it reads is in `data/mhr-grade-9/`, one JSON file per lesson.

---

## Done

- [x] Top half / bottom half layout, each half scrolling on its own
      (`min-h-0` on the pane AND on the image box, or nothing scrolls)
- [x] Load a lesson's JSON with `fetch` inside an `async` function
- [x] Show the first lesson page and the first answer page from the data
- [x] Page number in each title, read from the image path (`pageNumber()`)
- [x] ← → buttons for the question half, stopping at the first and last page
- [x] ← → buttons for the answer half, with its own index
- [x] Listeners at the top level, so loading another lesson will not stack them
- [x] Both indexes go back to 0 when a lesson loads
- [x] `loadLesson(path)` takes the lesson's file instead of having it typed in
- [x] Lesson picker: a dropdown filled from `data/mhr-grade-9/index.json`,
      built as one string and set once; choosing a lesson loads it
- [x] The page opens on the lesson the dropdown shows
- [x] Picker grouped by chapter with `<optgroup>`: remember the current chapter,
      open a new group when it changes, close the last one after the loop

---

## Good plane tasks (no internet needed)

Live Server works offline. Tailwind comes from a CDN, so load the page once
before you lose the connection and keep the tab open, or the styling will not load.

- [ ] **Scroll back to the top when the page changes.**
      Try it: scroll a page half-way down, press →. The new page opens half-way
      down too, because the box kept its scroll position.
      The box that scrolls is the `div` around the `<img>`, not the image.
      A box knows how far it has been scrolled; you used that property in the
      fraction drag code. Setting it puts the box where you want.
      Do it for both halves.

- [ ] **Show when a button has nowhere to go.**
      On the first page ← does nothing, and nothing on screen says why. Same for →
      on the last page. Most lessons have a single answer page, so both answer
      buttons are dead most of the time.
      Target: a button that cannot move looks faded and cannot be pressed.
      Buttons have a property for "cannot be pressed", and Tailwind has a variant
      that styles a button while it is in that state.
      Think about WHEN this has to be worked out: after every press, and also when
      a lesson first loads. That points at one function that sets all four buttons.

- [ ] **Safety net: a lesson with no pages.**
      `lesson.pageImages[0]` assumes the list has at least one page. If a list is
      empty, `[0]` is `undefined`, `pageNumber(undefined)` throws, and the code
      stops there - so the answer half never loads either.
      No lesson in this book is empty any more (8.3 was, until its pages were
      added), so you will not see it happen today. A second book with a gap
      would bring it back.
      Target: when a list is empty, that half shows a short message such as
      "No pages for this lesson" and the other half still loads.
      A list tells you how many items it has with `.length`.
      To test it without a broken lesson: open DevTools, and after a lesson has
      loaded type `lesson.pageImages = []` in the console, then call whatever
      shows the first page. Or temporarily make a copy of a lesson file with an
      empty `pageImages` list and load that.
      Check both lists: `pageImages` and `answerPageImages`.

- [ ] **Tidy `updatePage(page, num, img)`.** Inside it, `page` is the `<img>`,
      `num` is the title and `img` is a path. Rename them to what they are.

- [ ] **The four button listeners are nearly the same code.** Not urgent. Only
      worth merging if you can see a way that is still easy to read.

---

## Next

- [ ] **Tidy the picker's labels.** Entries like `1.0 Get Ready` and
      `1.R Chapter 1 Review` show ids that were made up for the file names, not
      numbers from the book. Show the number only for real lessons (1.1, 1.2...).
- [ ] **Bigger buttons.** `h-[2rem]` is small for a finger. The fraction page
      uses `h-11`.
- [ ] **Questions mode.** One question next to its answer, using `items` in the
      JSON. `demos/answer-key.html` shows the target.
- [ ] **Hide answer** toggle, for when the student can see the screen.
- [ ] Try it on the Fire HD in both orientations.
