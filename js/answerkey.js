const BOOKS_URL = "https://vismath-books.pages.dev";

const question = document.querySelector('#js-question');
const questionPage = question.querySelector('#js-question-page');
const questionPageNumber = question.querySelector('#js-question-page-number');
const questionLeftBtn = question.querySelector('#js-question-left-btn');
const questionRightBtn = question.querySelector('#js-question-right-btn');

const answer = document.querySelector('#js-answer');
const answerPage = answer.querySelector('#js-answer-page');
const answerPageNumber = answer.querySelector('#js-answer-page-number');
const answerLeftBtn = answer.querySelector('#js-answer-left-btn');
const answerRightBtn = answer.querySelector('#js-answer-right-btn');

const lessonPicker = document.querySelector('#js-lesson-picker');

const questionHideBtn = document.querySelector('#js-question-hide-btn');
const answerHideBtn = document.querySelector('#js-answer-hide-btn');

const params = new URLSearchParams(location.search);
const book = params.get('book');

let lesson;
let lessonIndex;
let isNew = true;
let questionIndex = 0;
let answerIndex = 0;

function refineCall(lessonName, lessonIndex) {
    return `${BOOKS_URL}/${lessonName.slice(0, -10)}/${lessonIndex.lessons[0].lesson}.json`;
}

function pageNumber(page) {
    return Number(page.slice(-8, -5));
}

function updatePage(page, num, img) {
    num.textContent = `Page ${pageNumber(img)}`;
    page.src = `${BOOKS_URL}/${img}`;
}


async function loadIndex() {
    const response = await fetch(`${BOOKS_URL}/data/${params.get('book')}/index.json`);
    lessonIndex = await response.json();
    document.title = `${lessonIndex.shortTitle}`;

    let lessonList = '';
    let currentChapter = 0;
    lessonIndex.lessons.forEach((item) => {
        if (item.chapter !== currentChapter) {
            if (currentChapter > 0) {
                lessonList += `</optgroup>`
            }
        
            lessonList += `<optgroup label="Chapter ${item.chapter}">`
            currentChapter = item.chapter;
        }

        lessonList += `<option value="${item.file}">${item.lesson} ${item.title}</option>`
    })
    lessonList += `</optgroup>`;

    lessonPicker.innerHTML = lessonList;
    loadLesson(`data/${params.get('book')}/index.json`, true);
}

lessonPicker.addEventListener('change', (e) => {
    loadLesson(e.target.value);
})

loadIndex();


async function loadLesson(lessonName, isFirst = false) {
    let response;
    
    if (isFirst) {
        response = await fetch(`${refineCall(lessonName, lessonIndex)}`);
        lesson = await response.json();
    } else {
        response = await fetch(`${BOOKS_URL}/${lessonName}`);
        lesson = await response.json();
    }
    
    
    
    questionIndex = 0;
    answerIndex = 0;

    updatePage(questionPage, questionPageNumber, lesson.pageImages[0]);
    updatePage(answerPage, answerPageNumber, lesson.answerPageImages[0]);
}



questionLeftBtn.addEventListener('click', () => {
    if (questionIndex - 1 >= 0) {
        questionIndex--;
        updatePage(questionPage, questionPageNumber, lesson.pageImages[questionIndex]);
    }
})

questionRightBtn.addEventListener('click', () => {
    if (questionIndex + 1 < lesson.pageImages.length) {
        questionIndex++;
        updatePage(questionPage, questionPageNumber, lesson.pageImages[questionIndex]);
    }
})

answerLeftBtn.addEventListener('click', () => {
    if (answerIndex - 1 >= 0) {
        answerIndex--;
        updatePage(answerPage, answerPageNumber, lesson.answerPageImages[answerIndex]);
    }
})

answerRightBtn.addEventListener('click', () => {
    if (answerIndex + 1 < lesson.answerPageImages.length) {
        answerIndex++;
        updatePage(answerPage, answerPageNumber, lesson.answerPageImages[answerIndex]);
    }
})

questionHideBtn.addEventListener('click', () => {
    
    if (questionPage.classList.toggle('hidden')) {
        questionHideBtn.textContent = "Show";
    } else {
        questionHideBtn.textContent = "Hide";
    }
    question.classList.toggle('portrait:flex-none');
    
})

answerHideBtn.addEventListener('click', () => {
    if (answerPage.classList.toggle('hidden')) {
        answerHideBtn.textContent = "Show";
    } else {
        answerHideBtn.textContent = "Hide";
    }
    answer.classList.toggle('portrait:flex-none');
    
})



