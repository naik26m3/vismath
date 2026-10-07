"""
Turn a textbook PDF into data the web app can use.

For each lesson it produces:
  - a crop of every question, straight out of the page
  - a crop of every answer, out of the two-column answers section
  - a full-page image per page, for the "Page" button
  - one JSON file describing the lesson

Nothing here is specific to one book. A new book means a new entry in BOOKS
plus its lesson list; the rest is the same.

    python tools/extract.py mhr-grade-9 1

Needs PyMuPDF:  pip install pymupdf
"""

import fitz
import io
import json
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# Books
#
# page_offset: pdf page number = book page number + page_offset
# answers_from / answers_to: where the Answers section lives, in PDF pages
# --------------------------------------------------------------------------

BOOKS = {
    "mhr-grade-9": {
        "title": "MHR Mathematics 9",
        "pdf": "books/MHR+GRADE+9.pdf",
        "page_offset": 12,
        "answers_from": 541,
        "answers_to": 585,          # p586 onward is the Glossary, then Index
        "chapters": {
            "1": [
                # id,     title,                                           book pages
                ("1.0", "Get Ready",                                        4, 5),
                ("1.1", "Focus on Problem Solving",                         6, 9),
                ("1.2", "Focus on Communicating",                          10, 13),
                ("1.3", "Focus on Connecting",                             14, 18),
                ("1.4", "Focus on Representing",                           19, 22),
                ("1.5", "Focus on Selecting Tools and Computational Strategies", 23, 28),
                ("1.6", "Focus on Reasoning and Proving",                  29, 33),
                ("1.7", "Focus on Reflecting",                             34, 36),
                ("1.R", "Chapter 1 Review",                                37, 39),
            ],
        },
    },
}

DPI_CROP = 150
DPI_PAGE = 120

# WebP instead of PNG. These are crops of printed text, so the difference is
# invisible and the files are roughly five times smaller — which matters both
# for what gets deployed and for a tablet on centre wi-fi.
IMAGE_EXT = ".webp"
WEBP_QUALITY = 80


def save(pixmap, path):
    """Write a pixmap as WebP."""
    image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    image.save(path, "WEBP", quality=WEBP_QUALITY, method=6)


# The headings that start a new run of question numbers. The book restarts at 1
# under each of these, so a question is only identified by section + number.
SECTION_HEADINGS = [
    "Questions",            # not a printed heading - see default_section()
    "Investigate A", "Investigate B", "Investigate",
    "Communicate Your Understanding",
    "Practise", "Connect and Apply", "Extend",
    "Achievement Check", "Chapter Problem", "Chapter Problem Wrap-Up",
    "Use Technology", "Math Contest",
]

# The answer key numbers only the exercise run, and that run is continuous
# across these headings (Practise 1-4, Connect and Apply 5-9, Extend 10-11).
# Investigate restarts at 1 and has no entry in the key.
EXERCISE_SECTIONS = {
    "Questions",
    "Practise", "Connect and Apply", "Extend",
    "Achievement Check", "Chapter Problem", "Chapter Problem Wrap-Up",
    "Math Contest",
}

# A question starts with "N." near the left edge of its column. Parts a) b) c)
# are indented further, so the x position is what tells them apart.
QUESTION_RE = re.compile(r'^(\d+)\.(?!\d)')


def blocks_of(page, clip=None):
    """Text blocks, in reading order, as (x0, y0, x1, y1, text)."""
    out = []
    for b in page.get_text("blocks", clip=clip):
        text = b[4].strip()
        if text:
            out.append((b[0], b[1], b[2], b[3], text))
    out.sort(key=lambda b: (round(b[1], 1), b[0]))
    return out


def question_starts(blocks, left_edge, indent_tolerance=14):
    """The blocks that begin a numbered question, as (number, y)."""
    starts = []
    for x0, y0, _, _, text in blocks:
        m = QUESTION_RE.match(text)
        if m and x0 <= left_edge + indent_tolerance:
            starts.append((m.group(1), y0, x0))
    return starts


# --------------------------------------------------------------------------
# Questions: lesson pages, single column
# --------------------------------------------------------------------------

