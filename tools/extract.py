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
# answers_from / answers_to: where the Answers section lives, in PDF pages.
#
# Nothing else is typed in by hand:
#   - the lesson list (ids, titles, page ranges) is read from the headings of
#     the Answers section itself - see read_lessons()
#   - book page -> pdf page comes from the page numbers printed in the
#     footers - see page_map(). A fixed offset is not safe: this PDF is
#     missing book pages 436-443, so the offset changes part-way through.
# --------------------------------------------------------------------------

BOOKS = {
    "mhr-grade-9": {
        "title": "MHR Mathematics 9",
        "pdf": "books/MHR+GRADE+9.pdf",
        "answers_from": 541,
        "answers_to": 585,          # p586 onward is the Glossary, then Index
    },
}

# Every question crop, as (lesson, file, page_index, clip, column_x0, column_x1,
# next_question_y). Lets an audit find text that ended up in no crop at all.
AUDIT = []

# Every answer crop, as (lesson, file, page_index, clip). Used by review.py.
ANSWER_AUDIT = []

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
    # The whole line has to BE the heading. "Starts with" also matched a
    # question whose text begins "Investigate whether...", and the
    # "Extended Response" label on a test, and moved real questions into the
    # wrong section. Trailing dots and rules after the word are ignored.
    bare = re.sub(r'[\W_]+$', '', flat)
    for name in SECTION_HEADINGS:
        if name != "Questions" and bare == name:
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


_DRAWINGS = {}
_TEXTDICT = {}


def drawings_of(page):
    """drawings_of(page), remembered - it is slow and asked for per question."""
    if page.number not in _DRAWINGS:
        _DRAWINGS[page.number] = page.get_drawings()
    return _DRAWINGS[page.number]


def textdict_of(page):
    """page.get_text("dict"), remembered."""
    if page.number not in _TEXTDICT:
        _TEXTDICT[page.number] = page.get_text("dict")
    return _TEXTDICT[page.number]


_PAGE_MAPS = {}
PRINTED_NUMBER = re.compile(r'(?:^|\s)(\d{1,3})\s+MHR\b|\bMHR\s+(\d{1,3})\s*$')


def page_map(doc):
    """
    {book page number: pdf page index}, read from the number printed in each
    page's footer ("44 MHR - Chapter 2", "Answers - MHR 539").

    Chapter-opener pages print no number; they are filled in from their
    neighbours. Front matter is skipped - its roman numerals and the table of
    contents produce numbers that are not page numbers.
    """
    if doc.name in _PAGE_MAPS:
        return _PAGE_MAPS[doc.name]

    by_index = {}
    for index in range(12, doc.page_count):
        page = doc[index]
        for x0, y0, x1, y1, text in lines_of(page):
            if y0 > page.rect.height - 70 and "MHR" in text:
                m = PRINTED_NUMBER.search(text)
                if m:
                    by_index[index] = int(m.group(1) or m.group(2))

    # a page with no number, between two that are two apart
    for index in range(13, doc.page_count - 1):
        if index not in by_index and index - 1 in by_index and index + 1 in by_index:
            if by_index[index + 1] - by_index[index - 1] == 2:
                by_index[index] = by_index[index - 1] + 1
    # ...and the pairs of unnumbered pages at each chapter opening
    for index in range(13, doc.page_count - 2):
        if (index not in by_index and index + 1 not in by_index
                and index - 1 in by_index and index + 2 in by_index
                and by_index[index + 2] - by_index[index - 1] == 3):
            by_index[index] = by_index[index - 1] + 1
            by_index[index + 1] = by_index[index - 1] + 2

    mapping = {book_page: index for index, book_page in by_index.items()}
    _PAGE_MAPS[doc.name] = mapping
    return mapping


LESSON_HEADING = re.compile(r'^(\d+)\.(\d+)\s+([A-Z].*)$')
OTHER_HEADING = re.compile(
    r'^(Get Ready|Chapter (\d+) (?:Practice )?Test|Chapter (\d+) Review'
    r'|Chapters \d+ to (\d+) Review)\b')
PAGES = re.compile(r'\bpages?\s+(\d+)(?:\D{1,3}(\d+))?')


