"""
Bundle the lesson JSON into one script file for demos/answer-key.html.

The demo is opened by double-clicking, and a page opened that way cannot
fetch() JSON. So the data is written as a .js file the page can just load.

    python tools/demo_data.py mhr-grade-9
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
book = sys.argv[1] if len(sys.argv) > 1 else "mhr-grade-9"

lessons = [json.loads(p.read_text(encoding="utf-8"))
           for p in sorted(p for p in (ROOT / "data" / book).glob("*.json") if p.name != "index.json")]

out = ROOT / "demos" / "answer-key-data.js"
out.write_text("window.ANSWER_KEY_LESSONS = " + json.dumps(lessons) + ";\n", encoding="utf-8")
print(f"{len(lessons)} lessons -> {out}")