def lines_of(page):
    """Text lines, top to bottom, as (x0, y0, x1, y1, text)."""
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"]).strip()
            if text:
                out.append((*line["bbox"], text))
    out.sort(key=lambda l: (round(l[1], 1), l[0]))
    return out


def default_section(title):
    """
    The section a question belongs to before any heading has been seen.
    Get Ready, Chapter Review and Chapter Test print no headings at all and are
    nothing but exercises; ordinary lessons open with Investigate.
    """
    if re.search(r'Get Ready|Review|Test', title, re.I):
        return "Questions"
    return "Investigate"


def crop_questions(doc, book, lesson, out_dir, rel_dir):
    """Crop every numbered question on the lesson's pages."""
    lesson_id, title, first_page, last_page = lesson
    offset = book["page_offset"]
    found = {}
    # A section can run over a page break, so the last heading seen carries
    # forward to the top of the next page.
    carried = {"section": default_section(title)}
    used = set()

    for book_page in range(first_page, last_page + 1):
        index = book_page + offset - 1
        if index < 0 or index >= doc.page_count:
            continue
        page = doc[index]
        rect = page.rect
        bottom_limit = rect.height - 45

        body = [l for l in lines_of(page) if 40 < l[1] < bottom_limit]
        if not body:
            continue

        candidates = [(l, QUESTION_RE.match(l[4])) for l in body]
        candidates = [(l, m) for l, m in candidates if m]
        if not candidates:
            continue

        # Get Ready, Chapter Review and Chapter Test are laid out in two
        # columns, like the answers. If the question numbers sit at two very
        # different x positions, split the page at its gutter and treat each
        # half as its own column.
        xs = [l[0] for l, _ in candidates]
        if max(xs) - min(xs) > rect.width * 0.3:
            middle = column_split(page)
            columns = [fitz.Rect(rect.x0, 0, middle, rect.y1),
                       fitz.Rect(middle, 0, rect.x1, rect.y1)]
        else:
            columns = [fitz.Rect(rect.x0, 0, rect.x1, rect.y1)]

        # Where each section heading sits, so a question knows which run of
        # numbering it belongs to.
        heading_positions = []
        for _, y0, _, _, text in body:
            flat = " ".join(text.split())
            for name in SECTION_HEADINGS:
                if flat.startswith(name):
                    heading_positions.append((y0, name))
                    break

        def section_at(y):
            current = carried["section"]
            for hy, name in heading_positions:
                if hy <= y:
                    current = name
            return current

        for column in columns:
            in_column = [(l, m) for l, m in candidates if column.x0 <= l[0] < column.x1]
            if not in_column:
                continue

            # The indent is measured from the question numbers, not from the
            # leftmost text: sidebars and margin notes sit further left, and the
            # layout shifts between odd and even pages.
            indent = min(l[0] for l, _ in in_column)
            starts = [(m.group(1), l[1], l[0]) for l, m in in_column if l[0] <= indent + 12]
            starts.sort(key=lambda s: s[1])

            for i, (number, top, x0) in enumerate(starts):
                end = starts[i + 1][1] if i + 1 < len(starts) else bottom_limit
                right = column.x1 - (8 if len(columns) > 1 else 30)
                clip = fitz.Rect(max(column.x0, x0 - 18), top - 8,
                                 right, min(end - 4, bottom_limit))
                if clip.height < 12:
                    continue

                section = section_at(top)
                slug = re.sub(r'[^a-z0-9]+', '-', section.lower()).strip('-')
                # Two Investigate runs in one lesson both have a question 1, so
                # the name carries the page and, if needed, a counter.
                base = f"{lesson_id}-{slug}-p{book_page}-q{number}"
                name = f"{base}{IMAGE_EXT}"
                n = 2
                while name in used:
                    name = f"{base}-{n}{IMAGE_EXT}"
                    n += 1
                used.add(name)

                save(page.get_pixmap(dpi=DPI_CROP, clip=clip), out_dir / name)
                found.setdefault((section, number), []).append(f"{rel_dir}/{name}")

        if heading_positions:
            carried["section"] = heading_positions[-1][1]

    return found


# --------------------------------------------------------------------------
# Answers: two columns, one long run across several pages
# --------------------------------------------------------------------------

