const BAR_SPACING = 20;

const stage = document.querySelector('#js-fraction-stage');
const input = document.querySelector('#js-fraction-input');
const form = document.querySelector('#js-fraction-form');
let barCounter = 0;

function addBar(numerator, denominator) {
    const bar = document.createElement('div');
    bar.className = "flex w-60 h-14 border-2 absolute touch-none";

    bar.style.top = `${20 + (14 * 4 + BAR_SPACING) * barCounter}px`;
    bar.style.left = "20px";

    const delButton = document.createElement('button');
    delButton.className = "flex justify-center items-center absolute -top-3 -right-3 border-3 rounded-[100%] size-[1.5rem] bg-red-800";
    delButton.textContent = "X"; 

    let pieces = "";
    
    for (let i = 0; i < denominator; i++) {
        if (i < numerator) {
            pieces += `<div class="border flex-1 flex items-center justify-center bg-amber-300">1/${denominator}</div>`;
        } else {
            pieces += `<div class="border flex-1 flex items-center justify-center dark:bg-mist-900">1/${denominator}</div>`;
        }
    }
    bar.innerHTML = pieces;
    bar.appendChild(delButton);
    stage.appendChild(bar);
    barCounter++;

    delButton.addEventListener("pointerdown", (e) => {
        e.stopPropagation();
    });

    delButton.addEventListener("click", () => {
        bar.remove();
        barCounter--;
    })

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
}

document.querySelector('#js-fraction-add-button').addEventListener('click', () => {
    input.showModal();
});

form.addEventListener('submit', (e) => {
    const error = document.querySelector('#js-input-error');
    error.textContent = '';

    if (e.submitter.value === 'cancel') {
        return;
    }
    
    const numerator = Number(document.querySelector('#js-input-numerator').value);
    const denominator = Number(document.querySelector('#js-input-denominator').value);
        
    if (numerator >= 0 && denominator > 0 ) {
        addBar(numerator, denominator);
    } else {
        e.preventDefault();
        error.textContent = "Denominator should be > 0 and Numerator should be >= 0";
    }

})

document.querySelector('#js-fraction-clear-button').addEventListener('click', () => {
    barCounter = 0;
    stage.innerHTML = '';
});

