"""
Build a page for checking crops by eye.

Each crop is shown next to the full page it was cut from, with a red box
marking the cut. Press Y if it is right, N if it is wrong.

    python tools/review.py mhr-grade-9 1 answers
    python tools/review.py mhr-grade-9 1 questions

Then open  tools/review/index.html  in a browser.

Everything it writes goes in tools/review/, which is not committed.
"""

import io
import json
import sys
from pathlib import Path

import fitz
from PIL import Image

import extract

book_id = sys.argv[1] if len(sys.argv) > 1 else "mhr-grade-9"
chapter = sys.argv[2] if len(sys.argv) > 2 else "1"
kind = sys.argv[3] if len(sys.argv) > 3 else "answers"
if kind not in ("answers", "questions"):
    sys.exit("third argument must be 'answers' or 'questions'")

# Re-run the extractor so the crops on disk and the recorded positions match.
extract.run(book_id, chapter)

book = extract.BOOKS[book_id]
doc = fitz.open(extract.ROOT / book["pdf"])

out = extract.ROOT / "tools" / "review"
pages_dir = out / "pages"
pages_dir.mkdir(parents=True, exist_ok=True)

if kind == "answers":
    records = [(lesson, name, index, clip) for lesson, name, index, clip in extract.ANSWER_AUDIT]
else:
    records = [(r[0], r[1], r[2], r[3]) for r in extract.AUDIT]

