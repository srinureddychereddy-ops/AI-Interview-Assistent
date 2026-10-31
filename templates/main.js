

/**
 * AI Interview Assistant - Core Premium Client Architecture
 */

document.addEventListener("DOMContentLoaded", function () {
    // Mobil Sidebar Responsive View Manager
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", function (e) {
            e.stopPropagation();
            sidebar.classList.toggle("show");
        });
    }

    // Interactive Node Cleanups
    document.addEventListener("click", function (e) {
        if (sidebar && sidebar.classList.contains("show") && !sidebar.contains(e.target) && e.target !== sidebarToggle) {
            sidebar.classList.remove("show");
        }
    });

    // Auth form micro-interactions
    const authForm = document.querySelector("form.d-flex.flex-column.gap-3");
    if (authForm) {
        // Subtle dynamic border lighting feedback mechanics on interaction fields
        const inputs = authForm.querySelectorAll(".form-control-premium");
        inputs.forEach(input => {
            input.addEventListener("focus", function() {
                this.parentElement.style.transition = "transform 0.2s ease";
            });
        });
    });
});

/**
 * Chart Initialization Engine
 * Constructs modern single linear performance vectors matching UI expectations
 */
function initDashboardAnalytics() {
    const ctx = document.getElementById('performanceChart');
    if (!ctx) return;

    // Premium Color Stop Gradient Instantiator
    const chartContext = ctx.getContext('2d');
    const gradient = chartContext.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.25)');
    gradient.addColorStop(1, 'rgba(59, 130, 246, 0.00)');

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Session 01', 'Session 02', 'Session 03', 'Session 04', 'Session 05', 'Session 06', 'Session 07'],
            datasets: [{
                label: 'Performance Velocity Metric',
                data: [62, 68, 65, 74, 71, 79, 84],
                borderColor: '#3b82f6',
                borderWidth: 2.5,
                pointBackgroundColor: '#3b82f6',
                pointHoverRadius: 6,
                fill: true,
                backgroundColor: gradient,
                tension: 0.36
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#71717a', font: { family: 'Inter', size: 11 } }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#71717a', font: { family: 'Inter', size: 11 } },
                    min: 50,
                    max: 100
                }
            }
        }
    });
}

/**
 * Premium AI Interview Page Engine
 */
