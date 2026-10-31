/**
 * ==========================================================================
 * InterviewAI Global Loading Controller
 * ==========================================================================
 */

(function () {
    const DEFAULT_MESSAGE = "Preparing your AI Interview...";

    /**
     * Display the global full-screen AI loading overlay.
     * @param {string} [message] - Custom loading status message.
     */
    function showLoader(message) {
        const overlay = document.getElementById("global-loader-overlay");
        const messageElem = document.getElementById("loader-message");

        if (messageElem) {
            messageElem.textContent = message || DEFAULT_MESSAGE;
        }

        if (overlay) {
            overlay.classList.remove("d-none");
            // Force browser reflow for smooth opacity transition
            void overlay.offsetWidth;
            overlay.classList.add("active");
            overlay.setAttribute("aria-hidden", "false");
        }
    }

    /**
     * Hide the global full-screen AI loading overlay.
     */
    function hideLoader() {
        const overlay = document.getElementById("global-loader-overlay");

        if (overlay && overlay.classList.contains("active")) {
            overlay.classList.remove("active");
            overlay.setAttribute("aria-hidden", "true");

            // Hide element from display flow after transition completes
            setTimeout(() => {
                if (!overlay.classList.contains("active")) {
                    overlay.classList.add("d-none");
                }
            }, 350);
        }
    }

    // Expose global methods on window object
    window.showLoader = showLoader;
    window.hideLoader = hideLoader;

    // Listen for window pagehide / beforeunload if desired or handle SPA navigation hooks
    window.addEventListener("pageshow", function () {
        // Ensure loader is hidden when navigating back via browser cache
        hideLoader();
    });
})();