def answer_segments(doc, book):
    """
    The Answers section, line by line, in reading order:
    (page_index, column_rect, y0, x0, text).

    Lines, not blocks: PyMuPDF merges a whole run of answers into one block,
    so block-level segmentation cannot see where answer 2 starts.
    """
    segments = []
    for index in range(book["answers_from"] - 1, min(book["answers_to"], doc.page_count)):
        page = doc[index]
        rect = page.rect
        middle = column_split(page)

        for column in (fitz.Rect(rect.x0, rect.y0, middle, rect.y1),
                       fitz.Rect(middle, rect.y0, rect.x1, rect.y1)):
            lines = []
            for block in page.get_text("dict", clip=column)["blocks"]:
                for line in block.get("lines", []):
                    text = "".join(span["text"] for span in line["spans"]).strip()
                    if text:
                        x0, y0 = line["bbox"][0], line["bbox"][1]
                        lines.append((index, column, y0, x0, text))
            lines.sort(key=lambda l: l[2])
            segments.extend(lines)
    return segments


# How far a question number may sit from the column's left edge. Answers are
# indented about 79px; parts (a, b, c) sit further in again.
ANSWER_INDENT = 95


def column_split(page):
    """
    Where the gutter between the two answer columns is, on this page.

    It moves from page to page, so it has to be measured. The gutter is the one
    vertical strip that no line of text crosses: scan across the middle of the
    page, count how many lines span each x, and take the centre of the longest
    run where that count is lowest (zero, on a normal page).
    """
    rect = page.rect
    top, bottom = rect.y0 + 50, rect.y1 - 50          # ignore header / footer
    spans = [(line["bbox"][0], line["bbox"][2])
             for block in page.get_text("dict")["blocks"]
             for line in block.get("lines", [])
             if top < line["bbox"][1] < bottom]

    low = int(rect.x0 + rect.width * 0.30)
    high = int(rect.x0 + rect.width * 0.70)
    counts = [sum(1 for x0, x1 in spans if x0 < x < x1) for x in range(low, high)]
    if not counts:
        return (rect.x0 + rect.x1) / 2

    fewest = min(counts)
    best_start, best_len, run_start = low, 0, None
    for i, c in enumerate(counts + [fewest + 1]):        # sentinel ends last run
        if c == fewest and run_start is None:
            run_start = i
        elif c != fewest and run_start is not None:
            if i - run_start > best_len:
                best_start, best_len = run_start, i - run_start
            run_start = None

    return low + best_start + best_len / 2


def crop_answers(doc, book, lesson, segments, out_dir, rel_dir, all_ids):
    """Crop each numbered answer belonging to one lesson."""
    lesson_id, title, _, _ = lesson

    # Headings are not written consistently: "1.1 Focus on Problem Solving",
    # "Get Ready" with no number, "Chapter 1 Review", and sometimes the number
    # wraps onto a line by itself. Try each shape.
    patterns = [
        re.compile(r'^%s\s+%s' % (re.escape(lesson_id), re.escape(title[:26])), re.I),
        re.compile(r'^%s\s*,' % re.escape(title[:26]), re.I),
        re.compile(r'^%s\s*$' % re.escape(lesson_id)),
    ]
    # Where this lesson's answers end. Built from the real lesson ids rather
    # than a generic "N.N", because answers contain decimals like "0.3" and
    # "1.5" that would otherwise look like the next heading.
    others = [re.escape(i) for i in all_ids if i != lesson_id]
    next_heading = re.compile(
        r'^(?:' + '|'.join(others) + r')\s*(?:[A-Z]|$)'
        r'|^Chapter \d+ (?:Review|Test)'
        r'|^Chapter \d+\s*$'
        r'|^Get Ready')

    start_at = None
    for pattern in patterns:
        for i, (_, _, _, _, text) in enumerate(segments):
            if pattern.match(text):
                start_at = i
                break
        if start_at is not None:
            break
    if start_at is None:
        return {}

    stop_at = len(segments)
    for i in range(start_at + 1, len(segments)):
        if next_heading.match(segments[i][4]):
            stop_at = i
            break

    mine = segments[start_at + 1:stop_at]

    starts = []
    for i, (index, column, y0, x0, text) in enumerate(mine):
        m = QUESTION_RE.match(text)
        if m and x0 <= column.x0 + ANSWER_INDENT:
            starts.append((m.group(1), i))

    found = {}
    for n, (number, position) in enumerate(starts):
        index, column, y0, number_x, _ = mine[position]

        if n + 1 < len(starts):
            end_index, end_column, end_y, _, _ = mine[starts[n + 1][1]]
        else:
            end_index, end_column, end_y = mine[-1][0], mine[-1][1], mine[-1][2] + 14

        # Crop inside the column the answer starts in. If the next answer is in
        # a different column or on another page, run to the bottom of this one.
        same = (end_index == index and end_column == column)
        bottom = (end_y - 3) if same else (doc[index].rect.height - 40)

        # Text runs a little past the halfway line, so widen the crop beyond
        # the column used for finding things, or words get cut off the right.
        page_right = doc[index].rect.x1
        # Start just left of the number itself; a fixed inset cuts it off on
        # pages where the answers sit closer to the column edge.
        clip = fitz.Rect(max(column.x0 + 4, number_x - 14), y0 - 7,
                         min(column.x1 + 26, page_right - 6), bottom)
        if clip.height < 10:
            continue

        name = f"{lesson_id}-a{number}{IMAGE_EXT}"
        save(doc[index].get_pixmap(dpi=DPI_CROP, clip=clip), out_dir / name)
        found.setdefault(number, []).append(f"{rel_dir}/{name}")

    return found


