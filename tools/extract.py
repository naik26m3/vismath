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

# Every question crop, as (lesson, file, page_index, clip, column_x0, column_x1,
# next_question_y). Lets an audit find text that ended up in no crop at all.
AUDIT = []

DPI_CROP = 150
DPI_PAGE = 120

# WebP instead of PNG. These are crops of printed text, so the difference is
# invisible and the files are roughly five times smaller — which matters both
# for what gets deployed and for a tablet on centre wi-fi.
IMAGE_EXT = ".webp"
WEBP_QUALITY = 80


def save(pixmap, path, clip=None, blank=()):
    """
    Write a pixmap as WebP.

    `blank` is a list of page rectangles to paint white first - headings and
    "For help with..." lines that share a row with something the crop needs,
    so the rectangle cannot simply stop above them.
    """
    image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
    if clip is not None and blank:
        from PIL import ImageDraw
        draw = ImageDraw.Draw(image)
        sx = image.width / clip.width
        sy = image.height / clip.height
        for r in blank:
            box = r & clip
            if box.is_empty:
                continue
            draw.rectangle([(box.x0 - clip.x0) * sx - 2, (box.y0 - clip.y0) * sy - 2,
                            (box.x1 - clip.x0) * sx + 2, (box.y1 - clip.y0) * sy + 2],
                           fill="white")
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

# Some lessons split their Investigate into parts headed "A: Pentominoes",
# "B: Sums of cubes". Numbering restarts at 1 in each part.
PART_HEADING = re.compile(r'^([A-D]):\s+[A-Z]')


def section_heading_name(text):
    """The section a heading line opens, or None if it isn't one."""
    flat = " ".join(text.split())
    if len(flat) < 70:
        m = PART_HEADING.match(flat)
        if m:
            return f"Investigate {m.group(1)}"
    for name in SECTION_HEADINGS:
        if name != "Questions" and flat.startswith(name):
            return name
    return None


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


# The step tabs printed beside Investigate questions in the problem-solving
# lessons. They are labels for the page, not part of any question.
BANNER_LABELS = {"Understand the Problem", "Choose a Strategy",
                 "Carry Out the Strategy", "Reflect", "Look Back"}

# Words in a question that point at a picture. A photo in the margin is only
# taken as part of the question when the question refers to it - otherwise it
# is decoration (a snowy landscape beside a temperature question).
VISUAL_CUE = re.compile(
    r'\b(shown|shows? (?:below|at)|diagram|picture|photo|figure|map|graph|'
    r'board|illustrat\w*|labelled|pattern below|at (?:the )?(?:left|right))\b', re.I)

# A gap taller than this between two pieces of content means the question has
# ended and something else (a sidebar, a heading) has started.
CONTENT_GAP = 22


