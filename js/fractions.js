const stage = document.querySelector('#js-fraction-stage');

document.querySelector('#js-fraction-add-button').addEventListener('click', () => {
    
    const bar = document.createElement('div');
    bar.className = "flex w-60 h-14 border-2";
    
    const demoniator = 8;

    let pieces = "";
    for (let i = 0; i < demoniator; i++) {
        pieces += `<div class="border flex-1 flex items-center justify-center">1/${demoniator}</div>`
    }
    bar.innerHTML = pieces;

    stage.appendChild(bar);

})

