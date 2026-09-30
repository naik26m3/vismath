const BAR_SPACING = 30;

const stage = document.querySelector('#js-fraction-stage');
const inputFraction = document.querySelector('#js-fraction-input');
const inputNumber = document.querySelector('#js-number-input');
const fractionForm = document.querySelector('#js-fraction-form');
const numberForm = document.querySelector('#js-number-form');
let barCounter = 0;
let numberCounter = 0;
let isSelected = false;

function updateCount(parts, whole, denominator) {
    return `${parts * whole/denominator} (${parts}/${denominator})`
}

function addBar(numerator, denominator) {
    const bar = document.createElement('div');
    bar.className = "js-bar flex w-60 h-14 border-2 absolute touch-none bg-mist-900";

    bar.style.top = `${30 + (14 * 4 + BAR_SPACING) * barCounter}px`;
    bar.style.left = "20px";

    const delButton = document.createElement('button');
    delButton.className = "flex justify-center items-center absolute -top-3 -right-3 border-3 rounded-[100%] size-[1.5rem] bg-red-800";
    delButton.textContent = "X"; 

    const currentCount = document.createElement('p');
    currentCount.className = "js-count absolute -top-7.5 -left-1 text-xl font-bold"
    currentCount.textContent = `${numerator}/${denominator}`;


    let pieces = "";
    
    for (let i = 0; i < denominator; i++) {
        if (i < numerator) {
            pieces += `<div class="js-part border flex-1 flex items-center justify-center text-xl bg-amber-300">1/${denominator}</div>`;
        } else {
            pieces += `<div class="js-part border flex-1 flex items-center justify-center text-xl opacity-50">1/${denominator}</div>`;
        }
    }
    bar.innerHTML = pieces;
    bar.appendChild(delButton);
    bar.appendChild(currentCount);
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

    let coords = {};
    let shadedPart;
    bar.addEventListener("pointerdown", (e) => {
        isDragging = true;
        const barCoords = bar.getBoundingClientRect();
        howFarX = e.clientX - barCoords.x;
        howFarY = e.clientY - barCoords.y;
        coords.x = barCoords.x;
        coords.y = barCoords.y;
        bar.setPointerCapture(e.pointerId);
        if (e.target.matches('.js-part')) {
            shadedPart = e.target;
        } else {
            shadedPart = null;
        }
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
        const barNow = bar.getBoundingClientRect();

        if (shadedPart && Math.abs(coords.x - barNow.x) <= 5 && Math.abs(coords.y - barNow.y) <= 5) {
            shadedPart.classList.toggle("bg-amber-300")
            shadedPart.classList.toggle("opacity-50");
            let whole = Number(bar.dataset.whole);
            let parts = bar.querySelectorAll('.bg-amber-300').length; 

            if (bar.dataset.whole) {
                currentCount.textContent = `${updateCount(parts, whole, denominator)}`
            } else {
                currentCount.textContent = `${parts}/${denominator}`;
            }
            
        }
        // console.log(barNow);    
        isDragging = false;
    })
}

function addNumber(number) {
    const numberContainer = document.createElement('div');
    numberContainer.className = "h-10 px-3 absolute flex items-center justify-center touch-none";

    numberContainer.style.top = `${30 + (14 * 4 + BAR_SPACING) * numberCounter}px`;
    numberContainer.style.left = "20px";

    const delButton = document.createElement('button');
    delButton.className = "flex justify-center items-center absolute -top-3 -right-3 border-3 rounded-[100%] size-[1.5rem] bg-red-800";
    delButton.textContent = "X"; 

    const value = document.createElement('div');
    value.className = "font-bold text-4xl";
    value.textContent = number;

    numberContainer.appendChild(value);
    numberContainer.appendChild(delButton);
    stage.appendChild(numberContainer);
    numberCounter++;

    delButton.addEventListener("pointerdown", (e) => {
        e.stopPropagation();
    });

    delButton.addEventListener("click", () => {
        numberContainer.remove();
        numberCounter--;
    })

    let isDragging = false;

    let howFarX = 0;
    let howFarY = 0;

    let coords = {};
    numberContainer.addEventListener("pointerdown", (e) => {
        isDragging = true;
        const barCoords = numberContainer.getBoundingClientRect();
        howFarX = e.clientX - barCoords.x;
        howFarY = e.clientY - barCoords.y;
        coords.x = barCoords.x;
        coords.y = barCoords.y;
        numberContainer.setPointerCapture(e.pointerId);
    })

    numberContainer.addEventListener("pointermove", (e) => {
        if (isDragging) {
            const stageCoords = stage.getBoundingClientRect();
            numberContainer.style.top = `${e.clientY - stageCoords.y - howFarY  + stage.scrollTop}px`;
            numberContainer.style.left = `${e.clientX - stageCoords.x - howFarX + stage.scrollLeft}px`;
            // console.log(e.clientX, e.clientY); 
        } 
    })

    numberContainer.addEventListener("pointerup", (e) => {
        isDragging = false;
        numberContainer.style.pointerEvents = 'none'; 
        const bar = document.elementFromPoint(e.clientX, e.clientY).closest('.js-bar')
        numberContainer.style.pointerEvents = '';

        if (bar) {
            const pieces = bar.querySelectorAll('.js-part');
            const currentCount = bar.querySelector('.js-count');
            pieces.forEach((part) => {
                part.textContent = `${number/pieces.length}`;
                // console.log(part.classList.contains('bg-amber-300'));
            })
            const parts = bar.querySelectorAll('.bg-amber-300').length;
            currentCount.textContent = `${updateCount(parts, number, pieces.length)}`
            bar.dataset.whole = number;
            numberContainer.remove();
            numberCounter--;
        };

    })
}

document.querySelector('#js-fraction-add-fraction-button').addEventListener('click', () => {
    inputFraction.showModal();
});

document.querySelector('#js-fraction-add-number-button').addEventListener('click', () => {
    inputNumber.showModal();
});

fractionForm.addEventListener('submit', (e) => {
    const error = document.querySelector('#js-fraction-input-error');
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

numberForm.addEventListener('submit', (e) => {
    const error = document.querySelector('#js-number-input-error');
    error.textContent = '';

    if (e.submitter.value === 'cancel') {
        return;
    }

    addNumber(Number(document.querySelector('#js-input-number').value));
})


document.querySelector('#js-fraction-clear-button').addEventListener('click', () => {
    barCounter = 0;
    numberCounter = 0;
    stage.innerHTML = '';
});