def content_extent(page, x_from, x_to, top, end, body_right=None, next_top=None,
                   single_column=True):
    """
    The real bottom and right edge of one question.

    Walks down from the question number through everything on the page in that
    column - text lines, embedded images, and vector drawings (fraction strips,
    grids, number lines are drawn, not text) - and stops at the first big gap.
    That keeps sidebars like "Literacy Connections" out of the crop without
    cutting a diagram off.
    """
    items = []                                   # (rect, text, kind)
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") == 1:
            items.append((fitz.Rect(block["bbox"]), "", "image"))
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"]).strip()
            items.append((fitz.Rect(line["bbox"]), text, "text"))
    rect = page.rect
    kept = []
    for drawing in page.get_drawings():
        r = fitz.Rect(drawing["rect"])
        # Page decoration, not content: the coloured strip down the outer
        # edge, full-width rules, and anything taller than half the page.
        if (r.width > rect.width * 0.9 or r.height > rect.height * 0.5
                or r.x0 > rect.x1 - 45 or r.x1 < rect.x0 + 45):
            continue
        items.append((r, "", "drawing"))
        kept.append(r)
    # Whole diagrams, assembled from the pieces they are drawn with. A group
    # that just traces the edge of a photo is the photo's frame, not a
    # diagram - leave it to be judged as the image it surrounds.
    images = [r for r, _, k in items if k == "image"]

    def frames_an_image(cluster):
        return any((cluster & im).get_area() > 0.8 * min(cluster.get_area(), im.get_area())
                   for im in images)

    for cluster in drawing_clusters(kept):
        if is_figure(cluster) and not frames_an_image(cluster):
            items.append((cluster, "", "figure"))

    # A stacked fraction's numerator and its brackets begin a little ABOVE the
    # question's first line, so allow a small rise - but only a small one. A
    # concept box or a page decoration also "overlaps" the question, and lets
    # the crop climb to the top of the page if nothing limits it.
    RISE = 14
    def is_heading(text):
        # Section headings, and the italic "For help with questions 3 and 4,
        # see Example 2." lines that sit between questions. Neither belongs to
        # the question above or below it.
        flat = " ".join(text.split())
        return bool(flat) and (section_heading_name(flat) is not None
                               or flat.startswith("For help with"))

    # Step tabs: drop the label and the coloured shape behind it.
    banners = [r for r, t, k in items if k == "text" and " ".join(t.split()) in BANNER_LABELS]
    def under_banner(r):
        return any(r.intersects(b + (-40, -8, 40, 8)) for b in banners)

    # Every heading the crop could reach. They are painted out afterwards, so
    # it costs nothing to list one that ends up outside the crop.
    headings = [r for r, t, k in items
                if k == "text" and is_heading(t) and x_from - 10 <= r.x0 < x_to
                and top - 150 <= r.y0 < end]
    ceiling = None

    all_items = items
    heading_bottom = max((r.y1 for r, t, k in all_items
                          if k == "text" and is_heading(t) and x_from <= r.x0 < x_to
                          and r.y0 < top), default=-1)

    def tall_figure_here(r, k):
        # A diagram can start well above the question number (a sudoku grid
        # beside the question text). If most of it lies below the number, it
        # is this question's - as long as it doesn't reach past a heading.
        # A heading beside it is fine - headings are painted out of the crop.
        return ((k in ("image", "figure") or (k == "drawing" and is_figure(r)))
                and r.y0 < top and r.y1 - top > r.height / 2
                and r.y0 >= top - 80
                and x_from <= r.x0 < x_to and r.y0 < end)

    extra = [(r, t, k) for r, t, k in items if tall_figure_here(r, k)]
    items = [(r, t, k) for r, t, k in items
             if r.x0 >= x_from and r.x0 < x_to
             and r.y0 >= top - RISE and r.y1 > top and r.y0 < end
             # a heading sitting just above this question is not part of it
             and not (k == "text" and is_heading(t) and r.y0 < top)
             # something starting right above the NEXT question number is
             # that question's figure rising above its line, not this one's
             and not (next_top is not None and r.y0 >= next_top - 12)
             and not under_banner(r)]
    items += [it for it in extra if it not in items]

    # A figure's own labels ("3.7 cm" over the hockey puck) can sit higher than
    # the question number allows for. Let them rise the same small amount
    # above the figure itself, as long as they stay below any heading.
    figures = [r for r, _, k in items if k in ("image", "figure") or (k == "drawing" and is_figure(r))]
    for fig in figures:
        for r, t, k in all_items:
            if (k == "text" and t and not is_heading(t)
                    and fig.y0 - RISE <= r.y0 < fig.y0
                    and r.x1 > fig.x0 - 10 and r.x0 < fig.x1 + 10
                    and (ceiling is None or r.y0 > ceiling)
                    and (r, t, k) not in items):
                items.append((r, t, k))

    # Past the point where question text wraps is the margin. Keep a real
    # figure there (the sudoku grid sits beside its question), drop sidebar
    # text, tab banners and the small highlight boxes around glossary terms.
    if body_right is not None:
        items = [(r, t, k) for r, t, k in items
                 if r.x0 <= body_right + 8
                 or (k in ("image", "figure") and is_figure(r) and not is_tab(r))
                 or (k == "drawing" and is_figure(r) and not is_tab(r))]

    # Figures in the outer margin to the LEFT of the question. On even pages
    # the wide margin is on the left, and a question's diagram can sit there
    # (the tangram beside question 16, the magic square beside 12). Only on
    # single-column pages - in a two-column layout, "left" is another column.
    left = None
    # Text wholly left of the question number is never part of it - a stray
    # letter from a sidebar or the margin. Paint it out of the crop.
    # x_from is 20pt left of the question number, so "ends before the number
    # starts" is x_from + 17.
    margin_text = [r for r, t, k in all_items
                   if k == "text" and t and r.x1 <= x_from + 17
                   and top - RISE <= r.y0 < end]
    if single_column:
        question_text = " ".join(t for r, t, k in all_items
                                 if k == "text" and x_from <= r.x0 < x_to and top - 2 <= r.y0 < end)
        refers_to_picture = bool(VISUAL_CUE.search(question_text))
        left_figs = [r for r, t, k in all_items
                     # drawings always (tangram, magic square); a photo only
                     # when the question points at it ("the small board shown")
                     if (k == "figure" or (k == "image" and refers_to_picture and is_figure(r)))
                     and r.x1 <= x_from + 5 and r.x0 > rect.x0 + 30
                     and top - RISE <= r.y0 < end
                     and (next_top is None or r.y0 < next_top - 12)
                     and not under_banner(r) and not is_tab(r)]
        if left_figs:
            items += [(r, "", "figure") for r in left_figs]
            left = min(r.x0 for r in left_figs)
            # ...except a margin figure's own labels (the tangram's A-G)
            margin_text = [r for r in margin_text
                           if not any(r.intersects(fg + (-4, -4, 4, 4)) for fg in left_figs)]

    items.sort(key=lambda item: item[0].y0)
    if not items:
        return top, end, x_to, headings, None

    upper = min((r.y0 for r, _, _ in items if r.y0 < top + 12), default=top)
    bottom, right = items[0][0].y1, items[0][0].x1
    for r, text, _ in items[1:]:
        # A section heading ("Extend", "Connect and Apply") ends the question
        # even when it sits close enough not to leave a gap.
        if is_heading(text):
            break
        if r.y0 - bottom > CONTENT_GAP:
            break
        bottom = max(bottom, r.y1)
        right = max(right, r.x1)
    return upper, bottom, right, headings + margin_text, left


