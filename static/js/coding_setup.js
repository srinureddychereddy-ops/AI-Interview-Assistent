/**
 * Interview.ai — Phase 1 Coding Round Setup & Readiness Controller
 * Handles network status monitoring, language selection, validation, and exit confirmation.
 */

document.addEventListener('DOMContentLoaded', function () {
    // --- 1. Network Status Monitoring ---
    const networkPill = document.getElementById('networkPill');
    const networkIcon = document.getElementById('networkIcon');
    const networkText = document.getElementById('networkText');

    function updateNetworkStatus() {
        const isOnline = navigator.onLine;
        if (!networkPill || !networkText) return;

        if (isOnline) {
            networkPill.className = 'badge bg-success-subtle text-success border border-success-subtle px-2.5 py-1.5 rounded-pill font-monospace d-inline-flex align-items-center gap-1.5';
            if (networkIcon) networkIcon.className = 'bi bi-wifi';
            networkText.textContent = 'Online';
        } else {
            networkPill.className = 'badge bg-danger-subtle text-danger border border-danger-subtle px-2.5 py-1.5 rounded-pill font-monospace d-inline-flex align-items-center gap-1.5';
            if (networkIcon) networkIcon.className = 'bi bi-wifi-off';
            networkText.textContent = 'Offline';
        }
    }

    updateNetworkStatus();
    window.addEventListener('online', updateNetworkStatus);
    window.addEventListener('offline', updateNetworkStatus);

    // --- 2. Language Selector ---
    const languageBtns = document.querySelectorAll('.language-option-btn');
    const selectedLanguageInput = document.getElementById('selectedLanguageInput');
    const summaryLanguageText = document.getElementById('summaryLanguageText');

    languageBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            languageBtns.forEach(function (b) { b.classList.remove('active'); });
            this.classList.add('active');

            const lang = this.getAttribute('data-language') || 'Python';
            if (selectedLanguageInput) {
                selectedLanguageInput.value = lang;
            }
            if (summaryLanguageText) {
                summaryLanguageText.textContent = lang;
            }
        });
    });

    // --- 2b. Questions & Duration Config Selectors ---
    const configBtns = document.querySelectorAll('.config-pill-btn');
    const selectedQuestionsInput = document.getElementById('selectedQuestionsInput');
    const selectedDurationInput = document.getElementById('selectedDurationInput');

    configBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            const configType = this.getAttribute('data-config');
            const val = this.getAttribute('data-value');

            // Deselect siblings with same data-config
            document.querySelectorAll(`.config-pill-btn[data-config="${configType}"]`).forEach(function (b) {
                b.classList.remove('active');
            });
            this.classList.add('active');

            if (configType === 'questions' && selectedQuestionsInput) {
                selectedQuestionsInput.value = val;
            } else if (configType === 'duration' && selectedDurationInput) {
                selectedDurationInput.value = val;
            }
        });
    });

    // --- 3. Exit Confirmation Modal ---
    const btnBack = document.getElementById('btnBack');
    const leaveModal = document.getElementById('leaveModal');
    const btnStay = document.getElementById('btnStay');
    const btnGoBack = document.getElementById('btnGoBack');

    function openLeaveModal() {
        if (leaveModal) {
            leaveModal.classList.remove('d-none');
            document.body.style.overflow = 'hidden';
        }
    }

    function closeLeaveModal() {
        if (leaveModal) {
            leaveModal.classList.add('d-none');
            document.body.style.overflow = '';
        }
    }

    if (btnBack) {
        btnBack.addEventListener('click', function (e) {
            e.preventDefault();
            openLeaveModal();
        });
    }

    if (btnStay) {
        btnStay.addEventListener('click', function () {
            closeLeaveModal();
        });
    }

    if (btnGoBack) {
        btnGoBack.addEventListener('click', function () {
            closeLeaveModal();
            if (window.history.length > 1 && document.referrer && document.referrer.includes(window.location.host)) {
                window.history.back();
            } else {
                window.location.href = '/dashboard';
            }
        });
    }

    // Close on backdrop click
    if (leaveModal) {
        leaveModal.addEventListener('click', function (e) {
            if (e.target === leaveModal) {
                closeLeaveModal();
            }
        });
    }

    // Close on Escape key
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && leaveModal && !leaveModal.classList.contains('d-none')) {
            closeLeaveModal();
        }
    });

    // --- 4. Start Coding Assessment Form Handler ---
    const startForm = document.getElementById('codingSetupForm');
    const btnStart = document.getElementById('btnStartAssessment');

    if (startForm) {
        startForm.addEventListener('submit', function (e) {
            const lang = selectedLanguageInput ? selectedLanguageInput.value : 'Python';
            
            // Show global loader if available
            if (typeof window.showLoader === 'function') {
                window.showLoader(`Preparing your ${lang} coding assessment environment...`);
            } else if (btnStart) {
                btnStart.setAttribute('disabled', 'true');
                btnStart.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Initializing Assessment...';
            }
        });
    }
});
