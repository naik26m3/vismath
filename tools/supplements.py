"""
Lessons filled in from a second PDF.

The main PDF of MHR Mathematics 9 is missing book pages 436-443, which is
the whole of lesson 8.3. Those pages come from a separate file instead.

That file is a scan with machine-read text over it, not a digital PDF like
the main one: no vector drawings, no reliable fonts, and the text reader
missed two question numbers outright. So the automatic rules in extract.py
do not apply. The question boxes below were measured from the pages and
checked by eye, one lesson's worth.

extract.run() calls apply() at the end, so a re-scan keeps the lesson filled.
"""

import io
import json

import fitz
from PIL import Image

# Each question: (number, section, page index in the supplement PDF,
#                 left, top, right, bottom)  - in PDF points on that page.
# An optional last item lists rectangles to paint out: something belonging to
# the neighbouring question that the box cannot avoid.
SUPPLEMENTS = {
    "mhr-grade-9": [
        {
            "lesson": "8.3",
            "pdf": "books/mcgraw-hill-ryerson_principles-of-mathematics-9/lesson-8.3_pages-436-443.pdf",
            "first_book_page": 436,          # page index 0 is book page 436
            "questions": [
                # book page 441
                ("1",  "Practise",          5,  12,  62, 345, 179),
                ("2",  "Practise",          5,  12, 195, 345, 307),
                # 3b's "8 cm" label hangs down level with question 4's first line, to its
                # right. Question 3 reaches down to take it and paints out the start
                # of question 4; question 4 paints the label out.
                ("3",  "Practise",          5,  12, 323, 345, 428, [(12, 416, 228, 428)]),
                ("4",  "Practise",          5,  12, 412, 345, 514, [(228, 412, 345, 427)]),
                ("5",  "Practise",          5,  12, 511, 345, 572),
                ("6",  "Connect and Apply", 5,  12, 601, 345, 642),
                # book page 442 - text starts further right; photos fill the margins
                ("7",  "Connect and Apply", 6, 146,  31, 524, 102),
                ("8",  "Connect and Apply", 6, 140,  99, 524, 226),
                ("9",  "Connect and Apply", 6, 140, 223, 524, 314),
                ("10", "Connect and Apply", 6, 140, 311, 524, 368),
                ("11", "Connect and Apply", 6, 140, 365, 524, 513),
                # runs to the very bottom of the page; the footer is further left
                ("12", "Connect and Apply", 6, 140, 510, 524, 701),
                # book page 443
                ("13", "Connect and Apply", 7,  10,  24, 360, 151),
                ("14", "Achievement Check", 7,  10, 168, 360, 279),
                ("15", "Extend",            7,  10, 295, 360, 333),
                ("16", "Extend",            7,  10, 330, 478, 439),
                ("17", "Extend",            7,  10, 436, 360, 531),
                ("18", "Extend",            7,  10, 528, 465, 622),
            ],
        },
    ],
}


def _save(pixmap, path, quality=80, clip=None, blank=()):
    image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
    if clip is not None:
        sx, sy = image.width / clip.width, image.height / clip.height
        for rect in blank:
            box = fitz.Rect(rect) & clip
            if box.is_empty:
                continue
            left, top = int((box.x0 - clip.x0) * sx), int((box.y0 - clip.y0) * sy)
            right, bottom = int((box.x1 - clip.x0) * sx), int((box.y1 - clip.y0) * sy)
            # A scan's paper is not white, so paint with the paper colour found in
            # a thin strip just above the box (or just below, at the top edge).
            strip = (left, top - 5, right, top - 1) if top >= 6 else (left, bottom + 1, right, bottom + 5)
            pixels = sorted(image.crop(strip).getdata(), key=sum)
            colour = pixels[len(pixels) * 3 // 4]            # a light, typical pixel
            image.paste(colour, (left, top, right, bottom))
    image.save(path, "WEBP", quality=quality, method=6)


def apply(book_id, chapters_done, root, image_ext=".webp", dpi_crop=150, dpi_page=120):
    """Fill in every supplemented lesson belonging to the chapters just extracted."""
    for spec in SUPPLEMENTS.get(book_id, []):
        lesson_id = spec["lesson"]
        if lesson_id.split(".")[0] not in chapters_done:
            continue

        pdf_path = root / spec["pdf"]
        lesson_path = root / "data" / book_id / f"{lesson_id}.json"
        if not pdf_path.exists() or not lesson_path.exists():
            print(f"{lesson_id:5s} supplement skipped: {pdf_path.name} or the lesson file is missing")
            continue

        doc = fitz.open(pdf_path)
        rel = f"assets/books/{book_id}"
        asset_root = root / "assets" / "books" / book_id

        # whole pages
        pages = []
        for index in range(doc.page_count):
            book_page = spec["first_book_page"] + index
            name = f"p{book_page:03d}{image_ext}"
            _save(doc[index].get_pixmap(dpi=dpi_page), asset_root / "pages" / name)
            pages.append(f"{rel}/pages/{name}")

        # question crops
        questions = []
        for number, section, index, x0, top, x1, bottom, *rest in spec["questions"]:
            page = doc[index]
            clip = fitz.Rect(x0, top, x1, bottom) & page.rect
            book_page = spec["first_book_page"] + index
            slug = section.lower().replace(" ", "-")
            name = f"{lesson_id}-p{book_page:03d}-q{int(number):02d}-{slug}{image_ext}"
            _save(page.get_pixmap(dpi=dpi_crop, clip=clip), asset_root / "questions" / name,
                  clip=clip, blank=rest[0] if rest else ())
            questions.append((number, section, f"{rel}/questions/{name}"))

        # join them to the answers the main scan already found
        lesson = json.loads(lesson_path.read_text(encoding="utf-8"))
        answers = {item["number"]: item["answerImages"]
                   for item in lesson["items"] if item["answerImages"]}

        items = [{
            "section": section,
            "number": number,
            "questionImages": [path],
            "answerImages": answers.pop(number, []),
            "hasAnswerKey": True,
        } for number, section, path in questions]

        # any answer still without a question stays available
        for number in sorted(answers, key=int):
            items.append({"section": "Answer only", "number": number, "questionImages": [],
                          "answerImages": answers[number], "hasAnswerKey": True})

        lesson["pageImages"] = pages
        lesson["missingPages"] = []
        lesson["items"] = items
        lesson["source"] = f"questions and pages from {pdf_path.name}"
        lesson_path.write_text(json.dumps(lesson, indent=2), encoding="utf-8")

        answered = sum(1 for item in items if item["questionImages"] and item["answerImages"])
        print(f"{lesson_id:5s} filled from {pdf_path.name}: {len(pages)} pages, "
              f"{len(questions)} questions, {answered} with an answer")