def body_font(page):
    """
    The font the page's running text is set in: whichever font carries the
    most characters. Measured rather than named, so another book with a
    different typeface works without changes.
    """
    counts = {}
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                family = span["font"].split("-")[0]
                counts[family] = counts.get(family, 0) + len(span["text"].strip())
    return max(counts, key=counts.get) if counts else ""


def body_right_edge(page, indent, column_right):
    """
    Where the question text wraps on this page.

    Sidebars - glossary definitions, "Literacy Connections", the
    problem-solving tabs - sit in the margin to the right of that line. Only
    lines in the body font that start at the question indent are measured, so
    a sidebar cannot widen its own boundary.
    """
    family = body_font(page)
    rights = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            x0, _, x1, _ = line["bbox"]
            if not (indent - 6 <= x0 <= indent + 45):
                continue
            if any(sp["font"].startswith(family) for sp in line["spans"]):
                rights.append(x1)
    return min(max(rights), column_right + 30) if rights else column_right


def drawing_clusters(rects, touch=3):
    """
    Group drawings that touch into one rectangle each.

    A sudoku is dozens of thin lines and small cells; a tangram is seven
    separate pieces. None of them is figure-sized alone, so judged one at a
    time the diagram looks like decoration and gets dropped. Judged as a
    group, it is plainly a figure.
    """
    groups = [fitz.Rect(r) for r in rects]
    merged = True
    while merged:
        merged = False
        out = []
        while groups:
            g = groups.pop()
            i = 0
            while i < len(groups):
                if g.intersects(groups[i] + (-touch, -touch, touch, touch)):
                    g |= groups.pop(i)
                    merged = True
                else:
                    i += 1
            out.append(g)
        groups = out
    return groups


