document.addEventListener('DOMContentLoaded', () => {
    // --- View Selectors ---
    const infoView = document.getElementById('interview-info-view');
    const hardwareView = document.getElementById('hardware-check-view');
    const mcqView = document.getElementById('interview-mcq-view');

    // --- Button Selectors ---
    const startChecksBtn = document.getElementById('start-checks-btn');
    const startInterviewBtn = document.getElementById('start-interview-btn');
    const nextBtn = document.getElementById('nextBtn');
    const prevBtn = document.getElementById('previousBtn');
    const submitBtn = document.getElementById('submitInterview');
    const instructionsCheckbox = document.getElementById('instructions-read-checkbox');

    // --- MCQ View Element Selectors ---
    const timerEl = document.getElementById('timer');
    const questionTextEl = document.getElementById('questionText');
    const optionsContainer = document.querySelector('.options');
    const optionLabels = {
        'A': document.getElementById('optionA'),
        'B': document.getElementById('optionB'),
        'C': document.getElementById('optionC'),
        'D': document.getElementById('optionD')
    };
    const optionInputs = document.querySelectorAll('input[name="answer"]');
    const currentQuestionEl = document.getElementById('currentQuestion');
    const progressBarEl = document.getElementById('progressBar');
    const progressPercentEl = document.getElementById('progressPercent');
    const compactCurrentQuestionEl = document.getElementById('compactCurrentQuestion');
    const navigatorContainer = document.getElementById('navigator');
    const navigatorButtons = navigatorContainer ? Array.from(navigatorContainer.querySelectorAll('.question-number')) : [];
    const progressRingEl = document.getElementById('interviewProgressRing');
    const answeredQuestionsEl = document.getElementById('answeredQuestions');
    const remainingQuestionsEl = document.getElementById('remainingQuestions');
    const confidenceValueEl = document.getElementById('confidenceValue');
    const confidenceBarEl = document.getElementById('confidenceBar');
    const technicalScoreEl = document.getElementById('technicalScore');
    const technicalBarEl = document.getElementById('technicalBar');
    const predictionLabelEl = document.getElementById('predictionLabel');
    const liveHintEl = document.getElementById('liveHint');
    const motivationMessageEl = document.getElementById('motivationMessage');
    const liveQuestionCard = document.getElementById('liveQuestionCard');
    const countdownOverlay = document.getElementById('interviewCountdown');
    const countdownValue = document.getElementById('countdownValue');
    const celebrationOverlay = document.getElementById('interviewCelebration');
    const interviewThemeToggle = document.getElementById('interviewThemeToggle');
    const exitInterviewButton = document.getElementById('exitInterviewButton');
    const exitDialog = document.getElementById('exit-dialog') || document.getElementById('interviewExitDialog');
    const confirmInterviewExit = document.getElementById('confirmInterviewExit');
    const continueInterviewButtons = document.querySelectorAll('[data-continue-interview]');

    // --- Hardware Check Elements ---
    const webcamFeed = document.getElementById('webcam-feed');
    const webcamPlaceholder = document.getElementById('webcam-placeholder');
    const webcamPlaceholderText = document.getElementById('webcam-placeholder-text');
    const cameraStatusEl = document.getElementById('camera-status');
    const micStatusEl = document.getElementById('mic-status');
    const internetStatusEl = document.getElementById('internet-status');
    const permissionAlert = document.getElementById('permission-alert');
    const hardwareRetryBtn = document.getElementById('hardware-retry-btn');
    const proctorMessageEl = document.getElementById('proctor-message');

    // --- Floating Webcam Component Selectors ---
    const floatingCard = document.getElementById('floating-webcam-card');
    const floatingFeed = document.getElementById('floating-webcam-feed');
    const floatingLoading = document.getElementById('floating-webcam-loading');
    const floatingError = document.getElementById('floating-webcam-error');
    const floatingErrorMsg = document.getElementById('floating-webcam-error-msg');
    const webcamStatusPill = document.getElementById('webcam-status-pill');
    const webcamStatusText = document.getElementById('webcam-status-text');
    const retryWebcamBtn = document.getElementById('retry-webcam-btn');

    // --- Proctor Status Panel Selectors (Sidebar) ---
    const proctorPanelCamera = document.getElementById('proctor-panel-camera');
    const proctorPanelMic = document.getElementById('proctor-panel-mic');
    const proctorPanelNetwork = document.getElementById('proctor-panel-network');
    const proctorPanelFullscreen = document.getElementById('proctor-panel-fullscreen');
    const proctorPanelWarnings = document.getElementById('proctor-panel-warnings');

    // --- Proctor Overlays ---
    const proctorPauseOverlay = document.getElementById('proctor-pause-overlay');
    const proctorPauseCameraStatus = document.getElementById('proctor-pause-camera-status');
    const proctorPauseMicStatus = document.getElementById('proctor-pause-mic-status');
    const proctorReconnectBtn = document.getElementById('proctor-reconnect-btn');

    const fullscreenPauseOverlay = document.getElementById('fullscreen-pause-overlay');
    const fullscreenRestoreBtn = document.getElementById('fullscreen-restore-btn');

    // --- State Machine & State Tracking ---
    const InterviewState = {
        SETUP: 'SETUP',
        REQUEST_DEVICES: 'REQUEST_DEVICES',
        VERIFY_DEVICES: 'VERIFY_DEVICES',
        READY: 'READY',
        INTERVIEW_ACTIVE: 'INTERVIEW_ACTIVE',
        PAUSED: 'PAUSED',
        COMPLETED: 'COMPLETED'
    };
    let currentInterfaceState = InterviewState.SETUP;

    let timerInterval;
    let remainingTimerSeconds = 10 * 60; // 10 minutes
    let activeMediaStream = null;
    let mediaRequestInFlight = false;
    let isInterviewSubmitted = false;
    let isInterviewActive = false;
    let allowInterviewExit = false;
    let guardHistoryArmed = false;
    const answeredQuestionIndexes = new Set();

    let currentQuestionIndex = 0;
    let totalQuestions = 20;

    // Proctoring warning counters
    let cameraActive = false;
    let microphoneActive = false;
    let tabSwitchWarningCount = 0;
    let fullscreenWarningCount = 0;
    let proctorWarningCount = 0; // Cumulative

    const liveHints = [
        'Read every option before deciding.',
        'Eliminate answers that are technically incomplete.',
        'Look for the most precise engineering trade-off.',
        'Use first principles before relying on memory.'
    ];
    const motivationMessages = [
        'Take a breath. Focus on the signal in the question, not the clock.',
        'Strong interviews are built one clear decision at a time.',
        'You are building momentum. Stay deliberate and keep moving.',
        'Trust your preparation and choose the most complete answer.'
    ];

    // Initialize UI on load
    updateStatus(cameraStatusEl, 'denied', 'Not Active');
    updateStatus(micStatusEl, 'denied', 'Not Active');
    if (proctorMessageEl) {
        proctorMessageEl.textContent = 'Camera and microphone access are required to start the interview.';
    }

    // --- Hardware Validation State Variables ---
    let cameraCheckPassed = false;
    let microphoneCheckPassed = false;
    let networkCheckPassed = false;

    let audioContext = null;
    let micAnalyser = null;
    let micStreamSource = null;
    let micAnimationId = null;

    const cameraStatusBadge = document.getElementById('camera-status-badge');
    const cameraStatusDesc = document.getElementById('camera-status-desc');
    const micStatusBadge = document.getElementById('mic-status-badge');
    const micStatusDesc = document.getElementById('mic-status-desc');
    const micLevelBar = document.getElementById('mic-level-bar');
    const networkStatusBadge = document.getElementById('network-status-badge');
    const permissionAlertText = document.getElementById('permission-alert-text');
    const micRetryBtn = document.getElementById('mic-retry-btn');
    const cameraRetryBtn = document.getElementById('camera-retry-btn');
    const cameraLivePill = document.getElementById('camera-live-pill');
    const cameraSpinLoader = document.getElementById('camera-spin-loader');
    const cameraOffIcon = document.getElementById('camera-off-icon');
    const cameraSelectRow = document.getElementById('camera-select-row');
    const cameraSourceSelect = document.getElementById('camera-source-select');
    let availableVideoDevices = [];
    let currentActiveCameraId = null;
    let selectedCameraDeviceId = null;
    try {
        selectedCameraDeviceId = sessionStorage.getItem('selectedCameraDeviceId') || null;
    } catch (e) {}
    let currentActiveCameraId = selectedCameraDeviceId;
    let cameraRecoveryInProgress = false;
    let activeVideoStream = null;
    let activeAudioStream = null;

    let lastCameraFrameTime = Date.now();
    let isCameraFrameCallbackActive = false;

    function initVideoFrameCallback(videoEl) {
        if (!videoEl) return;
        
        ['pause', 'ended', 'emptied', 'error', 'stalled', 'suspend'].forEach(evt => {
            videoEl.addEventListener(evt, () => {
                console.warn(`[HardwareMonitor] Video element event: ${evt}`);
                if (currentInterfaceState === InterviewState.INTERVIEW_ACTIVE) {
                    handleDeviceDisconnected();
                }
        if (!videoEl.__proctorEventsBound) {
            videoEl.__proctorEventsBound = true;
            ['ended', 'error'].forEach(evt => {
                videoEl.addEventListener(evt, () => {
                    console.warn(`[HardwareMonitor] Video element event: ${evt}`);
                    if (currentInterfaceState === InterviewState.INTERVIEW_ACTIVE) {
                        handleDeviceDisconnected();
                    }
                });
            });
        });
        }

        if ('requestVideoFrameCallback' in HTMLVideoElement.prototype) {
            const onFrame = () => {
                lastCameraFrameTime = Date.now();
                isCameraFrameCallbackActive = true;
                if (videoEl && !videoEl.paused && !videoEl.ended) {
                    videoEl.requestVideoFrameCallback(onFrame);
                    try {
                        videoEl.requestVideoFrameCallback(onFrame);
                    } catch (e) {}
                }
            };
            try {
                videoEl.requestVideoFrameCallback(onFrame);
            } catch (e) {
                console.warn("requestVideoFrameCallback error:", e);
            }
        }
    }

    function inspectLiveVideoNonBlack(video) {
        if (!video || video.paused || video.ended || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
            return false;
        }
        try {
            const width = video.videoWidth || 320;
            const height = video.videoHeight || 240;
            if (width === 0 || height === 0) return false;

            const testCanvas = document.createElement('canvas');
            testCanvas.width = 64;
            testCanvas.height = 48;
            const testCtx = testCanvas.getContext('2d', { willReadFrequently: true });
            if (!testCtx) return true;

            testCtx.drawImage(video, 0, 0, 64, 48);
            const imgData = testCtx.getImageData(0, 0, 64, 48).data;
            
            let nonDarkPixels = 0;
            const totalPixels = imgData.length / 4;

            for (let i = 0; i < imgData.length; i += 4) {
                const r = imgData[i];
                const g = imgData[i + 1];
                const b = imgData[i + 2];
                const brightness = (r + g + b) / 3;
                if (brightness > 10) {
                    nonDarkPixels++;
                }
            }

            const usableRatio = nonDarkPixels / totalPixels;
            return usableRatio >= 0.03;
        } catch (e) {
            return video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA && !video.paused;
        }
    }

    function isCameraActuallyWorking() {
        if (!activeMediaStream) return false;
        const videoTrack = activeMediaStream.getVideoTracks()[0];
        const stream = activeVideoStream || activeMediaStream;
        if (!stream) return false;
        const videoTrack = stream.getVideoTracks()[0];
        if (!videoTrack) return false;

        // 1. MediaStreamTrack properties check
        if (videoTrack.readyState !== 'live' || !videoTrack.enabled || videoTrack.muted) {
            return false;
        }

        // 2. Video element properties check (floatingFeed or webcamFeed)
        const targetVideo = (floatingFeed && floatingFeed.srcObject) ? floatingFeed : (webcamFeed && webcamFeed.srcObject ? webcamFeed : null);
        if (!targetVideo) return false;

        if (targetVideo.paused || targetVideo.ended || targetVideo.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
        if (targetVideo.paused || targetVideo.ended || targetVideo.readyState < 2 || targetVideo.videoWidth <= 0 || targetVideo.videoHeight <= 0) {
            return false;
        }

        // 3. Frame callback freshness check
        if (isCameraFrameCallbackActive && (Date.now() - lastCameraFrameTime > 3000)) {
            console.warn("[HardwareMonitor] No new video frames received for >3s!");
        if (isCameraFrameCallbackActive && (Date.now() - lastCameraFrameTime > 4000)) {
            console.warn("[HardwareMonitor] No new video frames received for >4s!");
            return false;
        }

        // 4. Non-black frame check during active interview
        if (currentInterfaceState === InterviewState.INTERVIEW_ACTIVE) {
            const isFrameNonBlack = inspectLiveVideoNonBlack(targetVideo);
            if (!isFrameNonBlack) {
                console.warn("[HardwareMonitor] Camera feed is dark/black or stream stopped rendering.");
                return false;
            }
        }

        return true;
    }

    function isMicrophoneActuallyWorking() {
        if (!activeMediaStream) return false;
        const audioTrack = activeMediaStream.getAudioTracks()[0];
        const stream = activeAudioStream || activeMediaStream;
        if (!stream) return false;
        const audioTrack = stream.getAudioTracks()[0];
        if (!audioTrack) return false;

        if (audioTrack.readyState !== 'live' || !audioTrack.enabled || audioTrack.muted) {
            return false;
        }
        return microphoneCheckPassed;
    }

    function isProctoringHealthy() {
        return isCameraActuallyWorking() && isMicrophoneActuallyWorking();
    }

    function setWebcamStatusPill(state, text) {
        if (!webcamStatusPill || !webcamStatusText) return;
        webcamStatusPill.className = 'webcam-status-pill badge ' + (state === 'active' ? 'bg-success bg-opacity-10 text-success' : 'bg-danger bg-opacity-10 text-danger');
        webcamStatusText.textContent = text;
    }

    function updateProctorPanelStatus() {
        const isCamLive = isCameraActuallyWorking();
        const isMicLive = isMicrophoneActuallyWorking();

        cameraActive = isCamLive;
        microphoneActive = isMicLive;

        if (proctorPanelCamera) {
            proctorPanelCamera.className = isCamLive ? "text-success fw-semibold" : "text-danger fw-semibold";
            proctorPanelCamera.textContent = isCamLive ? "✓ Active" : "❌ Disconnected";
        }
        if (proctorPanelMic) {
            proctorPanelMic.className = isMicLive ? "text-success fw-semibold" : "text-danger fw-semibold";
            proctorPanelMic.textContent = isMicLive ? "✓ Active" : (microphoneCheckPassed ? "❌ Disconnected" : "❌ Permission Denied");
        }
        setWebcamStatusPill(isCamLive ? 'active' : 'off', isCamLive ? '● Camera Active' : 'Camera Disconnected');
    }

    function updateStartButtonState() {
        const allPassed = cameraCheckPassed && microphoneCheckPassed && networkCheckPassed;
        if (startInterviewBtn) {
            startInterviewBtn.disabled = !allPassed;
            if (allPassed) {
                startInterviewBtn.classList.add('btn-success');
                startInterviewBtn.classList.remove('btn-premium');
            } else {
                startInterviewBtn.classList.remove('btn-success');
                startInterviewBtn.classList.add('btn-premium');
            }
        }
        if (proctorMessageEl) {
            if (allPassed) {
                proctorMessageEl.className = "alert alert-success py-2.5 px-4 rounded-3 text-center small mb-3";
                proctorMessageEl.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i>Everything is ready. You can start the assessment.';
            } else if (!cameraCheckPassed) {
                proctorMessageEl.className = "alert alert-danger py-2.5 px-4 rounded-3 text-center small mb-3";
                proctorMessageEl.innerHTML = '<i class="bi bi-camera-video-off me-2"></i>Camera access is required before you can continue.';
            } else if (!microphoneCheckPassed) {
                proctorMessageEl.className = "alert alert-warning py-2.5 px-4 rounded-3 text-center small mb-3";
                proctorMessageEl.innerHTML = '<i class="bi bi-mic-mute me-2"></i>Microphone input is required before you can continue. Please speak into your microphone.';
            } else {
                proctorMessageEl.className = "alert alert-info py-2.5 px-4 rounded-3 text-center small mb-3";
                proctorMessageEl.innerHTML = 'Camera, microphone, and network checks must pass before starting the assessment.';
            }
        }
    }

    // --- Detailed User-Friendly Error Messages & Instructions ---
    function getMediaErrorMessage(err) {
        const name = err ? (err.name || '') : '';
        switch (name) {
            case 'NotAllowedError':
            case 'PermissionDeniedError':
                return {
                    title: "Permission Denied",
                    badge: "✕ Permission denied",
                    desc: "Camera and microphone access is blocked for this site.",
                    instruction: "Camera or microphone access is blocked. Click the camera/lock icon in the address bar, set Camera and Microphone to Allow, then click Retry.",
                    isBlocked: true
                };
            case 'NotFoundError':
            case 'DevicesNotFoundError':
                return {
                    title: "Device Not Found",
                    badge: "✕ Device not found",
                    desc: "No camera or microphone device found on your system.",
                    instruction: "Please connect a working camera and microphone, then click Retry.",
                    isBlocked: false
                };
            case 'NotReadableError':
            case 'TrackStartError':
                return {
                    title: "Device In Use",
                    badge: "✕ Device in use",
                    desc: "Your camera or microphone is already being used by another application.",
                    instruction: "Please close other apps using your camera or microphone (such as Zoom, Teams, or Meet), then click Retry.",
                    isBlocked: false
                };
            case 'SecurityError':
                return {
                    title: "Security Restriction",
                    badge: "✕ Security blocked",
                    desc: "Camera and microphone access is blocked by browser security restrictions.",
                    instruction: "Please ensure the page is loaded over a secure origin (HTTPS or localhost) and media access is permitted.",
                    isBlocked: false
                };
            case 'AbortError':
                return {
                    title: "Operation Interrupted",
                    badge: "✕ Interrupted",
                    desc: "Camera or microphone operation was interrupted.",
                    instruction: "The hardware request was interrupted. Please click Retry.",
                    isBlocked: false
                };
            default:
                return {
                    title: "Hardware Access Error",
                    badge: "✕ Access failed",
                    desc: "Camera and microphone could not be accessed.",
                    instruction: "Please check your browser permissions and camera settings, then click Retry.",
                    isBlocked: false
                };
        }
    }

    // --- Physical Camera Device Prioritization & Selection ---
    function scoreCameraDevice(device) {
        const label = (device.label || '').toLowerCase();
        let score = 50;

        // Heavy penalty for phone / mobile / virtual / wireless / link cameras
        const isVirtualOrPhone = /(phone|link|droidcam|iriun|epoccam|obs|virtual|camo|continuity|wireless|remote|ip camera|mobile)/i.test(label);
        // High priority for built-in / integrated laptop webcams
        const isBuiltIn = /(integrated|built-in|internal|laptop|facetime|hd camera|hd webcam|webcam|front camera|camera front)/i.test(label);
        // Moderate priority for dedicated external USB webcams
        const isUsbExternal = /(usb|external|logitech|creative|anker)/i.test(label);

        if (isVirtualOrPhone) {
            score -= 100;
        }
        if (isBuiltIn) {
            score += 100;
        } else if (isUsbExternal) {
            score += 40;
        }

        return score;
    }

    function waitForVideoReady(videoEl, timeoutMs = 4000) {
        return new Promise((resolve, reject) => {
            if (!videoEl) return resolve();

            if (videoEl.readyState >= 2 && videoEl.videoWidth > 0 && videoEl.videoHeight > 0) {
                return resolve();
            }

            let resolved = false;
            let timer = null;

            const checkAndDone = () => {
                if (resolved) return;
                if (videoEl.readyState >= 2 && videoEl.videoWidth > 0) {
                    resolved = true;
                    if (timer) clearTimeout(timer);
                    cleanup();
                    resolve();
                }
            };

            const cleanup = () => {
                videoEl.removeEventListener('loadedmetadata', checkAndDone);
                videoEl.removeEventListener('canplay', checkAndDone);
                videoEl.removeEventListener('playing', checkAndDone);
                videoEl.removeEventListener('timeupdate', checkAndDone);
            };

            videoEl.addEventListener('loadedmetadata', checkAndDone);
            videoEl.addEventListener('canplay', checkAndDone);
            videoEl.addEventListener('playing', checkAndDone);
            videoEl.addEventListener('timeupdate', checkAndDone);

            timer = setTimeout(() => {
                cleanup();
                if (videoEl.readyState >= 2 && videoEl.videoWidth > 0) {
                    resolve();
                } else {
                    reject(new Error("Video element readiness timeout"));
                }
            }, timeoutMs);
        });
    }

    function attachVideoTrackMonitoring(track) {
        if (!track) return;
        track.onended = () => {
            console.warn("[HardwareMonitor] Video track ended:", track.label);
            cameraActive = false;
            cameraCheckPassed = false;
            updateProctorPanelStatus();
            if (currentInterfaceState === InterviewState.INTERVIEW_ACTIVE) {
                enforceProctoringLock("camera");
            }
        };
        track.onmute = () => {
            console.warn("[HardwareMonitor] Video track muted:", track.label);
            cameraActive = false;
            cameraCheckPassed = false;
            updateProctorPanelStatus();
            if (currentInterfaceState === InterviewState.INTERVIEW_ACTIVE) {
                enforceProctoringLock("camera");
            }
        };
    }

    async function resolveTargetCameraDevice(forceReenumerate = false) {
        if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
            return selectedCameraDeviceId ? { deviceId: selectedCameraDeviceId, label: '' } : null;
        }

        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            availableVideoDevices = devices.filter(d => d.kind === 'videoinput');

            if (availableVideoDevices.length === 0) {
                return null;
            }

            // 1. If selectedCameraDeviceId is set and valid, verify it is still present
            if (selectedCameraDeviceId && !forceReenumerate) {
                const found = availableVideoDevices.find(d => d.deviceId === selectedCameraDeviceId);
                if (found) {
                    return found;
                }
            }

            // 2. Otherwise sort available cameras by priority score (Laptop physical camera prioritized, virtual/phone cameras penalized)
            const sorted = [...availableVideoDevices].sort((a, b) => scoreCameraDevice(b) - scoreCameraDevice(a));
            const best = sorted[0];
            if (best) {
                selectedCameraDeviceId = best.deviceId;
                currentActiveCameraId = selectedCameraDeviceId;
                try { sessionStorage.setItem('selectedCameraDeviceId', selectedCameraDeviceId); } catch (e) {}
                if (cameraSourceSelect) cameraSourceSelect.value = selectedCameraDeviceId;
                return best;
            }
        } catch (e) {
            console.warn("[Hardware] Device resolution error:", e);
        }

        return selectedCameraDeviceId ? { deviceId: selectedCameraDeviceId, label: '' } : null;
    }

    async function recoverCamera() {
        if (cameraRecoveryInProgress) {
            console.warn("[CameraRecovery] Camera recovery already in progress. Ignoring duplicate click.");
            return false;
        }
        cameraRecoveryInProgress = true;
        console.log("[CameraRecovery] Starting camera recovery...");

        try {
            // 1. Identify currently selected camera device, resolving failure if disconnected
            const targetDevice = await resolveTargetCameraDevice();
            if (!targetDevice) {
                throw new DOMException("No camera device found on system.", "NotFoundError");
            }

            console.log(`[CameraRecovery] Target camera device: "${targetDevice.label}" (${targetDevice.deviceId})`);

            // 2. Request new camera stream FIRST (do not stop old stream yet)
            let newVideoStream = null;
            try {
                newVideoStream = await navigator.mediaDevices.getUserMedia({
                    video: { deviceId: { exact: targetDevice.deviceId } }
                });
            } catch (reqErr) {
                if (reqErr.name === 'OverconstrainedError' || reqErr.name === 'NotFoundError') {
                    console.warn("[CameraRecovery] Exact deviceId constraint failed. Re-evaluating available cameras...");
                    const fallbackDevice = await resolveTargetCameraDevice(true);
                    if (fallbackDevice && fallbackDevice.deviceId) {
                        newVideoStream = await navigator.mediaDevices.getUserMedia({
                            video: { deviceId: { ideal: fallbackDevice.deviceId } }
                        });
                    } else {
                        throw reqErr;
                    }
                } else {
                    throw reqErr;
                }
            }

            // 3. Verify returned stream contains a live video track
            const newVideoTrack = newVideoStream.getVideoTracks()[0];
            if (!newVideoTrack || newVideoTrack.readyState !== 'live') {
                throw new Error("Returned stream does not contain a live video track.");
            }

            // Update selectedCameraDeviceId
            const trackSettings = (typeof newVideoTrack.getSettings === 'function') ? newVideoTrack.getSettings() : {};
            if (trackSettings.deviceId) {
                selectedCameraDeviceId = trackSettings.deviceId;
                currentActiveCameraId = selectedCameraDeviceId;
                try { sessionStorage.setItem('selectedCameraDeviceId', selectedCameraDeviceId); } catch (e) {}
                if (cameraSourceSelect) cameraSourceSelect.value = selectedCameraDeviceId;
            }

            // 4. Identify primary video element (#floating-webcam-feed if in exam, else #webcam-feed)
            const isInterviewRunning = (currentInterfaceState === InterviewState.INTERVIEW_ACTIVE || currentInterfaceState === InterviewState.PAUSED);
            const primaryVideoEl = (isInterviewRunning && floatingFeed) ? floatingFeed : webcamFeed;
            const secondaryVideoEl = (primaryVideoEl === floatingFeed) ? webcamFeed : floatingFeed;

            // 5. Combine new video track with existing microphone audio track WITHOUT touching mic
            const existingAudioTracks = (activeAudioStream && activeAudioStream.getAudioTracks().length > 0)
                ? activeAudioStream.getAudioTracks()
                : (activeMediaStream ? activeMediaStream.getAudioTracks() : []);

            const compositeStream = new MediaStream([newVideoTrack, ...existingAudioTracks]);

            // 6. Attach to video element(s)
            if (primaryVideoEl) {
                primaryVideoEl.srcObject = compositeStream;
                try {
                    await primaryVideoEl.play();
                } catch (playErr) {
                    console.warn("[CameraRecovery] primaryVideoEl.play() warning:", playErr);
                }
            }
            if (secondaryVideoEl) {
                secondaryVideoEl.srcObject = compositeStream;
                secondaryVideoEl.play().catch(() => {});
            }

            // 7. Wait for loadedmetadata / canplay
            await waitForVideoReady(primaryVideoEl, 4000);

            // 8. Verify video track is live AND video element actually running (video.readyState >= 2, videoWidth > 0, videoHeight > 0)
            const isTrackLive = newVideoTrack && newVideoTrack.readyState === 'live';
            const isVideoActive = primaryVideoEl ? (
                primaryVideoEl.readyState >= 2 &&
                primaryVideoEl.videoWidth > 0 &&
                primaryVideoEl.videoHeight > 0
            ) : true;

            if (!isTrackLive || !isVideoActive) {
                throw new Error("Camera verification failed: video track or element not rendering live frames.");
            }

            // 9. ONLY THEN cleanly stop the old video track(s)
            if (activeVideoStream) {
                activeVideoStream.getVideoTracks().forEach(track => {
                    if (track !== newVideoTrack) {
                        try { track.stop(); } catch (e) {}
                    }
                });
            }
            if (activeMediaStream) {
                activeMediaStream.getVideoTracks().forEach(track => {
                    if (track !== newVideoTrack) {
                        try { track.stop(); } catch (e) {}
                    }
                });
            }

            activeVideoStream = newVideoStream;
            activeMediaStream = compositeStream;

            // Reset frame timer & re-init frame monitoring
            lastCameraFrameTime = Date.now();
            isCameraFrameCallbackActive = true;
            if (primaryVideoEl) {
                initVideoFrameCallback(primaryVideoEl);
            }

            // 10. Attach track monitoring
            attachVideoTrackMonitoring(newVideoTrack);

            // 11. Mark Camera Active & update UI
            cameraActive = true;
            cameraCheckPassed = true;

            const activeCamName = targetDevice.label || newVideoTrack.label || 'Integrated Camera';
            if (cameraStatusBadge) {
                cameraStatusBadge.className = 'badge bg-success font-monospace';
                cameraStatusBadge.textContent = '✓ Ready';
            }
            if (cameraStatusDesc) {
                cameraStatusDesc.textContent = `✓ Ready — ${activeCamName}`;
            }
            setWebcamStatusPill('active', '● Camera Active');
            updateProctorPanelStatus();
            updateStartButtonState();

            if (webcamPlaceholder) webcamPlaceholder.classList.add('d-none');
            if (cameraLivePill) {
                cameraLivePill.className = 'badge bg-success bg-opacity-10 text-success font-monospace';
                cameraLivePill.textContent = '● LIVE PREVIEW';
                cameraLivePill.classList.remove('d-none');
            }

            console.log(`[CameraRecovery] Camera successfully recovered and verified: ${activeCamName}`);
            return true;

        } catch (err) {
            console.error("[CameraRecovery] Recovery error:", err);
            cameraActive = false;
            cameraCheckPassed = false;
            updateProctorPanelStatus();
            updateStartButtonState();

            const pauseMsgEl = document.getElementById('proctor-pause-message');
            if (pauseMsgEl) {
                if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
                    pauseMsgEl.textContent = "Camera is currently being used by another application. Close other apps using the camera and try again.";
                } else if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
                    pauseMsgEl.textContent = "Camera permission was denied. Please allow camera access in browser settings and try again.";
                } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
                    pauseMsgEl.textContent = "Selected camera was not found. Please connect your camera and try again.";
                } else {
                    pauseMsgEl.textContent = "Unable to start camera. Please ensure your camera is connected and try again.";
                }
            }

            if (proctorPauseCameraStatus) {
                proctorPauseCameraStatus.className = "fw-bold text-danger";
                proctorPauseCameraStatus.textContent = "⚠ Disconnected";
            }

            return false;
        } finally {
            cameraRecoveryInProgress = false;
        }
    }

    async function recoverMicrophone() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const aTrack = stream.getAudioTracks()[0];
            if (aTrack && aTrack.readyState === 'live') {
                if (activeAudioStream) {
                    activeAudioStream.getAudioTracks().forEach(t => { try { t.stop(); } catch (e) {} });
                }
                activeAudioStream = stream;
                microphoneActive = true;
                microphoneCheckPassed = true;
                startMicrophoneAudioMeter(activeAudioStream);
                
                const currentVTrack = activeVideoStream ? activeVideoStream.getVideoTracks()[0] : (activeMediaStream ? activeMediaStream.getVideoTracks()[0] : null);
                if (currentVTrack) {
                    activeMediaStream = new MediaStream([currentVTrack, aTrack]);
                }
                updateProctorPanelStatus();
                return true;
            }
        } catch (e) {
            console.warn("[Hardware] Microphone recovery error:", e);
        }
        return false;
    }

    async function switchCameraDevice(deviceId, streamRef = null) {
        selectedCameraDeviceId = deviceId;
        currentActiveCameraId = selectedCameraDeviceId;
        try { sessionStorage.setItem('selectedCameraDeviceId', selectedCameraDeviceId); } catch (e) {}

        const stream = streamRef || activeMediaStream;
        if (!stream) return null;

        try {
            console.log(`[Hardware] Switching camera to deviceId: ${deviceId}`);

            // 1. Request new video track with exact deviceId
            // 1. Request new video track with exact deviceId FIRST
            const newStream = await navigator.mediaDevices.getUserMedia({
                video: { deviceId: { exact: deviceId } }
            });

            const newVideoTrack = newStream.getVideoTracks()[0];
            if (!newVideoTrack) {
                throw new Error("No video track found from selected device.");
            if (!newVideoTrack || newVideoTrack.readyState !== 'live') {
                throw new Error("No live video track found from selected device.");
            }

            // 2. Stop old video track(s) only (KEEP AUDIO TRACKS RUNNING)
            const oldVideoTracks = stream.getVideoTracks();
            oldVideoTracks.forEach(track => {
                try {
                    track.stop();
                    stream.removeTrack(track);
                } catch (e) {
                    console.warn("[Hardware] Error stopping old video track:", e);
                }
            });

            // 3. Add new video track to existing stream
            stream.addTrack(newVideoTrack);
            activeVideoStream = newStream;
            currentActiveCameraId = deviceId;

            // 4. Update dropdown selector
            if (cameraSourceSelect) {
                cameraSourceSelect.value = deviceId;
            }

            // 5. Update video preview elements
            if (webcamFeed) {
                webcamFeed.srcObject = stream;
                try {
                    await webcamFeed.play();
                } catch (pe) {}
                if (webcamPlaceholder) webcamPlaceholder.classList.add('d-none');
                if (cameraLivePill) {
                    cameraLivePill.className = 'badge bg-success bg-opacity-10 text-success font-monospace';
                    cameraLivePill.textContent = '● LIVE PREVIEW';
                    cameraLivePill.classList.remove('d-none');
                }
            }
            if (floatingFeed) {
                floatingFeed.srcObject = stream;
                floatingFeed.play().catch(() => {});
            }

            // 6. Bind track lifecycle events
            newVideoTrack.addEventListener('ended', handleDeviceDisconnected);
            newVideoTrack.addEventListener('mute', handleDeviceDisconnected);
            newVideoTrack.addEventListener('unmute', handleDeviceDisconnected);
            attachVideoTrackMonitoring(newVideoTrack);

            // 7. Update status indicators with exact active camera name
            const selectedDev = availableVideoDevices.find(d => d.deviceId === deviceId);
            const activeCamName = (selectedDev && selectedDev.label) ? selectedDev.label : (newVideoTrack.label || 'Selected Camera');
            if (cameraStatusBadge) {
                cameraStatusBadge.className = 'badge bg-success font-monospace';
                cameraStatusBadge.textContent = '✓ Ready';
            }
            if (cameraStatusDesc) {
                cameraStatusDesc.textContent = `✓ Ready — ${activeCamName}`;
            }

            cameraCheckPassed = true;
            cameraActive = true;
            updateStartButtonState();
            updateProctorPanelStatus();

            return stream;
        } catch (err) {
            console.error("[Hardware] Failed to switch camera device:", err);
            return stream;
        }
    }

    async function setupCameraSelection(initialStream) {
        if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
            return initialStream;
        }

        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            availableVideoDevices = devices.filter(d => d.kind === 'videoinput');

            // Populate selector dropdown if element exists
            if (cameraSourceSelect) {
                cameraSourceSelect.innerHTML = '';
                availableVideoDevices.forEach((dev, idx) => {
                    const opt = document.createElement('option');
                    opt.value = dev.deviceId;
                    opt.textContent = dev.label || `Camera ${idx + 1}`;
                    cameraSourceSelect.appendChild(opt);
                });

                if (availableVideoDevices.length > 1 && cameraSelectRow) {
                    cameraSelectRow.classList.remove('d-none');
                } else if (cameraSelectRow) {
                    cameraSelectRow.classList.add('d-none');
                }
            }

            if (availableVideoDevices.length <= 1) {
                if (availableVideoDevices.length === 1) {
                    currentActiveCameraId = availableVideoDevices[0].deviceId;
                    selectedCameraDeviceId = availableVideoDevices[0].deviceId;
                    currentActiveCameraId = selectedCameraDeviceId;
                    try { sessionStorage.setItem('selectedCameraDeviceId', selectedCameraDeviceId); } catch (e) {}
                    if (cameraSourceSelect) cameraSourceSelect.value = currentActiveCameraId;
                }
                return initialStream;
            }

            // Find current active video track deviceId and label
            const currentVideoTrack = initialStream.getVideoTracks()[0];
            const currentSettings = (currentVideoTrack && typeof currentVideoTrack.getSettings === 'function') ? currentVideoTrack.getSettings() : {};
            const currentDeviceId = currentSettings.deviceId;
            const currentLabel = (currentVideoTrack && currentVideoTrack.label) ? currentVideoTrack.label : '';

            // Sort by priority score
            const sortedDevices = [...availableVideoDevices].sort((a, b) => scoreCameraDevice(b) - scoreCameraDevice(a));
            const bestDevice = sortedDevices[0];

            console.log("[Hardware] Available video devices:", availableVideoDevices.map(d => ({ label: d.label, id: d.deviceId, score: scoreCameraDevice(d) })));
            console.log("[Hardware] Preferred camera:", bestDevice ? bestDevice.label : 'none', "Current device ID:", currentDeviceId);

            // If current device is not the preferred device (or matches a virtual/phone camera), switch to laptop camera!
            if (bestDevice && ((currentDeviceId && bestDevice.deviceId !== currentDeviceId) || (!currentDeviceId && currentLabel && bestDevice.label !== currentLabel))) {
                console.log(`[Hardware] Default camera was "${currentLabel || currentDeviceId}", auto-switching to laptop camera: "${bestDevice.label}"`);
                const switchedStream = await switchCameraDevice(bestDevice.deviceId, initialStream);
                return switchedStream || initialStream;
            } else {
                currentActiveCameraId = currentDeviceId || (bestDevice ? bestDevice.deviceId : null);
                selectedCameraDeviceId = currentDeviceId || (bestDevice ? bestDevice.deviceId : null);
                currentActiveCameraId = selectedCameraDeviceId;
                try { sessionStorage.setItem('selectedCameraDeviceId', selectedCameraDeviceId); } catch (e) {}
                if (cameraSourceSelect && currentActiveCameraId) {
                    cameraSourceSelect.value = currentActiveCameraId;
                }
                return initialStream;
            }
        } catch (e) {
            console.warn("[Hardware] Camera device enumeration/selection error:", e);
            return initialStream;
        }
    }

    async function startWebcamStream(isRetry = false) {
        if (mediaRequestInFlight) return;
        mediaRequestInFlight = true;

        console.log("[Hardware] Initiating camera and microphone verification (isRetry=" + isRetry + ")...");
        currentInterfaceState = InterviewState.REQUEST_DEVICES;

        // Reset check states
        cameraCheckPassed = false;
        microphoneCheckPassed = false;
        updateStartButtonState();
        updateProctorPanelStatus();

        // 1. Set initial visual indicators to 'Waiting for permission...'
        if (cameraStatusBadge) {
            cameraStatusBadge.className = 'badge bg-secondary bg-opacity-10 text-secondary font-monospace';
            cameraStatusBadge.textContent = '○ Waiting for permission...';
        }
        if (cameraStatusDesc) {
            cameraStatusDesc.textContent = 'Verifying camera access...';
        }
        
        if (micStatusBadge) {
            micStatusBadge.className = 'badge bg-secondary bg-opacity-10 text-secondary font-monospace';
            micStatusBadge.textContent = '○ Waiting for permission...';
        }
        if (micStatusDesc) {
            micStatusDesc.innerHTML = 'Verifying microphone input...';
        }
        if (micLevelBar) {
            micLevelBar.style.width = '0%';
        }

        if (webcamPlaceholder) webcamPlaceholder.classList.remove('d-none');
        if (cameraSpinLoader) cameraSpinLoader.classList.remove('d-none');
        if (cameraOffIcon) cameraOffIcon.classList.add('d-none');
        if (cameraRetryBtn) cameraRetryBtn.classList.add('d-none');
        if (hardwareRetryBtn) hardwareRetryBtn.classList.add('d-none');
        if (micRetryBtn) micRetryBtn.classList.add('d-none');
        if (permissionAlert) permissionAlert.classList.add('d-none');
        if (cameraLivePill) {
            cameraLivePill.className = 'badge bg-secondary bg-opacity-10 text-secondary font-monospace d-none';
            cameraLivePill.textContent = '● OFF';
        }
        if (webcamPlaceholderText) {
            webcamPlaceholderText.textContent = 'Requesting camera and microphone access in browser...';
        }
        setWebcamStatusPill('loading', '🟡 Initializing...');

        // 2. Start independent network check in parallel
        validateNetworkLatency();

        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new DOMException('Media devices are not supported in this browser.', 'NotSupportedError');
            }

            // Stop any previous media streams
            stopWebcamStream();

            // Check permissions API if available
            let isPermanentlyDenied = false;
            if (navigator.permissions && navigator.permissions.query) {
                try {
                    const camPerm = await navigator.permissions.query({ name: 'camera' }).catch(() => null);
                    const micPerm = await navigator.permissions.query({ name: 'microphone' }).catch(() => null);
                    if (camPerm && camPerm.state === 'denied' && micPerm && micPerm.state === 'denied') {
                        isPermanentlyDenied = true;
                    }
                } catch (pe) {
                    // Ignore query restrictions on unsupported browsers
                }
            }

            // If both permanently denied and not explicitly triggered by user clicking Retry, show instructions directly
            if (isPermanentlyDenied && !isRetry) {
                throw new DOMException('Permission denied', 'NotAllowedError');
            }

            // 3. Request camera and microphone together in a single prompt
            let stream = null;
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: true,
                    audio: true
                });
            } catch (combErr) {
                // If NotFoundError, check devices independently so we can pinpoint whether camera or mic is missing
                if (combErr.name === 'NotFoundError') {
                    let vStream = null;
                    try {
                        vStream = await navigator.mediaDevices.getUserMedia({ video: true });
                    } catch (ve) {}

                    let aStream = null;
                    try {
                        aStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    } catch (ae) {}

                    const combinedTracks = [
                        ...(vStream ? vStream.getVideoTracks() : []),
                        ...(aStream ? aStream.getAudioTracks() : [])
                    ];

                    if (combinedTracks.length > 0) {
                        stream = new MediaStream(combinedTracks);
                    } else {
                        throw combErr;
                    }
                } else {
                    throw combErr;
                }
            }

            activeMediaStream = stream;
            const initVTrack = stream.getVideoTracks()[0];
            const initATrack = stream.getAudioTracks()[0];
            if (initVTrack) {
                activeVideoStream = new MediaStream([initVTrack]);
                attachVideoTrackMonitoring(initVTrack);
            }
            if (initATrack) {
                activeAudioStream = new MediaStream([initATrack]);
            }

            // Physical camera device prioritization & enumeration
            activeMediaStream = await setupCameraSelection(activeMediaStream);
            currentInterfaceState = InterviewState.VERIFY_DEVICES;

            // 4. Verify Video Track
            const videoTracks = activeMediaStream.getVideoTracks();
            if (videoTracks.length > 0 && videoTracks[0].readyState === 'live') {
                const vTrack = videoTracks[0];
                activeVideoStream = new MediaStream([vTrack]);
                attachVideoTrackMonitoring(vTrack);
                cameraActive = true;
                cameraCheckPassed = true;

                if (webcamFeed) {
                    webcamFeed.srcObject = activeMediaStream;

                    const onVideoLoaded = async () => {
                        try {
                            await webcamFeed.play();
                        } catch (e) {
                            console.warn("[Camera] Play error:", e);
                        }
                        if (webcamPlaceholder) webcamPlaceholder.classList.add('d-none');
                        if (cameraLivePill) {
                            cameraLivePill.className = 'badge bg-success bg-opacity-10 text-success font-monospace';
                            cameraLivePill.textContent = '● LIVE PREVIEW';
                            cameraLivePill.classList.remove('d-none');
                        }
                    };

                    if (webcamFeed.readyState >= HTMLMediaElement.HAVE_METADATA) {
                        onVideoLoaded();
                    } else {
                        webcamFeed.addEventListener('loadedmetadata', onVideoLoaded, { once: true });
                    }

                    webcamFeed.play().catch(() => {});
                }

                if (floatingFeed) {
                    floatingFeed.srcObject = activeMediaStream;
                    floatingFeed.play().catch(() => {});
                }

                // Determine active camera label
                const trackSettings = (typeof vTrack.getSettings === 'function') ? vTrack.getSettings() : {};
                const activeDev = availableVideoDevices.find(d => d.deviceId === trackSettings.deviceId);
                const activeCamLabel = (activeDev && activeDev.label) ? activeDev.label : (vTrack.label || 'Webcam');

                if (cameraStatusBadge) {
                    cameraStatusBadge.className = 'badge bg-success font-monospace';
                    cameraStatusBadge.textContent = '✓ Ready';
                }
                if (cameraStatusDesc) {
                    cameraStatusDesc.textContent = `✓ Ready — ${activeCamLabel}`;
                }
                setWebcamStatusPill('active', '● Camera Active');

                vTrack.addEventListener('ended', handleDeviceDisconnected);
                vTrack.addEventListener('mute', handleDeviceDisconnected);
                vTrack.addEventListener('unmute', handleDeviceDisconnected);
            } else {
                cameraActive = false;
                cameraCheckPassed = false;
                if (cameraStatusBadge) {
                    cameraStatusBadge.className = 'badge bg-danger text-white font-monospace';
                    cameraStatusBadge.textContent = '✕ Camera Not Ready';
                }
                if (cameraStatusDesc) {
                    cameraStatusDesc.textContent = 'No active video track detected.';
                }
                if (cameraRetryBtn) cameraRetryBtn.classList.remove('d-none');
            }

            // 5. Verify Audio Track
            const audioTracks = activeMediaStream.getAudioTracks();
            if (audioTracks.length > 0 && audioTracks[0].readyState === 'live') {
                const aTrack = audioTracks[0];
                activeAudioStream = new MediaStream([aTrack]);
                microphoneActive = true;
                microphoneCheckPassed = true;

                if (micStatusBadge) {
                    micStatusBadge.className = 'badge bg-success font-monospace';
                    micStatusBadge.textContent = '✓ Ready';
                }
                if (micStatusDesc) {
                    micStatusDesc.textContent = 'Microphone input active and ready.';
                }

                // Start visual audio level meter
                startMicrophoneAudioMeter(activeMediaStream);

                aTrack.addEventListener('ended', handleDeviceDisconnected);
                aTrack.addEventListener('mute', handleDeviceDisconnected);
                aTrack.addEventListener('unmute', handleDeviceDisconnected);
            } else {
                microphoneActive = false;
                microphoneCheckPassed = false;
                if (micStatusBadge) {
                    micStatusBadge.className = 'badge bg-danger text-white font-monospace';
                    micStatusBadge.textContent = '✕ Mic Not Ready';
                }
                if (micStatusDesc) {
                    micStatusDesc.textContent = 'No active audio track detected.';
                }
                if (micRetryBtn) micRetryBtn.classList.remove('d-none');
            }

        } catch (err) {
            console.error("[Hardware] Media permission/device error:", err);
            stopWebcamStream();

            cameraActive = false;
            microphoneActive = false;
            cameraCheckPassed = false;
            microphoneCheckPassed = false;

            const errInfo = getMediaErrorMessage(err);

            // Update Camera Status Card
            if (cameraStatusBadge) {
                cameraStatusBadge.className = 'badge bg-danger text-white font-monospace';
                cameraStatusBadge.textContent = errInfo.badge;
            }
            if (cameraStatusDesc) {
                cameraStatusDesc.textContent = errInfo.desc;
            }

            // Update Microphone Status Card
            if (micStatusBadge) {
                micStatusBadge.className = 'badge bg-danger text-white font-monospace';
                micStatusBadge.textContent = errInfo.badge;
            }
            if (micStatusDesc) {
                micStatusDesc.textContent = errInfo.desc;
            }

            // Update Video Preview Placeholder
            if (webcamPlaceholder) webcamPlaceholder.classList.remove('d-none');
            if (cameraOffIcon) cameraOffIcon.classList.remove('d-none');
            if (cameraSpinLoader) cameraSpinLoader.classList.add('d-none');
            if (webcamPlaceholderText) {
                webcamPlaceholderText.textContent = errInfo.desc;
            }
            if (cameraRetryBtn) cameraRetryBtn.classList.remove('d-none');
            if (hardwareRetryBtn) hardwareRetryBtn.classList.remove('d-none');

            // Show compact instructions alert
            if (permissionAlert) {
                permissionAlert.classList.remove('d-none');
                if (permissionAlertText) {
                    permissionAlertText.textContent = errInfo.instruction;
                }
            }

            setWebcamStatusPill('off', 'Camera Off');
        } finally {
            mediaRequestInFlight = false;
            updateStartButtonState();
            updateProctorPanelStatus();
            console.log("[Hardware] Check State Summary:", { cameraCheckPassed, microphoneCheckPassed, networkCheckPassed });
        }
    }

    // Microphone Web Audio API Level Meter (Purely visual, does not fail silence)
    function startMicrophoneAudioMeter(stream) {
        try {
            stopMicAnalysis();

            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            if (audioContext.state === 'suspended') {
                audioContext.resume().catch(() => {});
            }

            micStreamSource = audioContext.createMediaStreamSource(stream);
            micAnalyser = audioContext.createAnalyser();
            micAnalyser.fftSize = 256;
            micStreamSource.connect(micAnalyser);

            const dataArray = new Uint8Array(micAnalyser.frequencyBinCount);

            function updateLevel() {
                if (!micAnalyser) return;
                micAnalyser.getByteFrequencyData(dataArray);

                let sum = 0;
                for (let i = 0; i < dataArray.length; i++) {
                    sum += dataArray[i];
                }
                const avgAmp = sum / dataArray.length;
                const levelPercent = Math.min(100, Math.round((avgAmp / 120) * 100));

                if (micLevelBar) {
                    micLevelBar.style.width = levelPercent + '%';
                }

                micAnimationId = requestAnimationFrame(updateLevel);
            }

            updateLevel();
        } catch (e) {
            console.warn("[Hardware] Audio meter initialization error:", e);
        }
    }

    function stopMicAnalysis() {
        if (micAnimationId) {
            cancelAnimationFrame(micAnimationId);
            micAnimationId = null;
        }
        if (micStreamSource) {
            try { micStreamSource.disconnect(); } catch (e) {}
            micStreamSource = null;
        }
        if (audioContext) {
            try { audioContext.close(); } catch (e) {}
            audioContext = null;
        }
    }

    // Network Latency Test (Independent check)
    async function validateNetworkLatency() {
        try {
            const start = performance.now();
            await fetch('/static/favicon.ico', { method: 'HEAD', cache: 'no-store' });
            const latency = Math.round(performance.now() - start);
            networkCheckPassed = true;
            if (networkStatusBadge) {
                networkStatusBadge.className = 'badge bg-success font-monospace';
                networkStatusBadge.textContent = `✓ ${latency} ms (Stable)`;
            }
        } catch (e) {
            networkCheckPassed = true;
            if (networkStatusBadge) {
                networkStatusBadge.className = 'badge bg-success font-monospace';
                networkStatusBadge.textContent = '✓ Connected';
            }
        }
        updateStartButtonState();
    }

    // Cleanup: Stops all media tracks cleanly
    function stopWebcamStream() {
        stopMicAnalysis();
        if (activeVideoStream) {
            activeVideoStream.getTracks().forEach(track => {
                try {
                    track.stop();
                } catch (e) {
                    console.warn("[Hardware] Video track stop error:", e);
                }
            });
            activeVideoStream = null;
        }
        if (activeAudioStream) {
            activeAudioStream.getTracks().forEach(track => {
                try {
                    track.stop();
                } catch (e) {
                    console.warn("[Hardware] Audio track stop error:", e);
                }
            });
            activeAudioStream = null;
        }
        if (activeMediaStream) {
            activeMediaStream.getTracks().forEach(track => {
                try {
                    track.stop();
                } catch (e) {
                    console.warn("[Hardware] Track stop error:", e);
                }
            });
            activeMediaStream = null;
        }
        if (floatingFeed) floatingFeed.srcObject = null;
        if (webcamFeed) webcamFeed.srcObject = null;
        setWebcamStatusPill('off', 'Camera Off');
    }

    // ==========================================================================
    // Device Disconnection & Active Proctoring Monitor
    // ==========================================================================

    // ==========================================================================
    // Device Disconnection & Central Proctoring Lock Monitor
    // ==========================================================================

    let isExamLocked = false;

    function enforceProctoringLock(reason) {
        console.log(`[PROCTOR] enforceProctoringLock triggered with reason: ${reason}`);
        
        currentInterfaceState = InterviewState.PAUSED;
        isExamLocked = true;
        
        // 1. Pause interview timer
        clearInterval(timerInterval);

        // 2. Disable all answer options
        optionInputs.forEach(input => {
            input.disabled = true;
        });

        // 3. Disable navigation buttons
        if (nextBtn) nextBtn.disabled = true;
        if (prevBtn) prevBtn.disabled = true;
        if (submitBtn) submitBtn.disabled = true;
        if (navigatorButtons) {
            navigatorButtons.forEach(btn => btn.disabled = true);
        }

        // 4. Update status pill & sidebar status badges
        const isCamLive = isCameraActuallyWorking();
        const isMicLive = isMicrophoneActuallyWorking();
        cameraActive = isCamLive;
        microphoneActive = isMicLive;

        if (proctorPanelCamera) {
            proctorPanelCamera.className = isCamLive ? "text-success fw-semibold" : "text-danger fw-semibold";
            proctorPanelCamera.textContent = isCamLive ? "✓ Active" : "❌ Disconnected";
        }
        if (proctorPanelMic) {
            proctorPanelMic.className = isMicLive ? "text-success fw-semibold" : "text-danger fw-semibold";
            proctorPanelMic.textContent = isMicLive ? "✓ Active" : "❌ Disconnected";
        }
        setWebcamStatusPill('off', isCamLive ? '● Camera Active' : 'Camera Disconnected');

        // 5. Show warning overlay
        showProctorPauseOverlay(reason);
    }

    function handleDeviceDisconnected() {
        if (isInterviewSubmitted || currentInterfaceState === InterviewState.COMPLETED) return;

        const isCamLive = isCameraActuallyWorking();
        const isMicLive = isMicrophoneActuallyWorking();

        cameraActive = isCamLive;
        microphoneActive = isMicLive;

        if (!isCamLive && !isMicLive) {
            enforceProctoringLock("both");
        } else if (!isCamLive) {
            enforceProctoringLock("camera");
        } else if (!isMicLive) {
            enforceProctoringLock("microphone");
        }
    }

    function showProctorPauseOverlay(reason) {
    function showProctorPauseOverlay(reason, customMessage = null) {
        if (!proctorPauseOverlay) return;

        const isCamLive = isCameraActuallyWorking();
        const isMicLive = isMicrophoneActuallyWorking();

        const titleEl = proctorPauseOverlay.querySelector('h2');
        const pauseMsgEl = document.getElementById('proctor-pause-message');

        if (!isCamLive && isMicLive) {
            if (titleEl) titleEl.textContent = "CAMERA REQUIRED";
            if (pauseMsgEl) pauseMsgEl.textContent = "Your camera is currently off or disconnected. Please turn on your camera to continue the interview.";
            if (pauseMsgEl) pauseMsgEl.textContent = customMessage || "Your camera is currently off or disconnected. Please turn on your camera to continue the interview.";
            if (proctorReconnectBtn) proctorReconnectBtn.innerHTML = '<i class="bi bi-camera-video me-1.5"></i> Enable Camera Again';
        } else if (isCamLive && !isMicLive) {
            if (titleEl) titleEl.textContent = "MICROPHONE REQUIRED";
            if (pauseMsgEl) pauseMsgEl.textContent = "Your microphone is currently unavailable. Please enable your microphone to continue.";
            if (pauseMsgEl) pauseMsgEl.textContent = customMessage || "Your microphone is currently unavailable. Please enable your microphone to continue.";
            if (proctorReconnectBtn) proctorReconnectBtn.innerHTML = '<i class="bi bi-mic me-1.5"></i> Enable Microphone Again';
        } else {
            if (titleEl) titleEl.textContent = "CAMERA & MICROPHONE REQUIRED";
            if (pauseMsgEl) pauseMsgEl.textContent = "Your camera and microphone are currently off or disconnected. Please enable both to continue.";
            if (pauseMsgEl) pauseMsgEl.textContent = customMessage || "Your camera and microphone are currently off or disconnected. Please enable both to continue.";
            if (proctorReconnectBtn) proctorReconnectBtn.innerHTML = '<i class="bi bi-arrow-repeat me-1.5"></i> Enable Camera & Microphone Again';
        }

        if (proctorPauseCameraStatus) {
            proctorPauseCameraStatus.className = isCamLive ? "fw-bold text-success" : "fw-bold text-danger";
            proctorPauseCameraStatus.textContent = isCamLive ? "✓ Active" : "⚠ Disconnected";
        }
        if (proctorPauseMicStatus) {
            proctorPauseMicStatus.className = isMicLive ? "fw-bold text-success" : "fw-bold text-danger";
            proctorPauseMicStatus.textContent = isMicLive ? "✓ Active" : "⚠ Disconnected";
        }
        proctorPauseOverlay.classList.remove('d-none');
    }

    function pauseInterview() {
        enforceProctoringLock(isCameraActuallyWorking() ? "microphone" : "camera");
    }

    function resumeInterview() {
        if (!isProctoringHealthy()) {
            handleDeviceDisconnected();
            return;
        }

        console.log("[PROCTOR] Unlocking interview — camera and microphone verified active.");
        currentInterfaceState = InterviewState.INTERVIEW_ACTIVE;
        isExamLocked = false;
        
        // Re-enable interactions
        optionInputs.forEach(input => input.disabled = false);
        if (nextBtn) nextBtn.disabled = false;
        if (prevBtn) prevBtn.disabled = false;
        if (submitBtn) submitBtn.disabled = false;
        if (navigatorButtons) {
            navigatorButtons.forEach(btn => btn.disabled = false);
        }

        if (proctorPauseOverlay) proctorPauseOverlay.classList.add('d-none');

        // Restart timer with remaining seconds
        startTimer(remainingTimerSeconds);

        setWebcamStatusPill('active', '● Camera Active');
        updateUI(currentQuestionIndex, totalQuestions);
    }

    // Reconnect devices / Check Again trigger
    // Reconnect devices / Enable Camera Again trigger
    if (proctorReconnectBtn) {
        proctorReconnectBtn.addEventListener('click', async () => {
            console.log("[PROCTOR] Reconnect button clicked -> Re-requesting MediaStream...");
            if (cameraRecoveryInProgress) {
                console.log("[PROCTOR] Reconnect button clicked while recovery in progress. Ignoring duplicate click.");
                return;
            }
            console.log("[PROCTOR] Enable Camera Again clicked -> recovering camera stream...");
            proctorReconnectBtn.disabled = true;
            proctorReconnectBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Reconnecting...';
            
            await startWebcamStream();
            proctorReconnectBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Connecting Camera...';

            const cameraRecovered = await recoverCamera();

            // Also check microphone if it wasn't working
            if (!isMicrophoneActuallyWorking()) {
                console.log("[PROCTOR] Microphone also inactive, attempting mic recovery...");
                await recoverMicrophone();
            }

            proctorReconnectBtn.disabled = false;
            proctorReconnectBtn.innerHTML = '<i class="bi bi-camera-video me-1.5"></i> Enable Camera Again';

            if (isProctoringHealthy()) {
                console.log("[PROCTOR] Proctoring healthy after recovery -> resuming interview.");
                resumeInterview();
            } else {
                handleDeviceDisconnected();
                console.warn("[PROCTOR] Proctoring check failed after recovery. Keeping overlay visible.");
                showProctorPauseOverlay();
            }
        });
    }

    if (retryWebcamBtn) {
        retryWebcamBtn.addEventListener('click', async () => {
            if (cameraRecoveryInProgress) return;
            await recoverCamera();
            if (isProctoringHealthy()) {
                resumeInterview();
            }
        });
    }

    // Periodical hardware monitor checks (every 1 second)
    setInterval(() => {
        if (currentInterfaceState === InterviewState.INTERVIEW_ACTIVE) {
            handleDeviceDisconnected();
        }
        // Sync Online/Offline state
        const online = navigator.onLine;
        if (proctorPanelNetwork) {
            proctorPanelNetwork.className = online ? "text-success fw-semibold" : "text-danger fw-semibold";
            proctorPanelNetwork.textContent = online ? "✓ Stable" : "❌ Offline";
        }
    }, 1000);

    // ==========================================================================
    // Fullscreen Handling
    // ==========================================================================

    function checkFullscreen() {
        if (currentInterfaceState !== InterviewState.INTERVIEW_ACTIVE) return;

        const isFullscreen = !!(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement);
        
        if (proctorPanelFullscreen) {
            proctorPanelFullscreen.className = isFullscreen ? "text-success fw-semibold" : "text-danger fw-semibold";
            proctorPanelFullscreen.textContent = isFullscreen ? "✓ Active" : "❌ Exited";
        }

        if (!isFullscreen) {
            pauseInterview();
            fullscreenWarningCount++;
            proctorWarningCount++;
            if (proctorPanelWarnings) {
                proctorPanelWarnings.textContent = proctorWarningCount + " / 3";
            }
            if (fullscreenPauseOverlay) {
                fullscreenPauseOverlay.classList.remove('d-none');
            }
        }
    }

    document.addEventListener('fullscreenchange', checkFullscreen);
    document.addEventListener('webkitfullscreenchange', checkFullscreen);
    document.addEventListener('mozfullscreenchange', checkFullscreen);

    if (fullscreenRestoreBtn) {
        fullscreenRestoreBtn.addEventListener('click', () => {
            document.documentElement.requestFullscreen?.()
                .then(() => {
                    if (fullscreenPauseOverlay) fullscreenPauseOverlay.classList.add('d-none');
                    // Ensure camera/mic are active before resuming
                    if (cameraActive && microphoneActive) {
                        resumeInterview();
                    } else {
                        showProctorPauseOverlay();
                    }
                })
                .catch(err => {
                    alert("Fullscreen access required. Please try again.");
                });
        });
    }

    // ==========================================================================
    // Tab Switch (Visibility) Detection
    // ==========================================================================

    document.addEventListener('visibilitychange', () => {
        if (currentInterfaceState === InterviewState.INTERVIEW_ACTIVE && document.visibilityState === 'hidden') {
            tabSwitchWarningCount++;
            proctorWarningCount++;

            if (proctorPanelWarnings) {
                proctorPanelWarnings.textContent = proctorWarningCount + " / 3";
            }

            alert("Warning: Please return to the interview window. Switch events are recorded.");
        }
    });

    // ==========================================================================
    // Start Interview Action & State Triggers
    // ==========================================================================

    if (instructionsCheckbox) {
        instructionsCheckbox.addEventListener('change', () => {
            startChecksBtn.disabled = !instructionsCheckbox.checked;
        });
    }

    if (startChecksBtn) {
        startChecksBtn.addEventListener('click', () => {
            transitionView(infoView, hardwareView, () => {
                startWebcamStream(false);
            });
        });
    }

    if (hardwareRetryBtn) {
        hardwareRetryBtn.addEventListener('click', () => {
            startWebcamStream(true);
        });
    }

    if (cameraRetryBtn) {
        cameraRetryBtn.addEventListener('click', () => {
            startWebcamStream(true);
        });
    }

    if (micRetryBtn) {
        micRetryBtn.addEventListener('click', () => {
            startWebcamStream(true);
        });
    }

    // Manual camera device selection change listener
    if (cameraSourceSelect) {
        cameraSourceSelect.addEventListener('change', async (e) => {
            const targetDeviceId = e.target.value;
            if (targetDeviceId && targetDeviceId !== currentActiveCameraId) {
                console.log("[Hardware] User manually switched camera:", targetDeviceId);
                await switchCameraDevice(targetDeviceId);
            }
        });
    }

    // Dynamic hardware hotplug detection
    if (navigator.mediaDevices && navigator.mediaDevices.addEventListener) {
        navigator.mediaDevices.addEventListener('devicechange', async () => {
            if (activeMediaStream && currentInterfaceState !== InterviewState.COMPLETED) {
                console.log("[Hardware] Device change detected, updating available cameras...");
                await setupCameraSelection(activeMediaStream);
            console.log("[HardwareMonitor] Hardware devicechange event detected.");
            if (currentInterfaceState === InterviewState.COMPLETED) return;

            if (currentInterfaceState === InterviewState.INTERVIEW_ACTIVE || currentInterfaceState === InterviewState.PAUSED) {
                // DO NOT automatically switch cameras during the interview!
                // Check if currently selected camera was disconnected
                try {
                    const devices = await navigator.mediaDevices.enumerateDevices();
                    const videoDevs = devices.filter(d => d.kind === 'videoinput');
                    const isSelectedStillPresent = selectedCameraDeviceId ? videoDevs.some(d => d.deviceId === selectedCameraDeviceId) : true;
                    if (!isSelectedStillPresent) {
                        console.warn("[HardwareMonitor] Currently selected camera was disconnected from the system!");
                        cameraActive = false;
                        cameraCheckPassed = false;
                        updateProctorPanelStatus();
                        enforceProctoringLock("camera");
                    }
                } catch (e) {
                    console.warn("[HardwareMonitor] Error checking devices on devicechange:", e);
                }
            } else if (hardwareView && !hardwareView.classList.contains('d-none')) {
                if (activeMediaStream) {
                    await setupCameraSelection(activeMediaStream);
                }
            }
        });
    }

    // Auto-invoke getUserMedia hardware check ONLY if hardwareView is already active/visible
    if (hardwareView && !hardwareView.classList.contains('d-none')) {
        console.log("[Hardware] System readiness view active on load - requesting permissions...");
        startWebcamStream(false);
    }

    // Cleanup: Stop all camera and microphone tracks when leaving the page
    window.addEventListener('beforeunload', () => stopWebcamStream());
    window.addEventListener('pagehide', () => stopWebcamStream());

    if (startInterviewBtn) {
        startInterviewBtn.addEventListener('click', async () => {
            // Validate AGAIN on click
            if (!cameraCheckPassed || !microphoneCheckPassed || !networkCheckPassed) {
                alert("Camera, microphone, and network checks must pass before starting the assessment.");
                return;
            }

            // Attempt Fullscreen
            try {
                await document.documentElement.requestFullscreen();
            } catch (e) {
                console.warn("Fullscreen request declined", e);
            }

            document.body.classList.add('interview-focus-mode');
            isInterviewActive = true;
            currentInterfaceState = InterviewState.INTERVIEW_ACTIVE;

            if (!guardHistoryArmed) {
                window.history.pushState({ interviewGuard: true }, '', window.location.href);
                guardHistoryArmed = true;
            }

            runInterviewCountdown(() => {
                transitionView(hardwareView, mcqView, () => {
                    if (!activeMediaStream) {
                        startWebcamStream();
                    }
                    
                    // Unhide floating proctor card and sync stream
                    if (floatingCard) floatingCard.classList.remove('d-none');
                    if (floatingFeed && activeMediaStream) {
                        floatingFeed.srcObject = activeMediaStream;
                        initVideoFrameCallback(floatingFeed);
                        floatingFeed.play().catch(e => console.warn("[HardwareCheck] Floating feed playback error:", e));
                    }
                    setWebcamStatusPill('active', '● Camera Active');

                    // Verify proctor sidebar statuses
                    if (proctorPanelFullscreen) {
                        proctorPanelFullscreen.className = "text-success fw-semibold";
                        proctorPanelFullscreen.textContent = "✓ Active";
                    }

                    startTimer(10 * 60);
                    loadQuestion(0);
                });
            });
        });
    }

    const showExitDialog = () => {
        console.log("[INTERVIEW] Exit button clicked -> Opening exit dialog");
        const modal = document.getElementById('exit-dialog') || document.getElementById('interviewExitDialog') || exitDialog;
        if (!modal) {
            console.error("[INTERVIEW] Exit dialog modal not found in DOM!");
            return;
        }
        modal.classList.remove('d-none');
        modal.hidden = false;
        confirmInterviewExit?.focus();
    };

    const closeExitDialog = () => {
        console.log("[INTERVIEW] Continue interview clicked -> Closing exit dialog");
        const modal = document.getElementById('exit-dialog') || document.getElementById('interviewExitDialog') || exitDialog;
        if (modal) {
            modal.classList.add('d-none');
            modal.hidden = true;
        }
        nextBtn?.focus();
    };

    const exitActiveInterview = () => {
        console.log("[Exit] User confirmed exit interview. Performing full media cleanup & redirection...");
        allowInterviewExit = true;
        isInterviewActive = false;
        currentInterfaceState = InterviewState.COMPLETED;

        // 1. Stop timers
        clearInterval(timerInterval);

        // 2. Stop camera & mic MediaStreams and remove/cleanup all tracks
        stopWebcamStream();

        // 3. Reset UI focus state & exit fullscreen
        document.body.classList.remove('interview-focus-mode');
        if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});

        // 4. Navigate to assessment dashboard/history page
        window.location.href = '/interview-assessment';
    };

    const bindExitButtonEvents = () => {
        const exitBtns = [
            document.getElementById('exitInterviewButton'),
            document.getElementById('exit-interview-btn'),
            ...Array.from(document.querySelectorAll('.exit-interview'))
        ].filter(Boolean);

        console.log(`[INTERVIEW] Binding exit dialog triggers to ${exitBtns.length} button(s)`);
        exitBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                showExitDialog();
            });
        });
    };
    bindExitButtonEvents();

    const continueBtn = document.getElementById('continueInterviewButton');
    if (continueBtn) {
        continueBtn.addEventListener('click', closeExitDialog);
    }
    continueInterviewButtons.forEach(button => button.addEventListener('click', closeExitDialog));
    confirmInterviewExit?.addEventListener('click', exitActiveInterview);
    window.addEventListener('popstate', () => {
        if (!isInterviewActive || allowInterviewExit || isInterviewSubmitted) return;
        window.history.pushState({ interviewGuard: true }, '', window.location.href);
        showExitDialog();
    });

    // Prevent accidental page reloads
    window.addEventListener('beforeunload', event => {
        if (!isInterviewActive || allowInterviewExit || isInterviewSubmitted) return;
        event.preventDefault();
        event.returnValue = '';
    });
    window.addEventListener('pagehide', stopWebcamStream);

    // ==========================================================================
    // Question & Answer Submission
    // ==========================================================================

    if (nextBtn) {
        nextBtn.addEventListener('click', async () => {
            if (!isProctoringHealthy()) {
                pauseInterview();
                showProctorPauseOverlay();
                return;
            }
            await saveCurrentAnswer();
            if (currentQuestionIndex < totalQuestions - 1) {
                currentQuestionIndex++;
                loadQuestion(currentQuestionIndex);
            }
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', async () => {
            if (!isProctoringHealthy()) {
                pauseInterview();
                showProctorPauseOverlay();
                return;
            }
            await saveCurrentAnswer();
            if (currentQuestionIndex > 0) {
                currentQuestionIndex--;
                loadQuestion(currentQuestionIndex);
            }
        });
    }
    
    if (submitBtn) {
        submitBtn.addEventListener('click', async () => {
            if (!isProctoringHealthy()) {
                pauseInterview();
                showProctorPauseOverlay();
                return;
            }
            if (confirm('Are you sure you want to submit the interview?')) {
                await saveCurrentAnswer();
                submitInterview();
            }
        });
    }

    if (navigatorButtons) {
        navigatorButtons.forEach(btn => {
            btn.addEventListener('click', async () => {
                if (!isProctoringHealthy()) {
                    pauseInterview();
                    showProctorPauseOverlay();
                    return;
                }
                const targetIndex = parseInt(btn.textContent) - 1;
                if (targetIndex !== currentQuestionIndex) {
                    await saveCurrentAnswer();
                    currentQuestionIndex = targetIndex;
                    loadQuestion(currentQuestionIndex);
                }
            });
        });
    }

    optionInputs.forEach((input) => {
        input.addEventListener('change', () => {
            if (!isProctoringHealthy()) {
                input.checked = false;
                pauseInterview();
                showProctorPauseOverlay();
                return;
            }
            if (input.checked) answeredQuestionIndexes.add(currentQuestionIndex);
            if (input.checked && navigatorButtons[currentQuestionIndex]) {
                navigatorButtons[currentQuestionIndex].classList.add('answered');
            }
            updateLiveSignals();
        });
    });

    document.addEventListener('keydown', (event) => {
        if (!mcqView || mcqView.classList.contains('d-none') || mcqView.style.display === 'none') return;
        if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;

        if (!isProctoringHealthy()) {
            if (['1', '2', '3', '4', 'Enter', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
                event.preventDefault();
                event.stopPropagation();
                pauseInterview();
                showProctorPauseOverlay();
                return;
            }
        }

        if (['1', '2', '3', '4'].includes(event.key)) {
            const input = optionInputs[Number(event.key) - 1];
            if (input && !input.disabled) {
                event.preventDefault();
                input.checked = true;
                input.dispatchEvent(new Event('change', { bubbles: true }));
            }
        } else if (event.key === 'Enter') {
            event.preventDefault();
            if (currentQuestionIndex === totalQuestions - 1) submitBtn?.click();
            else nextBtn?.click();
        } else if (event.key === 'ArrowLeft') {
            event.preventDefault();
            prevBtn?.click();
        } else if (event.key === 'ArrowRight') {
            event.preventDefault();
            nextBtn?.click();
        }
    });

    if (interviewThemeToggle) {
        const syncInterviewThemeIcon = () => {
            const dark = document.documentElement.dataset.theme === 'dark';
            interviewThemeToggle.innerHTML = `<i class="bi bi-${dark ? 'sun' : 'moon-stars'}"></i>`;
            interviewThemeToggle.setAttribute('aria-label', dark ? 'Use light theme' : 'Use dark theme');
        };
        interviewThemeToggle.addEventListener('click', () => {
            const nextTheme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
            document.documentElement.dataset.theme = nextTheme;
            localStorage.setItem('interviewai-theme', nextTheme);
            window.dispatchEvent(new CustomEvent('interviewai:themechange', { detail: { theme: nextTheme } }));
            syncInterviewThemeIcon();
        });
        syncInterviewThemeIcon();
    }

    // ==========================================================================
    // View Transitions & Helper Functions
    // ==========================================================================

    function transitionView(fromView, toView, onComplete) {
        if (!fromView || !toView) return;
        fromView.classList.add('fade-out');
        setTimeout(() => {
            fromView.style.display = 'none';
            toView.classList.remove('d-none');
            toView.classList.add('fade-in');
            if (onComplete) onComplete();
        }, 300);
    }

    function runInterviewCountdown(onComplete) {
        if (!countdownOverlay || !countdownValue) {
            onComplete();
            return;
        }

        const steps = ['3', '2', '1', 'Start'];
        let step = 0;
        countdownOverlay.hidden = false;

        const advance = () => {
            countdownValue.textContent = steps[step];
            countdownValue.style.animation = 'none';
            void countdownValue.offsetWidth;
            countdownValue.style.animation = '';
            step += 1;

            if (step < steps.length) {
                window.setTimeout(advance, 760);
            } else {
                window.setTimeout(() => {
                    countdownOverlay.hidden = true;
                    onComplete();
                }, 620);
            }
        };

        advance();
    }

    function startTimer(duration) {
        remainingTimerSeconds = duration;
        timerInterval = setInterval(() => {
            let minutes = String(parseInt(remainingTimerSeconds / 60, 10)).padStart(2, '0');
            let seconds = String(parseInt(remainingTimerSeconds % 60, 10)).padStart(2, '0');
            if (timerEl) timerEl.textContent = `${minutes}:${seconds}`;
            if (--remainingTimerSeconds < 0) {
                clearInterval(timerInterval);
                submitInterview();
            }
        }, 1000);
    }

    async function loadQuestion(index) {
        liveQuestionCard?.classList.add('is-switching');
        try {
            const response = await fetch(`/api/mcq/question/${index}`);
            if (!response.ok) throw new Error('Failed to load question.');
            const data = await response.json();

            questionTextEl.textContent = data.question_text;
            totalQuestions = data.total_questions;

            // Populate options
            for (const [key, label] of Object.entries(optionLabels)) {
                if (data.options[key]) {
                    const optionCopy = label.querySelector('span');
                    if (optionCopy) optionCopy.textContent = data.options[key];
                    else label.textContent = data.options[key];
                    label.parentElement.style.display = 'block';
                } else {
                    label.parentElement.style.display = 'none';
                }
            }

            // Clear previous selection
            optionInputs.forEach(input => input.checked = false);

            // Restore saved answer
            if (data.saved_answer) {
                const savedInput = document.querySelector(`input[name="answer"][value="${data.saved_answer}"]`);
                if (savedInput) savedInput.checked = true;
                answeredQuestionIndexes.add(index);
            }

            updateUI(index, totalQuestions);

        } catch (error) {
            console.error('Error loading question:', error);
            questionTextEl.textContent = 'Error loading question. Please try refreshing the page.';
        } finally {
            window.setTimeout(() => liveQuestionCard?.classList.remove('is-switching'), 90);
        }
    }

    async function saveCurrentAnswer() {
        if (!isProctoringHealthy()) {
            console.warn("[Security] saveCurrentAnswer blocked — camera or microphone inactive.");
            return;
        }
        const selectedOption = document.querySelector('input[name="answer"]:checked');
        const answer = selectedOption ? selectedOption.value : null;

        if (answer && navigatorButtons[currentQuestionIndex]) {
            navigatorButtons[currentQuestionIndex].classList.add('answered');
        }
        if (answer) answeredQuestionIndexes.add(currentQuestionIndex);

        try {
            await fetch('/api/mcq/answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: currentQuestionIndex, answer: answer }),
            });
        } catch (error) {
            console.error('Failed to save answer:', error);
        }
    }

    async function submitInterview() {
        isInterviewSubmitted = true;
        isInterviewActive = false;
        allowInterviewExit = true;
        currentInterfaceState = InterviewState.COMPLETED;

        // Immediately stop media stream when interview finishes
        stopWebcamStream();

        if (nextBtn) nextBtn.disabled = true;
        if (prevBtn) prevBtn.disabled = true;
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Submitting...';
        }
        clearInterval(timerInterval);

        // Prep proctor statistics payload
        const proctorStats = {
            camera_verified: cameraActive,
            microphone_verified: microphoneActive,
            fullscreen_warnings: fullscreenWarningCount,
            tab_switch_warnings: tabSwitchWarningCount,
            proctoring_warnings: proctorWarningCount,
            interview_status: 'completed'
        };

        try {
            const response = await fetch('/api/mcq/submit', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(proctorStats)
            });
            const data = await response.json();
            if (data.status === 'success' && data.report_url) {
                if (celebrationOverlay) celebrationOverlay.hidden = false;
                window.setTimeout(() => {
                    window.location.href = data.report_url;
                }, celebrationOverlay ? 1800 : 0);
            } else {
                throw new Error(data.error || 'Failed to submit.');
            }
        } catch (error) {
            console.error('Submission failed:', error);
            isInterviewSubmitted = false;
            isInterviewActive = true;
            allowInterviewExit = false;
            currentInterfaceState = InterviewState.INTERVIEW_ACTIVE;
            alert('There was an error submitting your interview. Please contact support.');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Complete interview <i class="bi bi-stars"></i>';
            }
        }
    }
    
    function updateUI(index, total) {
        const progress = ((index + 1) / total) * 100;
        if (progressBarEl) progressBarEl.style.width = `${progress}%`;
        if (progressRingEl) progressRingEl.style.setProperty('--progress', progress);
        if (currentQuestionEl) currentQuestionEl.textContent = index + 1;
        if (compactCurrentQuestionEl) compactCurrentQuestionEl.textContent = index + 1;
        if (progressPercentEl) progressPercentEl.textContent = `${Math.round(progress)}%`;

        if (navigatorButtons) {
            navigatorButtons.forEach((btn, i) => {
                btn.classList.remove('current');
                if (i === index) {
                    btn.classList.add('current');
                }
            });
        }

        if (prevBtn) prevBtn.style.visibility = index === 0 ? 'hidden' : 'visible';
        if (nextBtn) nextBtn.style.display = index === total - 1 ? 'none' : 'block';
        if (submitBtn) submitBtn.style.display = index === total - 1 ? 'block' : 'none';
        updateLiveSignals();
    }

    function updateLiveSignals() {
        const answered = answeredQuestionIndexes.size;
        const remaining = Math.max(0, totalQuestions - answered);
        const completion = totalQuestions ? answered / totalQuestions : 0;
        const confidence = Math.round(18 + completion * 72);

        if (answeredQuestionsEl) answeredQuestionsEl.textContent = answered;
        if (remainingQuestionsEl) remainingQuestionsEl.textContent = remaining;
        if (confidenceValueEl) confidenceValueEl.textContent = answered < 3 ? 'Building' : confidence >= 70 ? 'Strong' : 'Growing';
        if (confidenceBarEl) confidenceBarEl.style.width = `${confidence}%`;
        if (technicalScoreEl) technicalScoreEl.textContent = `${confidence}%`;
        if (technicalBarEl) technicalBarEl.style.width = `${confidence}%`;
        if (predictionLabelEl) predictionLabelEl.textContent = answered < 5 ? 'Building your signal' : confidence >= 70 ? 'Strong trajectory' : 'Positive momentum';
        if (liveHintEl) liveHintEl.textContent = liveHints[currentQuestionIndex % liveHints.length];
        if (motivationMessageEl) {
            const message = motivationMessageEl.querySelector('p');
            if (message) message.textContent = motivationMessages[Math.floor(currentQuestionIndex / 5) % motivationMessages.length];
        }
    }

    function updateStatus(element, state, message) {
        if (!element) return;
        const icon = element.querySelector('i');
        const msg = element.querySelector('.badge') || element.querySelector('.status-message');
        const isSuccess = state === 'active';
        const isPending = state === 'checking' || state === 'initializing';
        
        if (icon) {
            if (isPending) icon.className = 'bi bi-hourglass-split text-warning me-2';
            else if (isSuccess) icon.className = 'bi bi-check-circle-fill text-success me-2';
            else icon.className = 'bi bi-x-circle-fill text-danger me-2';
        }
        
        if (msg) {
            msg.textContent = message;
            if (isPending) {
                msg.className = 'badge bg-warning text-dark';
            } else if (isSuccess) {
                msg.className = 'badge bg-success';
            } else {
                msg.className = 'badge bg-danger';
            }
        }
    }
});
