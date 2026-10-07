const stage = document.querySelector('#js-inner-stage');
const submit = document.querySelector('#js-input-submit');
const minInput = document.querySelector('#js-input-min');
const maxInput = document.querySelector('#js-input-max');
const errorMsg = document.querySelector('#js-error-msg');

function makeLine(min, max) {
    const line = document.createElement('div');
    line.className = "js-line h-5 border-t-4  border-slate-400 flex justify-between items-center py-5";
    line.style.width = `${((max - min) / 20) * 100}%`;

    let ticks = '';
    
    for (let i = min; i <= max; i++) {
        ticks += `<div class="w-0 flex flex-col items-center ">
                    <div class="w-0.5 h-5 bg-slate-400"></div>
                    <span class="text-lg">${i}</span>
                </div>`
    }

    line.innerHTML = ticks;
    stage.appendChild(line);
}



submit.addEventListener('click', () => {
    const min = Number(minInput.value);
    const max = Number(maxInput.value);

    if (Number.isInteger(min) && Number.isInteger(max)) {
        errorMsg.textContent = '';
        stage.textContent = '';
        const row = Math.ceil(( max - min ) / 20); 
        let gap = 20;
                                
        for (let i = 1; i <= row; i++) {
            // if (i == row) {
            //     makeLine(min + gap * (row - 1), max);
            // } else {
            //     makeLine(min + gap * (i - 1), min + gap * i);
            // }

            makeLine(min  + gap * (i - 1), Math.min(min + gap * i, max));
            
        }
        


    } else {
        errorMsg.textContent = "Pls input a whole number";
    } 

})