def is_tab(rect):
    """
    The problem-solving step tabs ("Understand the Problem", "Choose a
    Strategy", "Reflect"). Their lettering is drawn as shapes, not text, so it
    cannot be matched by wording - but they are unmistakably ribbon-shaped:
    short and very wide. Only used for things in the margins; a number line in
    the body is also flat and must stay.
    """
    return rect.height < 26 and rect.width > 3 * rect.height


def is_figure(rect):
    """Big enough to be a diagram, not a highlight box or a tab banner."""
    return rect.width * rect.height >= 2500 and min(rect.width, rect.height) >= 30


def content_floor(page):
    """
    The lowest y that still belongs to the page body.

    A fixed margin cut off real content: the last line of a question can sit
    closer to the bottom than any safe-looking guess. Find the running footer
    ("4 MHR • Chapter 1", "Answers • MHR 539") and stop just above it.
    """
    rect = page.rect
    footer_tops = [l[1] for l in lines_of(page)
                   if l[1] > rect.height - 70 and "MHR" in l[4]]
    return (min(footer_tops) - 1) if footer_tops else rect.height - 30


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
        bottom_limit = content_floor(page)

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
            name = section_heading_name(text)
            if name:
                heading_positions.append((y0, name))

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
            body_right = body_right_edge(page, indent, column.x1)
            starts.sort(key=lambda s: s[1])

            for i, (number, top, x0) in enumerate(starts):
                end = starts[i + 1][1] if i + 1 < len(starts) else bottom_limit
                end = min(end, bottom_limit)

                # Crop to the question's own content, not to the column edge
                # and the next question: the column edge cuts words off, and
                # the last question in a column would run on into whatever
                # sidebar sits below it.
                # Only content that STARTS in this column counts; a line may
                # still run past the gutter, which sets the right edge.
                content_top, content_bottom, content_right, headings, content_left = content_extent(
                    page, x0 - 20, column.x1, top, end, body_right,
                    next_top=starts[i + 1][1] if i + 1 < len(starts) else None,
                    single_column=len(columns) == 1)
                # Stop 2pt above the next question, but don't shave anything
                # off the page floor: the last line can sit right on it.
                limit = end - 2 if i + 1 < len(starts) else end
                crop_top = min(top - 8, content_top - 3)
                crop_left = x0 - 18 if content_left is None else min(x0 - 18, content_left - 6)
                clip = fitz.Rect(max(rect.x0, crop_left), crop_top,
                                 min(rect.x1 - 4, content_right + 10),
                                 min(limit, content_bottom + 6))
                if clip.height < 12:
                    continue

                section = section_at(top)
                slug = re.sub(r'[^a-z0-9]+', '-', section.lower()).strip('-')
                # Two Investigate runs in one lesson both have a question 1, so
                # the name carries the page and, if needed, a counter.
                # lesson - book page - question - section. Zero-padded so the
                # folder lists in reading order (p004 before p010, q2 before q10).
                base = f"{lesson_id}-p{book_page:03d}-q{int(number):02d}-{slug}"
                name = f"{base}{IMAGE_EXT}"
                n = 2
                while name in used:
                    name = f"{base}-{n}{IMAGE_EXT}"
                    n += 1
                used.add(name)

                save(page.get_pixmap(dpi=DPI_CROP, clip=clip), out_dir / name,
                     clip=clip, blank=headings)
                found.setdefault((section, number), []).append(f"{rel_dir}/{name}")
                AUDIT.append((lesson_id, name, index, clip, column.x0, column.x1, end))

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
        bottom = (end_y - 3) if same else content_floor(doc[index])

        # Text runs a little past the halfway line, so widen the crop beyond
        # the column used for finding things, or words get cut off the right.
        page_right = doc[index].rect.x1
        # Start just left of the number itself; a fixed inset cuts it off on
        # pages where the answers sit closer to the column edge.
        clip = fitz.Rect(max(column.x0 + 4, number_x - 14), y0 - 7,
                         min(column.x1 + 26, page_right - 6), bottom)
        if clip.height < 10:
            continue

        name = f"{lesson_id}-a{int(number):02d}{IMAGE_EXT}"
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
                name = f"p{book_page:03d}{IMAGE_EXT}"
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
