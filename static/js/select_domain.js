document.addEventListener('DOMContentLoaded', () => {
    const cards = [...document.querySelectorAll('.coding-domain-card')];
    const searchInput = document.getElementById('domainSearch');
    const difficultyFilter = document.getElementById('difficultyFilter');
    const noResults = document.getElementById('noDomainResults');
    const form = document.getElementById('codingDomainForm');
    const startButton = document.getElementById('startCodingRoundBtn');
    const selectedDomainInput = document.getElementById('selectedDomainInput');
    const selectedDifficultyInput = document.getElementById('selectedDifficultyInput');
    const selectedName = document.getElementById('selectedDomainName');
    const selectedDifficulty = document.getElementById('selectedDomainDifficulty');
    const selectedTime = document.getElementById('selectedDomainTime');
    const selectedQuestions = document.getElementById('selectedDomainQuestions');

    const selectCard = (card) => {
        cards.forEach((item) => item.classList.toggle('is-selected', item === card));
        selectedDomainInput.value = card.dataset.domain;
        selectedDifficultyInput.value = card.dataset.defaultDifficulty;
        selectedName.textContent = card.dataset.domain;
        selectedDifficulty.textContent = card.dataset.difficulty;
        selectedTime.textContent = card.dataset.time;
        selectedQuestions.textContent = `${card.dataset.questions} questions`;
        startButton.disabled = false;
    };

    const filterCards = () => {
        const query = searchInput.value.trim().toLowerCase();
        const difficulty = difficultyFilter.value;
        let visibleCount = 0;

        document.querySelectorAll('[data-domain-card]').forEach((column) => {
            const matchesSearch = column.dataset.search.toLowerCase().includes(query);
            const matchesDifficulty = difficulty === 'all' || column.dataset.levels.split(' ').includes(difficulty);
            const isVisible = matchesSearch && matchesDifficulty;
            column.classList.toggle('d-none', !isVisible);
            visibleCount += Number(isVisible);
        });

        noResults.classList.toggle('d-none', visibleCount > 0);
    };

    cards.forEach((card) => {
        card.addEventListener('click', (event) => {
            if (event.target.closest('.select-domain-btn') || event.target === card) selectCard(card);
            else selectCard(card);
        });
        card.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                selectCard(card);
            }
        });
    });

    searchInput.addEventListener('input', filterCards);
    difficultyFilter.addEventListener('change', filterCards);
    form.addEventListener('submit', (event) => {
        if (!selectedDomainInput.value) event.preventDefault();
    });
});
