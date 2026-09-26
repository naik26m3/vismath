const stage    = document.getElementById("stage");
const addBtn   = document.getElementById("add-btn");
const clearBtn = document.getElementById("clear-btn");

let dropCount = 0;   // how many bars have EVER been made. only goes up.
let topLayer  = 1;   // rises every grab, so the dragged bar sits on top

// Where new bars land. dropCount wraps around these slots with %,
// so bar 6 goes back to slot 0 instead of falling off the bottom.
const SLOT_COUNT   = 5;
const SLOT_HEIGHT  = 70;   // px from one slot to the next
const SLOT_INDENT  = 18;   // px each slot is nudged right, so they fan out
const SLOT_ORIGIN  = 16;   // px padding from the stage's top-left corner


// ---------------------------------------------------------------
// Dragging: pointer events work for mouse, finger and stylus alike.
// ---------------------------------------------------------------
function makeDraggable(el) {
  let grabX = 0;   // where inside the bar the pointer grabbed it
  let grabY = 0;

  el.addEventListener("pointerdown", function (e) {
    const box = el.getBoundingClientRect();
    grabX = e.clientX - box.left;
    grabY = e.clientY - box.top;

    // Keep receiving move events even if the pointer outruns the element.
    el.setPointerCapture(e.pointerId);

    el.style.zIndex = ++topLayer;
    el.classList.add("cursor-grabbing");
  });

  el.addEventListener("pointermove", function (e) {
    // Only move while this element actually holds the pointer.
    if (!el.hasPointerCapture(e.pointerId)) return;

    const area = stage.getBoundingClientRect();

    // Pointer position, made relative to the stage, minus the grab offset
    // so the bar stays where you grabbed it instead of snapping.
    let x = e.clientX - area.left - grabX;
    let y = e.clientY - area.top  - grabY;

    // Keep the bar inside the stage.
    x = Math.max(0, Math.min(x, stage.clientWidth  - el.offsetWidth));
    y = Math.max(0, Math.min(y, stage.clientHeight - el.offsetHeight));

    el.style.left = x + "px";
    el.style.top  = y + "px";
  });

  el.addEventListener("pointerup", function () {
    el.classList.remove("cursor-grabbing");
  });
}


// ---------------------------------------------------------------
// Building one fraction bar.
// ---------------------------------------------------------------
function addBar(numerator, denominator) {

  // The draggable group: label + bar, positioned absolutely in the stage.
  // "touch-none" stops a finger drag from scrolling the page instead.
  const group = document.createElement("div");
  group.className = "absolute cursor-grab touch-none select-none";

  // Stagger each new bar so they don't land on top of each other.
  // % wraps the slot back to 0 once we run past the last one:
  //   dropCount 0,1,2,3,4, 5,6,7,8,9, 10...
  //   slot      0,1,2,3,4, 0,1,2,3,4,  0...
  const slot = dropCount % SLOT_COUNT;

  group.style.left = (SLOT_ORIGIN + slot * SLOT_INDENT) + "px";
  group.style.top  = (SLOT_ORIGIN + slot * SLOT_HEIGHT) + "px";
  group.style.zIndex = ++topLayer;

  dropCount++;   // never goes down, not even when a bar is deleted

  const label = document.createElement("p");
  label.className = "text-xs font-mono mb-1 text-slate-600 dark:text-slate-400";
  label.textContent = numerator + "/" + denominator;

  // Fixed width, so every bar represents the same "whole" and they
  // can be compared by sliding one under another.
  const bar = document.createElement("div");
  bar.className = "flex w-80 h-14 border-2 border-slate-700 dark:border-slate-300 rounded overflow-hidden bg-white dark:bg-slate-700";

  for (let i = 0; i < denominator; i++) {
    const piece = document.createElement("div");

    const filled = "flex-1 flex items-center justify-center border-r border-slate-700 bg-amber-300 text-slate-900 text-xs";
    const empty  = "flex-1 flex items-center justify-center border-r border-slate-700 text-slate-500 text-xs";

    piece.className = (i < numerator) ? filled : empty;
    piece.textContent = "1/" + denominator;
    bar.appendChild(piece);
  }

  group.appendChild(label);
  group.appendChild(bar);
  stage.appendChild(group);

  makeDraggable(group);
}


addBtn.addEventListener("click", function () {
  const denominator = 5;
  const numerator   = 4;

  if (!Number.isInteger(denominator) || denominator < 1 || denominator > 20) {
    alert("Denominator must be a whole number from 1 to 20.");
    return;
  }
  if (!Number.isInteger(numerator) || numerator < 0 || numerator > denominator) {
    alert("Numerator must be a whole number from 0 to " + denominator + ".");
    return;
  }

  addBar(numerator, denominator);
});


clearBtn.addEventListener("click", function () {
  stage.innerHTML = "";
  dropCount = 0;
});