def read_lessons(segments):
    """
    The book's lesson list, read from the headings of the Answers section.

    Returns (chapters, spans):
      chapters  {"2": [(lesson_id, title, first_page, last_page), ...]}
      spans     {lesson_id: (start, stop)} - which segments hold its answers

    A heading is only believed if a page range follows it, on the same line
    or within the next two. That is what separates "2.5 Linear and Non-Linear
    Relations, pages 77-87" from the "2.5" on the axis of a graph.
    """
    chapters, order, stops = {}, [], []
    chapter = None

    for i, (_, _, _, _, text) in enumerate(segments):
        m = re.match(r'^Chapter (\d+)\s*$', text)
        if m:
            chapter = m.group(1)
            stops.append(i)
            continue
        if chapter is None:
            continue
        if text.startswith("Use Technology"):
            stops.append(i)          # its answers belong to no lesson
            continue

        lesson_id = title = None
        m = LESSON_HEADING.match(text)
        if m and m.group(1) == chapter:
            lesson_id, title = f"{m.group(1)}.{m.group(2)}", m.group(3)
        else:
            m = OTHER_HEADING.match(text)
            if m:
                title = m.group(1)
                if title == "Get Ready":
                    lesson_id = f"{chapter}.0"
                elif "Test" in title:
                    lesson_id = f"{chapter}.T"
                elif title.startswith("Chapters"):
                    lesson_id = f"{chapter}.C"
                else:
                    lesson_id = f"{chapter}.R"
        if lesson_id is None:
            continue

        # the page range: on this line, or one of the next two
        pages, last_line = None, i
        for j in range(i, min(i + 3, len(segments))):
            pm = PAGES.search(segments[j][4])
            if pm:
                pages, last_line = pm, j
                break
            if j > i:
                title += " " + segments[j][4]
        if not pages:
            continue

        title = PAGES.split(title)[0].strip(" ,")
        first = int(pages.group(1))
        last = int(pages.group(2) or first)
        if last < first:
            last = first

        # A misprinted range can overlap the lesson before it (8.2 is given
        # as 420-435, but 8.1 ends on 425).
        previous = chapters.get(chapter, [])
        if previous and first <= previous[-1][3] and re.match(r'^\d+\.[1-9]', lesson_id):
            first = previous[-1][3] + 1

        chapters.setdefault(chapter, []).append((lesson_id, title, first, last))
        order.append((lesson_id, i, last_line))
        stops.append(i)

    # The answer key lists "Chapter 2 Review, pages 95-96", but the review's
    # last questions are on 97. Where a review is followed by a gap before the
    # next thing starts, take one more page.
    flat = [l for c in sorted(chapters, key=int) for l in chapters[c]]
    for n, (lesson_id, title, first, last) in enumerate(flat):
        if lesson_id.endswith(".R") and n + 1 < len(flat) and flat[n + 1][2] > last + 1:
            chapter_list = chapters[lesson_id.split(".")[0]]
            chapter_list[chapter_list.index((lesson_id, title, first, last))] = (lesson_id, title, first, last + 1)

    stops = sorted(set(stops)) + [len(segments)]
    spans = {}
    for lesson_id, heading_line, last_line in order:
        stop = next(x for x in stops if x > heading_line)
        spans[lesson_id] = (last_line, stop)
    return chapters, spans


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
    for block in textdict_of(page)["blocks"]:
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
    for block in textdict_of(page)["blocks"]:
        if block.get("type") == 1:
            items.append((fitz.Rect(block["bbox"]), "", "image"))
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"]).strip()
            items.append((fitz.Rect(line["bbox"]), text, "text"))
    rect = page.rect
    kept = []
    for drawing in drawings_of(page):
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
    for block in textdict_of(page)["blocks"]:
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
    for block in textdict_of(page)["blocks"]:
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
    pages = page_map(doc)
    found = {}
    # A section can run over a page break, so the last heading seen carries
    # forward to the top of the next page.
    carried = {"section": default_section(title)}
    used = set()

    for book_page in range(first_page, last_page + 1):
        index = pages.get(book_page)
        if index is None:
            continue                  # this page is not in the PDF
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
            # The right column begins at its question numbers, so cut just
            # left of them. (Looking for an empty strip, as the answer pages
            # do, lands in the wide outer margin on these pages instead.)
            ordered = sorted(xs)
            _, first_right = max((b - a, b) for a, b in zip(ordered, ordered[1:]))
            middle = first_right - 10
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
                # Only the exercise run is kept. Investigate questions have no
                # entry in the answer key, so there is nothing to look up.
                # (They still count as "starts", so the exercise question
                # before one stops where it should.)
                if section_at(top) not in EXERCISE_SECTIONS:
                    continue
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
             for block in textdict_of(page)["blocks"]
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


