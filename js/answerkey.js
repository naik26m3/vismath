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

let lesson;
let questionIndex = 0;
let answerIndex = 0;

function pageNumber(page) {
    return Number(page.slice(-8, -5));
}

function updatePage(page, num, img) {
    num.textContent = `Page ${pageNumber(img)}`;
    page.src = img;
}

async function loadLesson(lessonName) {
    const response = await fetch(lessonName);
    lesson = await response.json();
    questionIndex = 0;
    answerIndex = 0;

    updatePage(questionPage, questionPageNumber, lesson.pageImages[0]);
    updatePage(answerPage, answerPageNumber, lesson.answerPageImages[0]);
}

loadLesson("data/mhr-grade-9/2.3.json");

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