items = []
rendered = set()
for lesson, name, index, clip in records:
    page = doc[index]
    page_file = f"p{index + 1}.webp"
    if index not in rendered:
        pix = page.get_pixmap(dpi=110)
        image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        image.save(pages_dir / page_file, "WEBP", quality=75)
        rendered.add(index)

    w, h = page.rect.width, page.rect.height
    items.append({
        "lesson": lesson,
        "name": name,
        "crop": f"../../assets/books/{book_id}/{kind}/{name}",
        "page": f"pages/{page_file}",
        "pdfPage": index + 1,
        # where the crop sits on the page, as percentages
        "box": [round(clip.x0 / w * 100, 2), round(clip.y0 / h * 100, 2),
                round(clip.width / w * 100, 2), round(clip.height / h * 100, 2)],
    })

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Crop review</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, sans-serif; background: #f5f5f4; color: #1e293b;
         height: 100vh; display: flex; flex-direction: column; }
  header { padding: 10px 16px; background: #fff; border-bottom: 1px solid #e2e8f0;
           display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
  header b { font-size: 18px; }
  .name { font-family: monospace; font-size: 14px; }
  .pill { padding: 2px 10px; border-radius: 999px; font-size: 13px; font-weight: 600; }
  .yes { background: #dcfce7; color: #166534; }
  .no  { background: #fee2e2; color: #991b1b; }
  .none { background: #e2e8f0; color: #475569; }
  main { flex: 1; min-height: 0; display: flex; gap: 12px; padding: 12px; }
  .pane { flex: 1; min-width: 0; background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
          display: flex; flex-direction: column; }
  .pane h2 { margin: 0; padding: 8px 14px; font-size: 12px; letter-spacing: .08em;
             text-transform: uppercase; color: #94a3b8; border-bottom: 1px solid #e2e8f0; }
  .scroll { flex: 1; min-height: 0; overflow: auto; padding: 14px; }
  #crop { max-width: 100%; border: 2px solid #ef4444; }
  #pageWrap { position: relative; }
  #page { width: 100%; display: block; }
  #box { position: absolute; border: 3px solid #ef4444; background: rgba(239,68,68,.10); }
  footer { padding: 10px 16px; background: #fff; border-top: 1px solid #e2e8f0;
           display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  button { font: inherit; padding: 8px 18px; border-radius: 10px; border: 1px solid #cbd5e1;
           background: #fff; cursor: pointer; }
  button.good { background: #16a34a; color: #fff; border-color: #16a34a; }
  button.bad  { background: #dc2626; color: #fff; border-color: #dc2626; }
  kbd { background: #e2e8f0; border-radius: 4px; padding: 1px 6px; font-size: 12px; }
  #summary { margin-left: auto; font-size: 14px; }
  #done { display: none; padding: 24px; overflow: auto; }
  #done textarea { width: 100%; height: 220px; font-family: monospace; font-size: 13px; }
</style>
</head>
<body>

<header>
  <b id="count"></b>
  <span class="name" id="name"></span>
  <span class="pill none" id="verdict">not checked</span>
  <span id="summary"></span>
</header>

<main id="main">
  <section class="pane">
    <h2>The crop</h2>
    <div class="scroll"><img id="crop" alt="crop"></div>
  </section>
  <section class="pane">
    <h2 id="pageTitle">The page it came from</h2>
    <div class="scroll" id="pageScroll">
      <div id="pageWrap"><img id="page" alt="page"><div id="box"></div></div>
    </div>
  </section>
</main>

<div id="done">
  <h2>Finished</h2>
  <p id="doneLine"></p>
  <p>The ones you marked wrong &mdash; copy this and send it over:</p>
  <textarea id="wrongList" readonly></textarea>
  <p><button id="backBtn">Go back through them</button></p>
</div>

<footer>
  <button class="good" id="yesBtn">Yes, correct <kbd>Y</kbd></button>
  <button class="bad" id="noBtn">No, wrong <kbd>N</kbd></button>
  <button id="prevBtn">&larr; Back <kbd>&larr;</kbd></button>
  <button id="nextBtn">Skip <kbd>&rarr;</kbd></button>
  <button id="wrongBtn">Show wrong list</button>
  <button id="resetBtn">Start over</button>
</footer>

<script>
const ITEMS = __ITEMS__;
const KEY = "crop-review:__KEY__";

// Answers survive a refresh or closing the tab.
let verdicts = {};
try { verdicts = JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) {}

// Start at the first one not checked yet.
let at = ITEMS.findIndex(it => !(it.name in verdicts));
if (at === -1) at = 0;

const $ = id => document.getElementById(id);

function save() {
  try { localStorage.setItem(KEY, JSON.stringify(verdicts)); } catch (e) {}
}

function wrongNames() {
  return ITEMS.filter(it => verdicts[it.name] === "no").map(it => it.name);
}

function show() {
  $("done").style.display = "none";
  $("main").style.display = "flex";

  const it = ITEMS[at];
  $("count").textContent = (at + 1) + " / " + ITEMS.length;
  $("name").textContent = it.name;
  $("pageTitle").textContent = "The page it came from (PDF page " + it.pdfPage + ")";

  const v = verdicts[it.name];
  const pill = $("verdict");
  pill.textContent = v === "yes" ? "marked correct" : v === "no" ? "marked WRONG" : "not checked";
  pill.className = "pill " + (v || "none");

  const yes = Object.values(verdicts).filter(x => x === "yes").length;
  const no = Object.values(verdicts).filter(x => x === "no").length;
  $("summary").textContent = yes + " correct, " + no + " wrong, " + (ITEMS.length - yes - no) + " left";

  $("crop").src = it.crop;

  const page = $("page");
  const box = $("box");
  box.style.left = it.box[0] + "%";
  box.style.top = it.box[1] + "%";
  box.style.width = it.box[2] + "%";
  box.style.height = it.box[3] + "%";

  // Scroll the page so the red box is in view, once the image has a height.
  const place = () => {
    const wrap = $("pageWrap");
    const y = wrap.offsetHeight * it.box[1] / 100;
    $("pageScroll").scrollTop = Math.max(0, y - 80);
  };
  if (page.getAttribute("src") === it.page && page.complete) {
    place();
  } else {
    page.onload = place;
    page.src = it.page;
  }
}

function finish() {
  $("main").style.display = "none";
  $("done").style.display = "block";
  const wrong = wrongNames();
  const unchecked = ITEMS.filter(it => !(it.name in verdicts)).length;
  $("doneLine").textContent = ITEMS.length + " crops: " + wrong.length + " marked wrong, "
                            + unchecked + " not checked.";
  $("wrongList").value = wrong.length ? wrong.join("\n") : "(none marked wrong)";
}

function mark(v) {
  verdicts[ITEMS[at].name] = v;
  save();
  if (at < ITEMS.length - 1) { at++; show(); } else { finish(); }
}

function move(step) {
  at = Math.min(ITEMS.length - 1, Math.max(0, at + step));
  show();
}

$("yesBtn").onclick = () => mark("yes");
$("noBtn").onclick = () => mark("no");
$("prevBtn").onclick = () => move(-1);
$("nextBtn").onclick = () => move(1);
$("wrongBtn").onclick = finish;
$("backBtn").onclick = show;
$("resetBtn").onclick = () => {
  if (confirm("Clear every answer and start again?")) { verdicts = {}; save(); at = 0; show(); }
};

document.addEventListener("keydown", e => {
  if (e.target.tagName === "TEXTAREA") return;
  const k = e.key.toLowerCase();
  if (k === "y") mark("yes");
  else if (k === "n") mark("no");
  else if (e.key === "ArrowLeft") move(-1);
  else if (e.key === "ArrowRight") move(1);
});

show();
</script>
</body>
</html>
"""

html = (HTML.replace("__ITEMS__", json.dumps(items))
            .replace("__KEY__", f"{book_id}:{chapter}:{kind}"))
(out / "index.html").write_text(html, encoding="utf-8")

print(f"\n{len(items)} {kind} crops, {len(rendered)} pages")
print(f"open: {out / 'index.html'}")