function initInterviewPage() {
    const setupView = document.getElementById('interview-setup-view');
    const liveView = document.getElementById('interview-live-view');
    const setupForm = document.getElementById('interviewSetupForm');
    const answerForm = document.getElementById('answer-form');
    const conversationArea = document.getElementById('conversation-area');
    const endInterviewBtn = document.getElementById('end-interview-btn');

    if (!setupView) return; // Only run on the interview page


    let interviewState = {};
    let timerInterval;

    // 1. Start Interview
    setupForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const startBtn = setupForm.querySelector('button[type="submit"]');
        toggleButtonLoading(startBtn, true);

        interviewState.role = document.getElementById('role').value;
        interviewState.experience = document.getElementById('experience').value;
        interviewState.interview_type = document.getElementById('interview_type').value;

        const response = await fetch('/api/interview/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(interviewState),
        });
        const data = await response.json();

        if (data.status === 'success') {
            interviewState.currentQuestion = data.question;
            interviewState.questionNumber = data.question_number; // This is the number of the question being ASKED
            interviewState.session_id = data.session_id;
            
            // Transition UI
            setupView.classList.add('fade-out');
            setTimeout(() => {
                setupView.classList.add('d-none');
                liveView.classList.remove('d-none');
                liveView.classList.add('fade-in');
                document.getElementById('active-role').textContent = interviewState.role;
                startTimer();
                addMessageToConversation('ai', data.question);
            }, 500);
        } else {
            // Handle error
            toggleButtonLoading(startBtn, false);
        }
    });

    // 2. Submit Answer
    answerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const answerInput = document.getElementById('user-answer');
        const answer = answerInput.value.trim();
        if (!answer) return;

        const submitBtn = document.getElementById('submit-answer-btn');
        toggleButtonLoading(submitBtn, true, true);
        addMessageToConversation('user', answer);
        answerInput.value = '';
        answerInput.disabled = true;

        const payload = { ...interviewState, answer: answer, question: interviewState.currentQuestion };
        
        const response = await fetch('/api/interview/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await response.json();

        if (data.status === 'success') {
            // Add AI feedback and next question
            addMessageToConversation('feedback', data.evaluation.feedback);
            setTimeout(() => {
                addMessageToConversation('ai', data.next_question, true);
                interviewState.currentQuestion = data.next_question;
                interviewState.questionNumber++;
                updateLiveEvaluation(data.evaluation.scores);
                document.getElementById('question-counter').textContent = `Q ${interviewState.questionNumber}/10`;
                
                toggleButtonLoading(submitBtn, false, true);
                answerInput.disabled = false;
                answerInput.focus();
            }, 1000); // Simulate AI thinking time
        }
    });

    // 3. End Interview
    endInterviewBtn.addEventListener('click', async () => {
        if (!confirm("Are you sure you want to end the interview?")) {
            return;
        }

        liveView.classList.add('fade-out');
        clearInterval(timerInterval);

        const response = await fetch('/api/interview/end', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: interviewState.session_id })
        });
        const data = await response.json();

        if (data.status === 'success') {
            window.location.href = `/report/${data.session_id}`;
        } else {
            alert('Failed to generate report. Please try again.');
            liveView.classList.remove('fade-out');
        }
    });

    // --- Helper Functions ---

    function typeEffect(element, text) {
        let i = 0;
        element.innerHTML = "";
        const timer = setInterval(() => {
            if (i < text.length) {
                element.innerHTML += text.charAt(i);
                i++;
                conversationArea.scrollTop = conversationArea.scrollHeight;
            } else {
                clearInterval(timer);
            }
        }, 20);
    }

    function addMessageToConversation(sender, text, useTypingEffect = false) {
        const messageWrapper = document.createElement('div');
        messageWrapper.className = `chat-message-wrapper ${sender}-wrapper`;

        let iconClass = sender === 'ai' ? 'bi-stars' : 'bi-person';
        let title = sender === 'ai' ? 'AI Interviewer' : 'Your Answer';
        if (sender === 'feedback') {
            iconClass = 'bi-clipboard-data';
            title = 'Feedback';
        }

        messageWrapper.innerHTML = `
            <div class="chat-icon"><i class="bi ${iconClass}"></i></div>
            <div class="chat-bubble">
                <div class="chat-title">${title}</div>
                <p class="chat-text"></p>
            </div>
        `;
        conversationArea.appendChild(messageWrapper);
        const textElement = messageWrapper.querySelector('.chat-text');

        if (useTypingEffect) {
            typeEffect(textElement, text);
        } else {
            textElement.innerHTML = text.replace(/\n/g, '<br>');
        }
        conversationArea.scrollTop = conversationArea.scrollHeight;
    }

    function updateLiveEvaluation(scores) {
        const metrics = {
            'Confidence': scores.confidence,
            'Communication': scores.communication,
            'Technical Accuracy': scores.technical_accuracy,
            'Problem Solving': scores.problem_solving,
        };
        const container = document.getElementById('live-evaluation-metrics');
        container.innerHTML = ''; // Clear existing

        for (const [key, value] of Object.entries(metrics)) {
            const metricEl = document.createElement('div');
            metricEl.className = 'metric-item';
            metricEl.innerHTML = `
                <div class="d-flex justify-content-between small mb-1">
                    <span class="text-muted">${key}</span>
                    <span class="text-main fw-semibold">${value}%</span>
                </div>
                <div class="progress" style="height: 6px;">
                    <div class="progress-bar" role="progressbar" style="width: ${value}%"></div>
                </div>
            `;
            container.appendChild(metricEl);
        }
    }

    function startTimer() {
        const timerElement = document.getElementById('interview-timer');
        let totalSeconds = 0;
        timerInterval = setInterval(() => {
            totalSeconds++;
            let mins = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
            let secs = String(totalSeconds % 60).padStart(2, '0');
            timerElement.textContent = `${mins}:${secs}`;
        }, 1000);
    }

    function toggleButtonLoading(button, isLoading, isIconBtn = false) {
        if (isIconBtn) {
            const icon = button.querySelector('.button-icon');
            const spinner = button.querySelector('.spinner-border');
            icon.classList.toggle('d-none', isLoading);
            spinner.classList.toggle('d-none', !isLoading);
        } else {
            const text = button.querySelector('.button-text');
            const spinner = button.querySelector('.spinner-border');
            text.classList.toggle('d-none', isLoading);
            spinner.classList.toggle('d-none', !isLoading);
        }
        button.disabled = isLoading;
    }
}