def crop_answers(doc, book, lesson, segments, out_dir, rel_dir, span):
    """Crop each numbered answer belonging to one lesson."""
    lesson_id, title, _, _ = lesson
    if span is None:
        return {}
    start_at, stop_at = span

    mine = segments[start_at + 1:stop_at]

    starts = []
    for i, (index, column, y0, x0, text) in enumerate(mine):
        m = QUESTION_RE.match(text)
        if m and x0 <= column.x0 + ANSWER_INDENT:
            starts.append((m.group(1), i))

    found = {}
    row_cache = {}

    def column_items(index, column):
        """Text lines and non-decorative drawings in one column, cached."""
        key = (index, round(column.x0))
        if key not in row_cache:
            page = doc[index]
            lines = [fitz.Rect(line["bbox"])
                     for block in page.get_text("dict", clip=column)["blocks"]
                     for line in block.get("lines", [])]
            pr = page.rect
            drawings = []
            for d in drawings_of(page):
                r = fitz.Rect(d["rect"])
                # the coloured strip down the outer edge, full-width rules...
                if (r.width > pr.width * 0.9 or r.height > pr.height * 0.5
                        or r.x0 > pr.x1 - 45 or r.x1 < pr.x0 + 45):
                    continue
                if column.x0 <= r.x0 < column.x1:
                    drawings.append(r)
            row_cache[key] = (lines, drawings)
        return row_cache[key]

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

        page = doc[index]
        page_right = page.rect.x1

        lines, drawings = column_items(index, column)

        def first_row_top(y, lines=lines):
            # Just above whatever shares an answer's first row. A stacked
            # fraction's numerator starts above the number, so a fixed margin
            # either clips it or lets in a sliver of the neighbouring answer.
            row = [r for r in lines if y - 12 <= r.y0 < y + 4 and r.y1 > y + 2]
            return min([r.y0 for r in row] + [y])

        crop_top = first_row_top(y0) - 2

        # Bottom: where the NEXT answer's first row really begins.
        if same:
            next_top = first_row_top(end_y)
            bottom = next_top - 1
        else:
            next_top = None
            bottom = content_floor(page)

        # A drawing that starts inside this answer can hang down into the next
        # answer's row (the Egyptian numerals). Keep the whole drawing, and
        # paint out the next answer's text where the two overlap.
        blank = []
        mine_drawn = [r for r in drawings if crop_top - 1 <= r.y0 < bottom]
        if same and mine_drawn:
            overhang = max(r.y1 for r in mine_drawn)
            if bottom < overhang <= bottom + 14:
                bottom = overhang + 1
                blank = [r for r in lines if r.y0 >= next_top - 0.5]

        # Last answer in a column: the limit is the page floor, which leaves a
        # tall blank area under a short answer. Trim to what is actually there.
        if not same:
            below = [r for r in lines + drawings if crop_top - 1 <= r.y0 < bottom]
            if below:
                bottom = min(bottom, max(r.y1 for r in below) + 4)

        # Right edge: the content itself, never past the measured gutter. The
        # page edge would bring in the decorative strip beside the outer column.
        inside = [r for r in lines + drawings if crop_top - 1 <= r.y0 < bottom]
        content_right = max([r.x1 for r in inside], default=column.x1) + 6
        right = min(column.x1, page_right - 6, content_right)

        clip = fitz.Rect(max(column.x0 + 4, number_x - 14), crop_top, right, bottom)

        # Only skip genuinely empty slivers. A one-line answer is about 10pt
        # tall, so a higher cutoff silently drops real answers.
        if clip.height < 5:
            continue

        name = f"{lesson_id}-a{int(number):02d}{IMAGE_EXT}"
        save(doc[index].get_pixmap(dpi=DPI_CROP, clip=clip), out_dir / name,
             clip=clip, blank=blank)
        found.setdefault(number, []).append(f"{rel_dir}/{name}")
        ANSWER_AUDIT.append((lesson_id, name, index, clip))

        # An answer can run on past the bottom of its column - into the next
        # column, or onto the next page (1.2 answer 6 starts at the foot of
        # one page and parts b-d are at the top of the next). Each further
        # column it reaches gets its own crop, in reading order.
        stop = starts[n + 1][1] if n + 1 < len(starts) else len(mine)
        groups = []
        for g_index, g_column, g_y, g_x, _ in mine[position:stop]:
            key = (g_index, round(g_column.x0))
            if not groups or groups[-1]["key"] != key:
                groups.append({"key": key, "index": g_index, "column": g_column, "ys": [], "xs": []})
            groups[-1]["ys"].append(g_y)
            groups[-1]["xs"].append(g_x)

        for part, group in enumerate(groups[1:], start=2):
            g_index, g_column = group["index"], group["column"]
            g_page = doc[g_index]
            g_lines, g_drawings = column_items(g_index, g_column)

            # top: its first line, or a drawing sitting above that line at the
            # head of the column
            g_top = first_row_top(min(group["ys"]), g_lines)
            above = [r.y0 for r in g_drawings if 40 < r.y0 < g_top]
            g_top = min([g_top] + above) - 2

            # bottom: the next answer if it starts in this column, otherwise
            # the end of this answer's own content
            ends_here = (n + 1 < len(starts)
                         and (end_index, round(end_column.x0)) == group["key"])
            if ends_here:
                g_bottom = first_row_top(end_y, g_lines) - 1
            else:
                g_bottom = min(content_floor(g_page), max(group["ys"]) + 60)
                inside = [r for r in g_lines + g_drawings if g_top - 1 <= r.y0 <= max(group["ys"]) + 1]
                if inside:
                    g_bottom = min(g_bottom, max(r.y1 for r in inside) + 4)

            inside = [r for r in g_lines + g_drawings if g_top - 1 <= r.y0 < g_bottom]
            g_right = min(g_column.x1, g_page.rect.x1 - 6,
                          max([r.x1 for r in inside], default=g_column.x1) + 6)
            g_left = max(g_column.x0 + 4, min([r.x0 for r in inside], default=min(group["xs"])) - 8)
            g_clip = fitz.Rect(g_left, g_top, g_right, g_bottom)
            if g_clip.height < 5 or g_clip.width < 5:
                continue

            g_name = f"{lesson_id}-a{int(number):02d}-part{part}{IMAGE_EXT}"
            save(g_page.get_pixmap(dpi=DPI_CROP, clip=g_clip), out_dir / g_name)
            found.setdefault(number, []).append(f"{rel_dir}/{g_name}")
            ANSWER_AUDIT.append((lesson_id, g_name, g_index, g_clip))

    return found