# --------------------------------------------------------------------------

def run(book_id, chapter):
    book = BOOKS[book_id]
    doc = fitz.open(ROOT / book["pdf"])

    asset_root = ROOT / "assets" / "books" / book_id
    q_dir = asset_root / "questions"
    a_dir = asset_root / "answers"
    p_dir = asset_root / "pages"
    for d in (q_dir, a_dir, p_dir):
        d.mkdir(parents=True, exist_ok=True)

    data_dir = ROOT / "data" / book_id
    data_dir.mkdir(parents=True, exist_ok=True)

    rel = f"assets/books/{book_id}"
    segments = answer_segments(doc, book)
    all_ids = [l[0] for l in book["chapters"][chapter]]

    for lesson in book["chapters"][chapter]:
        lesson_id, title, first_page, last_page = lesson

        questions = crop_questions(doc, book, lesson, q_dir, f"{rel}/questions")
        answers = crop_answers(doc, book, lesson, segments, a_dir, f"{rel}/answers", all_ids)

        # full pages, for the "show the page" button
        pages = []
        for book_page in range(first_page, last_page + 1):
            index = book_page + book["page_offset"] - 1
            if 0 <= index < doc.page_count:
                name = f"p{index + 1}{IMAGE_EXT}"
                target = p_dir / name
                if not target.exists():
                    save(doc[index].get_pixmap(dpi=DPI_PAGE), target)
                pages.append(f"{rel}/pages/{name}")

        # Numbering restarts under each heading, so a question is identified by
        # section AND number. The answer key does not repeat the headings, so
        # its numbers are matched to the last section that has that number -
        # usually the main exercise set. Marked so the app can show the doubt.
        sections = {}
        for (section, number), images in questions.items():
            sections.setdefault(section, {})[number] = images

        items = []
        for section in SECTION_HEADINGS:
            if section not in sections:
                continue
            for number in sorted(sections[section], key=int):
                in_exercises = section in EXERCISE_SECTIONS
                items.append({
                    "section": section,
                    "number": number,
                    "questionImages": sections[section][number],
                    "answerImages": answers.get(number, []) if in_exercises else [],
                    "hasAnswerKey": in_exercises,
                })

        out = {
            "book": book_id,
            "bookTitle": book["title"],
            "chapter": chapter,
            "lesson": lesson_id,
            "title": title,
            "bookPages": [first_page, last_page],
            "pageImages": pages,
            "items": items,
        }

        path = data_dir / f"{lesson_id}.json"
        path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"{lesson_id:5s} {title[:42]:42s} "
              f"questions {len(questions):3d}  answers {len(answers):3d}")


if __name__ == "__main__":
    book_id = sys.argv[1] if len(sys.argv) > 1 else "mhr-grade-9"
    chapter = sys.argv[2] if len(sys.argv) > 2 else "1"
    run(book_id, chapter)
