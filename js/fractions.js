const BAR_SPACING = 60;

const stage = document.querySelector('#js-fraction-stage');
let barCounter = 0;

document.querySelector('#js-fraction-add-button').addEventListener('click', () => {
    const denominator = Number(prompt("What is the denominator?"));

    if (!Number.isInteger(denominator) || denominator > 20 || denominator < 1) {
        alert("Enter a whole number from 1 to 20");
        return;
    }

    const numerator = Number(prompt("What is the numerator?"));
    
    if (!Number.isInteger(numerator) || numerator > denominator || numerator < 0) {
        alert(`Enter a whole number from 0 to ${denominator}`);
        return;
    }

    // const numerator = 3;
    // const denominator = 4;

    const bar = document.createElement('div');
    bar.className = "flex w-60 h-14 border-2 absolute touch-none";


    bar.style.top = `${BAR_SPACING * barCounter}px`;
    bar.style.left = "20px";

    let pieces = "";
    
    for (let i = 0; i < denominator; i++) {
        if (i < numerator) {
            pieces += `<div class="border flex-1 flex items-center justify-center bg-amber-300">1/${denominator}</div>`;
        } else {
            pieces += `<div class="border flex-1 flex items-center justify-center bg-inherit">1/${denominator}</div>`;
        }
    }
    bar.innerHTML = pieces;
    stage.appendChild(bar);
    barCounter++;

    let isDragging = false;

    let howFarX = 0;
    let howFarY = 0;

    bar.addEventListener("pointerdown", (e) => {
        isDragging = true;
        const barCoords = bar.getBoundingClientRect();
        howFarX = e.clientX - barCoords.x;
        howFarY = e.clientY - barCoords.y;
        bar.setPointerCapture(e.pointerId);
        // console.log(bar.getBoundingClientRect().x, bar.getBoundingClientRect().y);
    })

    bar.addEventListener("pointermove", (e) => {
        if (isDragging) {
            const stageCoords = stage.getBoundingClientRect();
            bar.style.top = `${e.clientY - stageCoords.y - howFarY  + stage.scrollTop}px`;
            bar.style.left = `${e.clientX - stageCoords.x - howFarX + stage.scrollLeft}px`;
            // console.log(e.clientX, e.clientY); 
        } 
        
    })

    bar.addEventListener("pointerup", () => {
        isDragging = false;
    })
});

document.querySelector('#js-fraction-clear-button').addEventListener('click', () => {
    barCounter = 0;
    stage.innerHTML = '';
});

// document.addEventListener("pointermove", e => {
//     console.log("Cursor coords:", e.clientX, e.clientY);
//     console.log("Stage coords: ", stage.getBoundingClientRect().x, stage.getBoundingClientRect().y);
//     console.log("CurInS coords1:", e.clientX - stage.getBoundingClientRect().x, e.clientY - stage.getBoundingClientRect().y);
// });

