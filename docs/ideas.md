# Tool ideas

Tools not started yet. Per-tool task lists live in their own file
(e.g. `fractions-todo.md`) once work actually begins.

---

## Metric unit converter

Added 2026-10-06.

**The problem:** kids struggle to convert between metric units, and drawing the
staircase by hand every time is slow and gets messy.

**The picture:** the standard prefix strip, biggest on the left:

```
Kilo  Hecto  Deca  Metre  Deci  Centi  Milli
```

**The rule to teach:** moving one place **left** multiplies by 10, moving one place
**right** divides by 10. That is the whole idea — the decimal point walks along the strip.

**Not designed yet.** Open questions for when it gets picked up:
- Does the student drag a value along the strip, or tap a start and an end unit?
- Does the number update live as it moves, so they see `1.5 m` become `150 cm`?
- Show the hop arcs with `×10` on them, like the number line already does?
- Does it cover length only, or mass and volume too (same prefixes, different base unit)?
- Where does the decimal point go visually — is *moving the point* the thing being shown,
  or just the arithmetic?

**Reuse:** the hop arcs and the stepping buttons from the number line are the same shape.
Worth looking at `demos/number-line.html` before starting from scratch.

---

## Answer-key lookup (textbook companion)

Added 2026-10-06.

**The problem:** some students work from their own school textbook rather than the centre's
package. Finding the question takes time, then flipping to the back for the answer key takes
more. It happens many times per session.

**The wish:** the book on screen, tap a question, the answer appears.

### What is actually hard

Not the PDF viewer. Mozilla's **PDF.js** renders a PDF to a canvas in the browser, and it is
what Firefox itself uses. Displaying `MHR GRADE 9.pdf` is an afternoon.

The hard parts are:

1. **Linking a question to its answer.** A PDF is pictures of text — nothing in it says
   "this is question 7b" or "this answer belongs to it". Something has to build that map.
   Either typed by hand, or pulled out of the answer-key pages with text extraction and a
   lot of cleaning. Realistically: one chapter at a time, by hand, as needed.

2. **Clickable regions.** To tap a question you need to know where it sits on the page —
   x, y, width, height per question. That is manual work per page unless the layout is very
   regular.

### Copyright — the real blocker

The PDF is a published textbook. Putting it on a public site (Vercel, GitHub) is
distribution, regardless of intent, and that is the part that could actually cause trouble.
It is a different thing from using the book in a session.

`books/` is currently NOT tracked by git. Keep it that way — add it to `.gitignore` so it is
never pushed by accident.

If this gets built, keep it local-only (open the page from disk), or behind a login that
only staff can reach. Do not deploy the PDF.

### A much smaller version that solves most of the pain

Skip the PDF entirely. A page where you type a chapter and question number and the answer
appears. The data is a JSON file of answers that grows as chapters are used.

- no PDF, no clickable regions, no copyright exposure for the book itself
- the student keeps using their own paper book, which they have in front of them anyway
- can be built in an evening and improved every time a new chapter comes up

Worth doing this first and seeing whether the full version is still wanted.

### Storage

A 17MB PDF is fine for a static host — but see the copyright note; size is not the reason to
avoid it. A JSON answer file is a few KB.

### Ask-an-AI button

Added 2026-10-06.

Next to each answer, a small button that copies a ready-made prompt — the question, the
answer, and a line asking for the working — then opens ChatGPT / Gemini in a new tab so the
instructor just pastes.

For when an instructor can see the answer but not the reasoning, mid-session, with a student
waiting.

Pieces, all of which already exist elsewhere in this project:
- `navigator.clipboard.writeText(...)` — same API as the old `colors.html` swatches
- `window.open(url, "_blank")` for the new tab
- the prompt itself is a template string over the question and answer already on screen

Worth knowing: some assistants accept the prompt in the URL and prefill the box
(`chatgpt.com/?q=...`, `claude.ai/new?q=...`), which removes the paste step entirely.
Gemini has no reliable equivalent. So: copy to clipboard always, and prefill where the
site supports it.

Needs the question text, not just its number — so it depends on the text layer from the
step above, or on the answer JSON carrying the question text too.
