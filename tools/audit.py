"""
Check the question crops for text that was left out of every crop.

For each crop, look at the text lines in the same column between where the
crop stops and where the next question starts. Headings and sidebars are
expected to land there; anything else is probably part of the question that
got cut off.

    python tools/audit.py mhr-grade-9 1
"""
import sys
import fitz
import extract

book_id = sys.argv[1] if len(sys.argv) > 1 else "mhr-grade-9"
chapter = sys.argv[2] if len(sys.argv) > 2 else "1"

extract.run(book_id, chapter)
doc = fitz.open(extract.ROOT / extract.BOOKS[book_id]["pdf"])

SIDEBARS = ("Literac", "Connections", "Did You Know", "Making", "Tools",
            "Refer to", "Communicate", "Key Concepts", "Achievement", "Chapter Problem",
            "Reflect", "Investigate", "Example", "Solution", "Connect and Apply",
            "Extend", "Practise", "For help with")

problems = 0
for lesson, name, index, clip, cx0, cx1, end in extract.AUDIT:
    page = doc[index]
    for x0, y0, x1, y1, text in extract.lines_of(page):
        if not (cx0 <= x0 < cx1):
            continue
        # Must sit wholly between this crop and the next question. A line that
        # overlaps the next question's first line (a superscript lifts it a
        # little) belongs to that question, not this one.
        if not (clip.y1 < y0 and y1 < end + 2 and y0 < end - 2):
            continue
        if text.startswith(SIDEBARS) or len(text.strip()) < 2:
            continue
        print(f"{name:42s} left out: {text[:55]!r}")
        problems += 1
        break

print(f"\n{len(extract.AUDIT)} crops checked, {problems} with text left out")