# --------------------------------------------------------------------------

def run(book_id, chapter):
    """Extract one chapter ("3"), or every chapter ("all")."""
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
    chapters, spans = read_lessons(segments)
    book["chapters"] = chapters
    pages_by_book = page_map(doc)
    book_by_index = {index: book_page for book_page, index in pages_by_book.items()}

    wanted = sorted(chapters, key=int) if chapter == "all" else [chapter]
    summary = []

    for chapter_id in wanted:
        for lesson in chapters[chapter_id]:
            lesson_id, title, first_page, last_page = lesson

            questions = crop_questions(doc, book, lesson, q_dir, f"{rel}/questions")
            answers = crop_answers(doc, book, lesson, segments, a_dir, f"{rel}/answers",
                                   spans.get(lesson_id))

            # full pages, for page mode and the "whole page" button
            pages, missing_pages = [], []
            for book_page in range(first_page, last_page + 1):
                index = pages_by_book.get(book_page)
                if index is None:
                    missing_pages.append(book_page)
                    continue
                name = f"p{book_page:03d}{IMAGE_EXT}"
                target = p_dir / name
                if not target.exists():
                    save(doc[index].get_pixmap(dpi=DPI_PAGE), target)
                pages.append(f"{rel}/pages/{name}")

            # the answer-key pages this lesson's answers sit on
            answer_pages = []
            for index in sorted({a[2] for a in ANSWER_AUDIT if a[0] == lesson_id}):
                name = f"p{book_by_index.get(index, index + 1):03d}{IMAGE_EXT}"
                target = p_dir / name
                if not target.exists():
                    save(doc[index].get_pixmap(dpi=DPI_PAGE), target)
                answer_pages.append(f"{rel}/pages/{name}")

            # Numbering restarts under each heading, so a question is identified
            # by section AND number. Only the exercise run is kept, and that is
            # what the answer key numbers.
            sections = {}
            for (section, number), images in questions.items():
                sections.setdefault(section, {})[number] = images

            items, matched = [], set()
            for section in SECTION_HEADINGS:
                if section not in sections:
                    continue
                for number in sorted(sections[section], key=int):
                    matched.add(number)
                    items.append({
                        "section": section,
                        "number": number,
                        "questionImages": sections[section][number],
                        "answerImages": answers.get(number, []),
                        "hasAnswerKey": True,
                    })

            # An answer whose question was not found - the question's page is
            # missing from the PDF, or the question could not be picked out.
            # Keep the answer anyway; it is still worth having.
            orphans = sorted((n for n in answers if n not in matched), key=int)
            for number in orphans:
                items.append({
                    "section": "Answer only",
                    "number": number,
                    "questionImages": [],
                    "answerImages": answers[number],
                    "hasAnswerKey": True,
                })

            out = {
                "book": book_id,
                "bookTitle": book["title"],
                "chapter": chapter_id,
                "lesson": lesson_id,
                "title": title,
                "bookPages": [first_page, last_page],
                "pageImages": pages,
                "answerPageImages": answer_pages,
                "missingPages": missing_pages,
                "items": items,
            }
            (data_dir / f"{lesson_id}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

            numbers = sorted(int(n) for n in matched)
            gaps = sorted(set(range(1, (numbers[-1] if numbers else 0) + 1)) - set(numbers))
            unanswered = [n for n in matched if n not in answers]
            summary.append({
                "lesson": lesson_id, "title": title, "questions": len(matched),
                "answers": len(answers), "gaps": gaps, "orphans": orphans,
                "unanswered": sorted(unanswered, key=int), "missingPages": missing_pages,
            })
            print(f"{lesson_id:5s} {title[:38]:38s} q {len(matched):3d}  a {len(answers):3d}"
                  f"{'  gaps ' + str(gaps) if gaps else ''}"
                  f"{'  answer-only ' + str(len(orphans)) if orphans else ''}"
                  f"{'  no-answer ' + str(len(unanswered)) if unanswered else ''}"
                  f"{'  MISSING PAGES ' + str(missing_pages) if missing_pages else ''}")

    write_index(data_dir, book_id, book)
    return summary


def write_index(data_dir, book_id, book):
    """
    index.json: the list of lessons, in book order, for a lesson picker.

    A web page cannot list the files in a folder, so it needs to be told which
    lessons exist. Built from every lesson file present, so extracting a
    single chapter does not drop the others from the list.
    """
    lessons = []
    for path in data_dir.glob("*.json"):
        if path.name == "index.json":
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        lessons.append({
            "lesson": d["lesson"],
            "chapter": d["chapter"],
            "title": d["title"],
            "bookPages": d["bookPages"],
            "file": f"data/{book_id}/{path.name}",
        })
    lessons.sort(key=lambda l: (int(l["chapter"]), l["bookPages"][0]))

    index = {"book": book_id, "bookTitle": book["title"], "lessons": lessons}
    (data_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")


if __name__ == "__main__":
    book_id = sys.argv[1] if len(sys.argv) > 1 else "mhr-grade-9"
    chapter = sys.argv[2] if len(sys.argv) > 2 else "1"
    run(book_id, chapter)
