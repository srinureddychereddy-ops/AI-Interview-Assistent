document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("resumeAnalyzerFormV2") || document.getElementById("resumeAnalyzerForm");
  if (!form) return;

  const dropzone = document.getElementById("resumeDropzoneV2") || document.getElementById("resumeDropzone");
  const fileInput = document.getElementById("resumeFileV2") || document.getElementById("resumeFile");
  const browseButton = document.getElementById("browseResumeV2") || document.getElementById("browseResume");
  const emptyState = document.getElementById("dropzoneEmptyV2") || document.getElementById("dropzoneEmpty");
  const selectedState = document.getElementById("selectedFileV2") || document.getElementById("selectedFile");
  const selectedName = document.getElementById("selectedFileNameV2") || document.getElementById("selectedFileName");
  const selectedMeta = document.getElementById("selectedFileMetaV2") || document.getElementById("selectedFileMeta");
  const removeButton = document.getElementById("removeResumeV2") || document.getElementById("removeResume");
  const resumeError = document.getElementById("resumeErrorV2") || document.getElementById("resumeError");
  const job = document.getElementById("jobDescriptionV2") || document.getElementById("jobDescription");
  const jobCount = document.getElementById("jobCharacterCountV2") || document.getElementById("jobCharacterCount");
  const jobError = document.getElementById("jobErrorV2") || document.getElementById("jobError");
  const interviewInput = document.getElementById("interviewTypeV2") || document.getElementById("interviewType");
  const submitButton = document.getElementById("generateInterviewV2") || document.getElementById("generateInterview");
  const spinner = document.getElementById("generateSpinnerV2") || document.getElementById("generateSpinner");
  const requestError = document.getElementById("resumeRequestError");

  const liveLoading = document.getElementById("resumeLiveLoading");
  const loadingProgress = document.getElementById("resumeLoadingProgress");
  const loadingTitle = document.getElementById("resumeLoadingTitle");
  const loadingSteps = document.querySelectorAll(".resume-loading-step");
  const dashboard = document.getElementById("resumeAnalysisDashboard");

  let isAnalyzing = false;
  let animationTimer = null;

  const validPdf = file => file && (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) && file.size <= 5 * 1024 * 1024;
  
  const showFile = file => {
    const valid = validPdf(file);
    if (resumeError) resumeError.classList.toggle("d-none", valid);
    if (!valid) { fileInput.value = ""; return false; }
    const sizeMb = (file.size / 1048576).toFixed(2);
    if (selectedName) selectedName.textContent = file.name;
    if (selectedMeta) selectedMeta.textContent = `${sizeMb} MB · PDF · Ready to analyze`;
    if (emptyState) emptyState.classList.add("d-none");
    if (selectedState) selectedState.classList.remove("d-none");
    return true;
  };

  if (browseButton) browseButton.addEventListener("click", event => { event.stopPropagation(); fileInput.click(); });
  if (dropzone) {
    dropzone.addEventListener("click", event => { if (!event.target.closest("button")) fileInput.click(); });
    dropzone.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); fileInput.click(); } });
    ["dragenter", "dragover"].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.add("dragging"); }));
    ["dragleave", "drop"].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.remove("dragging"); }));
    dropzone.addEventListener("drop", event => {
      const file = event.dataTransfer.files[0];
      if (showFile(file)) { const transfer = new DataTransfer(); transfer.items.add(file); fileInput.files = transfer.files; }
    });
  }

  if (fileInput) fileInput.addEventListener("change", () => fileInput.files[0] && showFile(fileInput.files[0]));
  if (removeButton) {
    removeButton.addEventListener("click", event => {
      event.stopPropagation();
      fileInput.value = "";
      if (selectedState) selectedState.classList.add("d-none");
      if (emptyState) emptyState.classList.remove("d-none");
      if (resumeError) resumeError.classList.add("d-none");
    });
  }

  const updateCount = () => {
    if (jobCount && job) jobCount.textContent = job.value.length.toLocaleString();
    if (jobError && job) jobError.classList.toggle("d-none", Boolean(job.value.trim()));
  };
  if (job) job.addEventListener("input", updateCount);

  document.querySelectorAll(".resume-type-card").forEach(card => card.addEventListener("click", () => {
    document.querySelectorAll(".resume-type-card").forEach(item => { item.classList.remove("active"); item.setAttribute("aria-pressed", "false"); });
    card.classList.add("active");
    card.setAttribute("aria-pressed", "true");
    const val = card.dataset.interviewTypeV2 || card.dataset.interviewType;
    if (interviewInput && val) interviewInput.value = val;
  }));

  const pipelineBanner = document.getElementById("resumePipelineStatusBanner");
  const pipelineTitle = document.getElementById("pipelineStatusTitle");
  const pipelineSubtitle = document.getElementById("pipelineStatusSubtitle");
  const pipelineBadge = document.getElementById("pipelineStatusBadge");
  const pipelineSpinner = document.getElementById("pipelineSpinner");
  const stageTimeline = document.getElementById("resumeStageTimeline");

  const STAGES = [
    { id: 1, label: "Resume uploaded" },
    { id: 2, label: "Resume content extracted" },
    { id: 3, label: "Matching against job description" },
    { id: 4, label: "Calculating ATS insights" },
    { id: 5, label: "Preparing recommendations" }
  ];

  const updateStageTimeline = (currentStageNum, stageName) => {
    if (!stageTimeline) return;
    stageTimeline.innerHTML = STAGES.map(stage => {
      if (stage.id < currentStageNum) {
        return `<span class="stage-chip completed"><i class="bi bi-check-circle-fill text-success"></i> ${stage.label}</span>`;
      } else if (stage.id === currentStageNum) {
        return `<span class="stage-chip active"><span class="spinner-border spinner-border-sm me-1" style="width: 11px; height: 11px;"></span> ${stage.label}</span>`;
      } else {
        return `<span class="stage-chip"><i class="bi bi-circle text-muted"></i> ${stage.label}</span>`;
      }
    }).join("");

    if (pipelineTitle) {
      if (currentStageNum >= 5) {
        pipelineTitle.textContent = "Finalizing recommendations & insights...";
      } else if (currentStageNum === 4) {
        pipelineTitle.textContent = "Running published ATS workflow...";
      } else if (currentStageNum === 3) {
        pipelineTitle.textContent = "Evaluating match against job requirements...";
      } else {
        pipelineTitle.textContent = "Processing resume data...";
      }
    }
  };

  // Render skeleton loaders inside the actual result cards
  const renderSkeletonDashboard = () => {
    if (pipelineBanner) {
      pipelineBanner.classList.remove("d-none");
      if (pipelineBadge) {
        pipelineBadge.textContent = "In Progress";
        pipelineBadge.className = "badge bg-primary-subtle text-primary rounded-pill font-monospace px-3 py-1.5";
      }
      if (pipelineSpinner) pipelineSpinner.classList.remove("d-none");
    }
    updateStageTimeline(1, "Resume uploaded");

    // ATS ring skeleton
    const atsRing = document.getElementById("atsScoreRing");
    if (atsRing) {
      atsRing.style.background = "#e2e8f0";
      atsRing.innerHTML = `<div class="skeleton-circle skeleton-shimmer"></div>`;
    }
    const scoreVal = document.getElementById("atsScoreValue");
    if (scoreVal) scoreVal.textContent = "...";
    const scoreLabel = document.getElementById("atsScoreLabel");
    if (scoreLabel) scoreLabel.innerHTML = `<span class="skeleton-line skeleton-shimmer w-50 mb-2"></span>`;
    const scoreExp = document.getElementById("atsScoreExplanation");
    if (scoreExp) scoreExp.innerHTML = `<span class="skeleton-line skeleton-shimmer w-75"></span>`;

    // Job match skeleton
    const jobMatchVal = document.getElementById("jobMatchValue");
    if (jobMatchVal) jobMatchVal.innerHTML = `<span class="skeleton-line skeleton-shimmer w-25 mb-1" style="height: 32px;"></span>`;
    const jobMatchExp = document.getElementById("jobMatchExplanation");
    if (jobMatchExp) jobMatchExp.innerHTML = `<span class="skeleton-line skeleton-shimmer w-75"></span>`;

    // Summary skeleton
    const summaryText = document.getElementById("resumeSummaryText");
    if (summaryText) {
      summaryText.innerHTML = `
        <span class="skeleton-line skeleton-shimmer w-100 mb-2"></span>
        <span class="skeleton-line skeleton-shimmer w-85 mb-2"></span>
        <span class="skeleton-line skeleton-shimmer w-60"></span>
      `;
    }

    // Strengths skeleton
    const strongList = document.getElementById("strongPointsList");
    if (strongList) {
      strongList.innerHTML = `
        <div class="d-flex flex-column gap-2.5">
          <div class="p-3 rounded-3 skeleton-box skeleton-shimmer"><span class="skeleton-line skeleton-shimmer w-85"></span></div>
          <div class="p-3 rounded-3 skeleton-box skeleton-shimmer"><span class="skeleton-line skeleton-shimmer w-70"></span></div>
          <div class="p-3 rounded-3 skeleton-box skeleton-shimmer"><span class="skeleton-line skeleton-shimmer w-80"></span></div>
        </div>
      `;
    }

    // Improvement areas skeleton
    const improveList = document.getElementById("improvementAreasList");
    if (improveList) {
      improveList.innerHTML = `
        <div class="d-flex flex-column gap-2.5">
          <div class="p-3 rounded-3 skeleton-box skeleton-shimmer"><span class="skeleton-line skeleton-shimmer w-80"></span></div>
          <div class="p-3 rounded-3 skeleton-box skeleton-shimmer"><span class="skeleton-line skeleton-shimmer w-65"></span></div>
        </div>
      `;
    }

    // Missing skills skeleton
    const missingSkillsCloud = document.getElementById("missingSkillsList");
    if (missingSkillsCloud) {
      missingSkillsCloud.innerHTML = `
        <div class="d-flex flex-wrap gap-2">
          <span class="skeleton-pill skeleton-shimmer"></span>
          <span class="skeleton-pill skeleton-shimmer"></span>
          <span class="skeleton-pill skeleton-shimmer"></span>
          <span class="skeleton-pill skeleton-shimmer"></span>
        </div>
      `;
    }

    // Recommendations skeleton
    const tipsList = document.getElementById("atsTipsList");
    if (tipsList) {
      tipsList.innerHTML = `
        <div class="d-flex flex-column gap-2.5">
          <div class="p-3 rounded-3 skeleton-box skeleton-shimmer"><span class="skeleton-line skeleton-shimmer w-90"></span></div>
          <div class="p-3 rounded-3 skeleton-box skeleton-shimmer"><span class="skeleton-line skeleton-shimmer w-75"></span></div>
        </div>
      `;
    }

    // Category scores skeleton
    const categoryGrid = document.getElementById("categoryScoresList");
    if (categoryGrid) {
      categoryGrid.innerHTML = `
        <div class="d-flex flex-column gap-3">
          <div class="p-2 skeleton-box skeleton-shimmer" style="height: 28px;"></div>
          <div class="p-2 skeleton-box skeleton-shimmer" style="height: 28px;"></div>
          <div class="p-2 skeleton-box skeleton-shimmer" style="height: 28px;"></div>
          <div class="p-2 skeleton-box skeleton-shimmer" style="height: 28px;"></div>
        </div>
      `;
    }

    // Actions block skeleton
    const nextStepsBlock = document.querySelector(".resume-dashboard-actions");
    if (nextStepsBlock) {
      nextStepsBlock.innerHTML = `
        <div class="w-100 p-4 rounded-4 skeleton-box skeleton-shimmer">
          <span class="skeleton-line skeleton-shimmer w-40 mb-2"></span>
          <span class="skeleton-line skeleton-shimmer w-70"></span>
        </div>
      `;
    }

    if (dashboard) {
      dashboard.classList.remove("d-none");
      dashboard.scrollIntoView({ behavior: "smooth" });
    }
  };

  // Score counter animation
  const animateScoreCounter = (targetVal) => {
    const scoreValEl = document.getElementById("atsScoreValue") || document.getElementById("atsScoreVal");
    const targetScore = Math.max(0, Math.min(100, Math.round(targetVal || 0)));

    let current = 0;
    const duration = 1000;
    const startTime = performance.now();

    const tick = (now) => {
      const elapsed = now - startTime;
      const progress = Math.min(1, elapsed / duration);
      const ease = 1 - Math.pow(1 - progress, 3);
      current = Math.round(targetScore * ease);
      if (scoreValEl) scoreValEl.textContent = `${current}%`;
      if (progress < 1) {
        requestAnimationFrame(tick);
      }
    };
    requestAnimationFrame(tick);
  };

  // Render normalized analysis dashboard with real data
  const renderDashboard = (data) => {
    const analysis = data.analysis || {};
    const recordId = data.record_id;
    const atsScore = analysis.ats_score !== null && analysis.ats_score !== undefined ? analysis.ats_score : 0;
    const isEligible = atsScore >= 80;

    // Status banner updates to finished
    if (pipelineBanner) {
      if (pipelineTitle) pipelineTitle.textContent = "Analysis complete";
      if (pipelineSubtitle) pipelineSubtitle.textContent = "Verified real results from AI workflow.";
      if (pipelineBadge) {
        pipelineBadge.textContent = "Completed";
        pipelineBadge.className = "badge bg-success-subtle text-success rounded-pill font-monospace px-3 py-1.5";
      }
      if (pipelineSpinner) pipelineSpinner.classList.add("d-none");
    }
    if (stageTimeline) {
      stageTimeline.innerHTML = STAGES.map(stage => (
        `<span class="stage-chip completed"><i class="bi bi-check-circle-fill text-success"></i> ${stage.label}</span>`
      )).join("");
    }

    const matchTier = analysis.match_level || (atsScore >= 90 ? "Excellent Match" : atsScore >= 80 ? "Strong Match" : atsScore >= 60 ? "Good Match" : atsScore >= 40 ? "Moderate Match" : "Low Match");
    const scoreColor = atsScore >= 80 ? "#10b981" : atsScore >= 60 ? "#3b82f6" : atsScore >= 40 ? "#f59e0b" : "#ef4444";

    // Section 1: ATS Score Ring & Label
    const scoreLabel = document.getElementById("atsScoreLabel");
    const scoreExp = document.getElementById("atsScoreExplanation");
    const atsRing = document.getElementById("atsScoreRing");

    if (atsRing) {
      atsRing.innerHTML = `
        <div id="atsRingCenter">
          <strong id="atsScoreValue">${Math.round(atsScore)}%</strong>
          <small>ATS SCORE</small>
        </div>
      `;
      atsRing.style.background = `conic-gradient(${scoreColor} ${atsScore}%, rgba(226,232,240,0.4) 0)`;
    }
    if (scoreLabel) scoreLabel.textContent = matchTier;
    if (scoreExp) scoreExp.textContent = `Your resume matches ${Math.round(atsScore)}% of key requirements for ${analysis.job_role || 'the target role'}.`;

    // Section 2: Job Match
    const jobMatchValEl = document.getElementById("jobMatchValue");
    const jobMatchExpEl = document.getElementById("jobMatchExplanation");
    const jobMatch = analysis.job_match !== undefined && analysis.job_match !== null ? analysis.job_match : atsScore;
    if (jobMatchValEl) jobMatchValEl.textContent = `${Math.round(jobMatch)}%`;
    if (jobMatchExpEl) {
      jobMatchExpEl.textContent = `Overall requirement match against target job description (${Math.round(atsScore)}% ATS score).`;
    }

    // Section 3: Summary
    const summaryText = document.getElementById("resumeSummaryText");
    if (summaryText) summaryText.textContent = analysis.summary || "Summary unavailable from the analysis workflow.";

    // Section 4: Strengths
    const strongList = document.getElementById("strongPointsList");
    if (strongList) {
      const list = analysis.strengths || [];
      if (list.length > 0) {
        strongList.innerHTML = list.map(s => `
          <div class="insight-card-item mb-2 p-2.5 rounded-3 border d-flex align-items-start gap-2.5" style="background: rgba(16, 185, 129, 0.04); border-color: rgba(16, 185, 129, 0.15) !important;">
            <i class="bi bi-check2-circle text-success fs-5 flex-shrink-0 mt-0.5"></i>
            <span class="text-main small">${s}</span>
          </div>
        `).join('');
      } else {
        strongList.innerHTML = '<p class="text-muted small py-2">No strengths identified by workflow.</p>';
      }
    }

    // Section 5: Areas to Improve
    const improveList = document.getElementById("improvementAreasList");
    if (improveList) {
      const list = (analysis.responsibility_gaps && analysis.responsibility_gaps.length > 0)
        ? analysis.responsibility_gaps
        : (analysis.missing_requirements || []);
      if (list.length > 0) {
        improveList.innerHTML = list.map(w => `
          <div class="insight-card-item mb-2 p-2.5 rounded-3 border d-flex align-items-start gap-2.5" style="background: rgba(245, 158, 11, 0.04); border-color: rgba(245, 158, 11, 0.15) !important;">
            <i class="bi bi-exclamation-triangle text-warning fs-5 flex-shrink-0 mt-0.5"></i>
            <span class="text-main small">${w}</span>
          </div>
        `).join('');
      } else {
        improveList.innerHTML = '<p class="text-muted small py-2">No areas to improve identified by workflow.</p>';
      }
    }

    // Section 6: Missing Skills
    const missingSkillsCloud = document.getElementById("missingSkillsList");
    if (missingSkillsCloud) {
      const skills = (analysis.missing_requirements && analysis.missing_requirements.length > 0)
        ? analysis.missing_requirements
        : (analysis.keyword_opportunities || []);
      if (skills.length > 0) {
        missingSkillsCloud.innerHTML = skills.map(k => `
          <span class="missing-skill-pill me-1 mb-1"><i class="bi bi-tag-fill me-1"></i>${k}</span>
        `).join('');
      } else {
        missingSkillsCloud.innerHTML = '<span class="text-muted small">No major missing skills identified.</span>';
      }
    }

    // Section 7: Recommendations
    const tipsList = document.getElementById("atsTipsList");
    if (tipsList) {
      const recs = analysis.resume_improvements || [];
      if (recs.length > 0) {
        tipsList.innerHTML = recs.map((t, idx) => `
          <div class="optimization-item mb-2 p-2.5 rounded-3 border d-flex align-items-start gap-2" style="background: rgba(99, 102, 241, 0.04); border-color: rgba(99, 102, 241, 0.15) !important;">
            <strong class="text-primary font-monospace flex-shrink-0">0${idx + 1}</strong>
            <span class="text-main small">${t}</span>
          </div>
        `).join('');
      } else if (analysis.final_recommendation) {
        tipsList.innerHTML = `
          <div class="optimization-item p-2.5 rounded-3 border" style="background: rgba(99, 102, 241, 0.04); border-color: rgba(99, 102, 241, 0.15) !important;">
            <span class="text-main small">${analysis.final_recommendation}</span>
          </div>
        `;
      } else {
        tipsList.innerHTML = '<p class="text-muted small py-2">No recommendations provided by workflow.</p>';
      }
    }

    // Section 8: Category Scores
    const categoryGrid = document.getElementById("categoryScoresList");
    if (categoryGrid) {
      let breakdownItems = [];
      if (analysis.score_breakdown && typeof analysis.score_breakdown === 'object' && Object.keys(analysis.score_breakdown).length > 0) {
        breakdownItems = Object.entries(analysis.score_breakdown).map(([k, v]) => {
          const label = k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          return [label, v];
        });
      }

      if (breakdownItems.length > 0) {
        categoryGrid.innerHTML = breakdownItems.map(([name, score]) => {
          const valNum = (score !== null && score !== undefined && !isNaN(Number(score))) ? Math.round(Number(score)) : null;
          const valTxt = valNum !== null ? `${valNum}%` : 'Not evaluated';
          const barWidth = valNum !== null ? Math.max(0, Math.min(100, valNum)) : 0;
          const color = barWidth >= 80 ? '#10b981' : barWidth >= 60 ? '#3b82f6' : barWidth >= 40 ? '#f59e0b' : '#ef4444';
          return `
            <div class="resume-category-item mb-2.5">
              <div class="d-flex justify-content-between small mb-1">
                <span class="text-main fw-semibold">${name}</span>
                <span class="text-main fw-bold font-monospace">${valTxt}</span>
              </div>
              <div class="resume-category-track" style="height: 6px; border-radius: 6px; background: rgba(0,0,0,0.06);">
                <div class="resume-category-fill" style="width: ${barWidth}%; background: ${color}; height: 100%; border-radius: 6px;"></div>
              </div>
            </div>
          `;
        }).join('');
      } else {
        categoryGrid.innerHTML = '<p class="text-muted small py-3 text-center">Category breakdown not provided by workflow.</p>';
      }
    }

    // Section 9: Aptitude Eligibility CTA Gate
    const nextStepsBlock = document.querySelector(".resume-dashboard-actions");
    if (nextStepsBlock) {
      nextStepsBlock.innerHTML = `
        <div class="w-100 p-4 rounded-4 mb-3 ${isEligible ? 'bg-success-subtle border border-success' : 'bg-warning-subtle border border-warning'}">
          <div class="d-flex flex-column flex-md-row align-items-md-center justify-content-between gap-3">
            <div>
              <span class="badge ${isEligible ? 'bg-success' : 'bg-warning text-dark'} rounded-pill mb-2 font-monospace">
                ${isEligible ? '✓ Aptitude Unlocked' : '🔒 Aptitude Locked'}
              </span>
              <h4 class="h5 fw-bold mb-1">${isEligible ? "You're eligible for the Aptitude Round!" : "Improve your resume before continuing"}</h4>
              <p class="text-muted small mb-0">${isEligible ? 'Your ATS score meets the 80% threshold required to start the Aptitude Assessment.' : 'An ATS score of at least 80% is required to unlock the Aptitude Round. Update your resume and re-analyze.'}</p>
            </div>
            <div>
              ${isEligible ? `
                <a href="/aptitude" class="btn btn-success btn-lg rounded-pill px-4 fw-bold shadow-sm d-inline-flex align-items-center gap-2">
                  <span>Start Aptitude Round</span> <i class="bi bi-arrow-right"></i>
                </a>
              ` : `
                <button type="button" class="btn btn-warning btn-lg rounded-pill px-4 fw-bold shadow-sm d-inline-flex align-items-center gap-2" id="retryImproveBtn">
                  <i class="bi bi-arrow-repeat"></i> <span>Improve Resume</span>
                </button>
              `}
            </div>
          </div>
        </div>
        <div class="d-flex flex-wrap gap-2 align-items-center">
          ${recordId ? `
            <a href="/resume-analysis/${recordId}" class="btn btn-outline-primary rounded-pill px-3.5 py-2 font-monospace small d-inline-flex align-items-center gap-1.5 shadow-xs">
              <i class="bi bi-file-earmark-check"></i> View Saved ATS Analysis Record
            </a>
          ` : ''}
          <button type="button" class="resume-action-secondary" id="analyzeAnotherResume"><i class="bi bi-arrow-repeat"></i> Analyze Another Resume</button>
        </div>
      `;
      document.getElementById("retryImproveBtn")?.addEventListener("click", resetAnalyzerUI);
      document.getElementById("analyzeAnotherResume")?.addEventListener("click", resetAnalyzerUI);
    }

    if (dashboard) {
      dashboard.classList.remove("d-none");
    }

    animateScoreCounter(atsScore);
  };

  // Reset Analyzer for new upload
  const resetAnalyzerUI = () => {
    if (dashboard) dashboard.classList.add("d-none");
    if (pipelineBanner) pipelineBanner.classList.add("d-none");
    if (form) form.classList.remove("d-none");
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.classList.remove("disabled");
      if (spinner) spinner.classList.add("d-none");
    }
    // Clear file selection & input states
    if (fileInput) fileInput.value = "";
    if (selectedState) selectedState.classList.add("d-none");
    if (emptyState) emptyState.classList.remove("d-none");
    if (resumeError) resumeError.classList.add("d-none");
    if (requestError) requestError.classList.add("d-none");

    // Remove analysis_id from URL if present
    if (window.history && window.history.replaceState) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
    window.__INITIAL_ANALYSIS__ = null;
    window.__INITIAL_RECORD_ID__ = null;
    isAnalyzing = false;
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  document.getElementById("analyzeAnotherResume")?.addEventListener("click", resetAnalyzerUI);
  document.getElementById("uploadImprovedResume")?.addEventListener("click", resetAnalyzerUI);

  // Form Submit Handler (AJAX) with in-flight guard & double-click protection
  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (isAnalyzing) return; // In-flight request guard

    const fileOk = validPdf(fileInput.files[0]);
    const jobOk = Boolean(job.value.trim());

    if (resumeError) resumeError.classList.toggle("d-none", fileOk);
    if (jobError) jobError.classList.toggle("d-none", jobOk);

    if (!fileOk || !jobOk) {
      (fileOk ? job : dropzone).focus();
      return;
    }

    isAnalyzing = true;
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.classList.add("disabled");
    }
    if (spinner) spinner.classList.remove("d-none");

    // Immediately render skeleton states inside result cards
    renderSkeletonDashboard();
    form.classList.add("d-none");

    const formData = new FormData(form);
    formData.append("async", "true");

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: formData,
        headers: { 
          "X-Requested-With": "XMLHttpRequest",
          "Accept": "application/json"
        }
      });

      const contentType = response.headers.get("content-type") || "";
      let result;

      if (contentType.includes("application/json")) {
        result = await response.json();
      } else {
        const rawText = await response.text();
        console.error("Non-JSON response received from server:", response.status, rawText);
        if (response.status === 401 || response.url.includes("/login")) {
          throw new Error("Your session has expired. Please log in again to continue.");
        }
        throw new Error("Resume analysis could not be completed. Please try again.");
      }

      if (!response.ok || !result.success) {
        throw new Error(result.error || result.message || "Resume analysis could not be completed. Please try again.");
      }

      if (result.task_id) {
        const taskId = result.task_id;
        let isDone = false;
        let attempts = 0;
        const maxAttempts = 60; // 60 * 1500ms ~ 90s timeout

        while (!isDone && attempts < maxAttempts) {
          attempts++;
          await new Promise(r => setTimeout(r, 1500));
          const pollRes = await fetch(`/api/resume/status/${taskId}`, {
            headers: {
              "X-Requested-With": "XMLHttpRequest",
              "Accept": "application/json"
            }
          });

          const pollContentType = pollRes.headers.get("content-type") || "";
          let statusPayload;
          if (pollContentType.includes("application/json")) {
            statusPayload = await pollRes.json();
          } else {
            const rawPoll = await pollRes.text();
            console.error("Non-JSON polling response:", pollRes.status, rawPoll);
            if (pollRes.status === 401 || pollRes.url.includes("/login")) {
              throw new Error("Your session has expired. Please log in again.");
            }
            throw new Error("Resume analysis could not be completed. Please try again.");
          }

          if (!pollRes.ok || !statusPayload.success) {
            throw new Error(statusPayload.error || statusPayload.message || "Resume analysis could not be completed. Please try again.");
          }

          if (statusPayload.status === "failed") {
            throw new Error(statusPayload.error || statusPayload.message || "Resume analysis could not be completed. Please try again.");
          }

          updateStageTimeline(
            statusPayload.current_step || 1,
            statusPayload.step_name || "Processing resume"
          );

          if (statusPayload.status === "completed") {
            isDone = true;
            renderDashboard(statusPayload);
            break;
          }
        }

        if (!isDone) {
          throw new Error("Resume analysis could not be completed. Please try again.");
        }
      } else if (result.analysis) {
        renderDashboard(result);
      } else {
        throw new Error("Resume analysis could not be completed. Please try again.");
      }
    } catch (err) {
      if (pipelineBanner) pipelineBanner.classList.add("d-none");
      if (dashboard) dashboard.classList.add("d-none");
      if (form) form.classList.remove("d-none");
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.classList.remove("disabled");
      }
      if (spinner) spinner.classList.add("d-none");
      isAnalyzing = false;

      if (requestError) {
        const msgEl = requestError.querySelector("span") || requestError;
        msgEl.textContent = err.message || "Resume analysis could not be completed. Please try again.";
        requestError.classList.remove("d-none");
        requestError.scrollIntoView({ behavior: "smooth" });
      } else {
        alert(err.message || "Resume analysis could not be completed. Please try again.");
      }
    } finally {
      if (spinner) spinner.classList.add("d-none");
    }
  });

  // Check if saved analysis exists from database on initial load/refresh (Requirement 17)
  if (window.__INITIAL_ANALYSIS__) {
    form.classList.add("d-none");
    renderDashboard({
      analysis: window.__INITIAL_ANALYSIS__,
      record_id: window.__INITIAL_RECORD_ID__
    });
  }
});

/* Shared authentication experience. Kept framework-free and scoped to auth pages. */
document.addEventListener("DOMContentLoaded", () => {
  const page = document.querySelector("[data-auth-page]");
  if (!page) return;

  const panel = page.querySelector("#authPanel, .auth-panel");
  const toastPortal = document.getElementById("toastPortal");

  const showAuthToast = (message, category = "info") => {
    if (!toastPortal || !message) return;
    const normalized = category === "error" ? "danger" : category;
    const icon = normalized === "success" ? "check-circle-fill" : normalized === "danger" ? "exclamation-triangle-fill" : "info-circle-fill";
    const toast = document.createElement("div");
    toast.className = `glass-toast glass-toast-${normalized}`;
    toast.setAttribute("role", normalized === "danger" ? "alert" : "status");

    const marker = document.createElement("i");
    marker.className = `bi bi-${icon}`;
    marker.setAttribute("aria-hidden", "true");
    const body = document.createElement("span");
    body.className = "glass-toast-body";
    body.textContent = message;
    const close = document.createElement("button");
    close.type = "button";
    close.className = "glass-toast-close";
    close.setAttribute("aria-label", "Dismiss notification");
    close.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
    close.addEventListener("click", () => toast.remove());
    toast.append(marker, body, close);
    toastPortal.append(toast);
    window.setTimeout(() => {
      toast.classList.add("toast-fadeout");
      toast.addEventListener("animationend", () => toast.remove(), { once: true });
    }, 4800);
  };

  page.querySelectorAll("[data-auth-flash]").forEach(item => showAuthToast(item.textContent.trim(), item.dataset.category || "info"));

  if (page.hasAttribute("data-auth-motion") && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    page.addEventListener("pointermove", event => {
      const x = (event.clientX / window.innerWidth - .5) * 18;
      const y = (event.clientY / window.innerHeight - .5) * 18;
      page.querySelectorAll(".auth-blob").forEach((blob, index) => {
        const depth = (index + 1) * .45;
        blob.style.setProperty("--mouse-x", `${x * depth}px`);
        blob.style.setProperty("--mouse-y", `${y * depth}px`);
      });
    }, { passive: true });
  }

  page.querySelectorAll("[data-password-toggle]").forEach(button => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.passwordToggle);
      if (!input) return;
      const reveal = input.type === "password";
      input.type = reveal ? "text" : "password";
      button.setAttribute("aria-pressed", String(reveal));
      button.setAttribute("aria-label", reveal ? "Hide password" : "Show password");
      const icon = button.querySelector("i");
      if (icon) icon.className = `bi ${reveal ? "bi-eye-slash" : "bi-eye"}`;
      input.focus({ preventScroll: true });
    });
  });

  const passwordRules = value => ({
    length: value.length >= 8,
    upper: /[A-Z]/.test(value),
    lower: /[a-z]/.test(value),
    number: /\d/.test(value),
    special: /[^A-Za-z0-9]/.test(value)
  });

  page.querySelectorAll("[data-strength-input]").forEach(input => {
    const form = input.closest("form");
    const bar = form?.querySelector("[data-strength-bar]");
    const label = form?.querySelector("[data-strength-label]");
    const updateStrength = () => {
      const rules = passwordRules(input.value);
      const score = Object.values(rules).filter(Boolean).length;
      form?.querySelectorAll("[data-requirement]").forEach(item => {
        const valid = Boolean(rules[item.dataset.requirement]);
        item.classList.toggle("is-valid", valid);
        const icon = item.querySelector("i");
        if (icon) icon.className = `bi ${valid ? "bi-check-circle-fill" : "bi-circle"}`;
      });
      if (bar) {
        bar.style.width = input.value ? `${Math.max(12, score * 20)}%` : "0%";
        bar.style.background = score <= 2 ? "#ef4444" : score <= 4 ? "#f59e0b" : "#22c55e";
      }
      if (label) {
        label.textContent = !input.value ? "Not entered" : score <= 2 ? "Weak" : score <= 4 ? "Good" : "Strong";
        label.style.color = score <= 2 ? "#ef4444" : score <= 4 ? "#d97706" : "#15803d";
      }
      return Object.values(rules).every(Boolean);
    };
    input.addEventListener("input", updateStrength);
    updateStrength();
  });

  page.querySelectorAll("[data-confirm-password]").forEach(confirm => {
    const source = document.getElementById(confirm.dataset.confirmPassword);
    const validateMatch = () => {
      const mismatch = Boolean(confirm.value) && confirm.value !== source?.value;
      confirm.setCustomValidity(mismatch ? "Passwords do not match." : "");
      confirm.setAttribute("aria-invalid", String(mismatch));
      confirm.closest(".auth-field")?.classList.toggle("has-error", mismatch);
    };
    confirm.addEventListener("input", validateMatch);
    source?.addEventListener("input", validateMatch);
  });

  page.querySelectorAll("[data-auth-form]").forEach(form => {
    form.querySelectorAll("input").forEach(input => {
      input.addEventListener("input", () => {
        input.setAttribute("aria-invalid", "false");
        input.closest(".auth-field")?.classList.remove("has-error");
      });
      input.addEventListener("invalid", () => {
        input.setAttribute("aria-invalid", "true");
        input.closest(".auth-field")?.classList.add("has-error");
      });
    });

    form.addEventListener("submit", event => {
      let valid = form.checkValidity();
      const strengthInput = form.querySelector("[data-strength-input]");
      if (strengthInput && !Object.values(passwordRules(strengthInput.value)).every(Boolean)) {
        valid = false;
        strengthInput.setAttribute("aria-invalid", "true");
        strengthInput.closest(".auth-field")?.classList.add("has-error");
        showAuthToast("Use all five password requirements before continuing.", "danger");
      }
      const confirmation = form.querySelector("[data-confirm-password]");
      if (confirmation && confirmation.value !== document.getElementById(confirmation.dataset.confirmPassword)?.value) {
        valid = false;
        confirmation.setCustomValidity("Passwords do not match.");
        confirmation.closest(".auth-field")?.classList.add("has-error");
        showAuthToast("The confirmation password does not match.", "danger");
      }
      if (!valid) {
        event.preventDefault();
        form.reportValidity();
        form.querySelector(":invalid")?.focus();
        panel?.classList.add("auth-panel-shake");
        panel?.addEventListener("animationend", () => panel.classList.remove("auth-panel-shake"), { once: true });
        return;
      }

      const button = form.querySelector("[data-auth-submit]");
      const label = button?.querySelector("[data-button-label]");
      if (button) button.disabled = true;
      if (label) label.textContent = form.dataset.loadingText || "Please wait…";
      button?.querySelector("i")?.remove();
      if (button) button.insertAdjacentHTML("afterbegin", '<span class="auth-spinner" aria-hidden="true"></span>');
      form.querySelector("[data-auth-loading-overlay]")?.classList.add("is-visible");
      panel?.querySelector("[data-auth-loading-overlay]")?.classList.add("is-visible");
    });
  });

  page.querySelectorAll(".auth-button").forEach(button => {
    button.addEventListener("pointerdown", event => {
      const rect = button.getBoundingClientRect();
      const ripple = document.createElement("span");
      const size = Math.max(rect.width, rect.height);
      ripple.className = "auth-ripple";
      ripple.style.width = ripple.style.height = `${size}px`;
      ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
      ripple.style.top = `${event.clientY - rect.top - size / 2}px`;
      button.append(ripple);
      ripple.addEventListener("animationend", () => ripple.remove(), { once: true });
    });
  });

  const otpForm = page.querySelector("[data-otp-form]");
  if (otpForm) {
    const boxes = [...otpForm.querySelectorAll(".otp-box")];
    const submitButton = otpForm.querySelector("[data-auth-submit]");
    const submitLabel = submitButton?.querySelector("[data-button-label]");
    window.setTimeout(() => boxes[0]?.focus(), 450);

    boxes.forEach((box, index) => {
      box.addEventListener("input", () => {
        box.value = box.value.replace(/\D/g, "").slice(-1);
        box.classList.remove("is-invalid");
        if (box.value && index < boxes.length - 1) boxes[index + 1].focus();
      });
      box.addEventListener("keydown", event => {
        if (event.key === "Backspace" && !box.value && index > 0) boxes[index - 1].focus();
        if (event.key === "ArrowLeft" && index > 0) boxes[index - 1].focus();
        if (event.key === "ArrowRight" && index < boxes.length - 1) boxes[index + 1].focus();
      });
      box.addEventListener("paste", event => {
        const code = event.clipboardData?.getData("text").replace(/\D/g, "").slice(0, 6) || "";
        if (code.length !== 6) return;
        event.preventDefault();
        boxes.forEach((item, itemIndex) => { item.value = code[itemIndex]; item.classList.remove("is-invalid"); });
        boxes.at(-1)?.focus();
      });
    });

    const timer = page.querySelector("[data-otp-countdown]");
    const resend = page.querySelector("[data-otp-resend]");
    let remaining = Number(timer?.dataset.otpCountdown || 60);
    const renderTimer = () => {
      if (!timer) return;
      timer.textContent = `Resend in 00:${String(Math.max(0, remaining)).padStart(2, "0")}`;
      if (remaining <= 0) { timer.hidden = true; if (resend) resend.hidden = false; }
    };
    renderTimer();
    const countdownId = window.setInterval(() => { remaining -= 1; renderTimer(); if (remaining <= 0) window.clearInterval(countdownId); }, 1000);
    resend?.addEventListener("click", () => {
      resend.disabled = true;
      resend.textContent = "Sending…";
      document.getElementById("authResendForm")?.submit();
    });

    otpForm.addEventListener("submit", async event => {
      event.preventDefault();
      const enteredCode = boxes.map(box => box.value.trim()).join("");
      if (!/^\d{6}$/.test(enteredCode)) {
        boxes.filter(box => !box.value).forEach(box => box.classList.add("is-invalid"));
        showAuthToast("Enter the complete six-digit verification code.", "danger");
        boxes.find(box => !box.value)?.focus();
        return;
      }

      const payload = new FormData(otpForm);
      boxes.forEach(box => { box.readOnly = true; });
      if (submitButton) submitButton.disabled = true;
      if (submitLabel) submitLabel.textContent = "Verifying code…";
      submitButton?.querySelector("i")?.remove();
      submitButton?.insertAdjacentHTML("afterbegin", '<span class="auth-spinner" aria-hidden="true"></span>');

      try {
        const response = await fetch(otpForm.action, { method: "POST", body: payload });
        const destination = new URL(response.url).pathname;
        if (destination.endsWith("/reset-password")) {
          boxes.forEach(box => box.classList.add("is-valid"));
          page.querySelector("[data-otp-success]")?.classList.add("is-visible");
          window.setTimeout(() => { window.location.href = response.url; }, 1000);
          return;
        }
        if (destination.endsWith("/forgot-password")) {
          showAuthToast("The verification code is expired or no longer active.", "danger");
          window.setTimeout(() => { window.location.href = response.url; }, 1400);
          return;
        }
        throw new Error("The verification code is incorrect. Please try again.");
      } catch (error) {
        panel?.classList.add("auth-panel-shake");
        panel?.addEventListener("animationend", () => panel.classList.remove("auth-panel-shake"), { once: true });
        boxes.forEach(box => { box.readOnly = false; box.value = ""; box.classList.add("is-invalid"); });
        submitButton?.querySelector(".auth-spinner")?.remove();
        if (submitButton) submitButton.disabled = false;
        if (submitLabel) submitLabel.textContent = "Verify and continue";
        showAuthToast(error.message || "Unable to verify the code. Please try again.", "danger");
        boxes[0]?.focus();
      }
    });
  }

  const successCountdown = page.querySelector("[data-success-countdown]");
  if (successCountdown) {
    let seconds = Number(successCountdown.dataset.successCountdown || 5);
    const number = successCountdown.querySelector("span");
    const destination = page.dataset.successRedirect;
    const total = seconds;
    const render = () => {
      if (number) number.textContent = String(seconds);
      successCountdown.style.setProperty("--countdown-progress", `${((total - seconds) / total) * 100}%`);
      successCountdown.setAttribute("aria-label", `Redirecting in ${seconds} seconds`);
    };
    render();
    const redirectTimer = window.setInterval(() => {
      seconds -= 1;
      render();
      if (seconds <= 0) {
        window.clearInterval(redirectTimer);
        if (destination) window.location.href = destination;
      }
    }, 1000);

    const confettiRoot = page.querySelector("[data-confetti]");
    const colors = ["#4f46e5", "#7c3aed", "#06b6d4", "#22c55e", "#f59e0b", "#ec4899"];
    if (confettiRoot && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      for (let index = 0; index < 54; index += 1) {
        const piece = document.createElement("i");
        piece.className = "confetti-piece";
        piece.style.left = `${Math.random() * 100}vw`;
        piece.style.background = colors[index % colors.length];
        piece.style.setProperty("--duration", `${2.4 + Math.random() * 2.2}s`);
        piece.style.setProperty("--delay", `${Math.random() * .8}s`);
        piece.style.setProperty("--drift", `${-90 + Math.random() * 180}px`);
        piece.style.setProperty("--spin", `${360 + Math.random() * 720}deg`);
        confettiRoot.append(piece);
      }
    }
  }
});

/* Shared interface behaviors: theme persistence, reveal motion and form state. */
document.addEventListener("DOMContentLoaded", () => {
  const root = document.documentElement;
  const themeButtons = [document.getElementById("themeToggle"), document.getElementById("themeToggleFloating")].filter(Boolean);
  const floatingToggle = document.getElementById("themeToggleFloating");

  const applyTheme = (theme, persist = false) => {
    const resolvedTheme = theme === "dark" ? "dark" : "light";
    root.dataset.theme = resolvedTheme;
    if (persist) localStorage.setItem("interviewai-theme", resolvedTheme);
    themeButtons.forEach(button => {
      const isDark = resolvedTheme === "dark";
      button.setAttribute("aria-pressed", String(isDark));
      button.setAttribute("title", isDark ? "Use light theme" : "Use dark theme");
      const icon = button.querySelector("i");
      if (icon) icon.className = `bi ${isDark ? "bi-sun" : "bi-moon-stars"}`;
    });
    window.dispatchEvent(new CustomEvent("interviewai:themechange", { detail: { theme: resolvedTheme } }));
  };

  applyTheme(root.dataset.theme);
  themeButtons.forEach(button => button.addEventListener("click", () => {
    applyTheme(root.dataset.theme === "dark" ? "light" : "dark", true);
  }));
  if (floatingToggle && document.querySelector(".auth-page-body, .landing-hero")) {
    floatingToggle.classList.add("is-visible");
  }

  const revealTargets = document.querySelectorAll("[data-reveal], .card-glass, .stat-card, .resume-ai-card");
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.08, rootMargin: "0px 0px -24px" });
    revealTargets.forEach(target => { target.classList.add("ui-reveal"); observer.observe(target); });
  } else {
    revealTargets.forEach(target => target.classList.add("is-visible"));
  }

  document.querySelectorAll("form").forEach(form => {
    form.addEventListener("submit", () => form.classList.add("is-submitting"));
    form.querySelectorAll("input, textarea, select").forEach(field => {
      field.addEventListener("invalid", () => field.closest(".form-group-floating, .form-group")?.classList.add("has-error"));
      field.addEventListener("input", () => field.closest(".form-group-floating, .form-group")?.classList.remove("has-error"));
    });
  });
});


/* Premium authenticated workspace interactions. Framework-free and route-safe. */
document.addEventListener("DOMContentLoaded", () => {
  if (!document.body.classList.contains("authenticated-saas")) return;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const toastPortal = document.getElementById("saasToastPortal");
  const showToast = (message, category = "info") => {
    if (!toastPortal || !message) return;
    const tone = category === "error" ? "danger" : category;
    const toast = document.createElement("div");
    toast.className = `saas-toast ${tone}`;
    toast.setAttribute("role", tone === "danger" ? "alert" : "status");
    const icon = document.createElement("i");
    icon.className = `bi bi-${tone === "success" ? "check-circle-fill" : tone === "danger" ? "exclamation-triangle-fill" : "stars"}`;
    const copy = document.createElement("span");
    copy.textContent = message;
    const close = document.createElement("button");
    close.type = "button";
    close.setAttribute("aria-label", "Dismiss notification");
    close.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
    const dismiss = () => {
      toast.classList.add("is-leaving");
      window.setTimeout(() => toast.remove(), 240);
    };
    close.addEventListener("click", dismiss);
    toast.append(icon, copy, close);
    toastPortal.append(toast);
    window.setTimeout(dismiss, 4600);
  };
  window.interviewToast = showToast;
  document.querySelectorAll("[data-saas-flash]").forEach(item => showToast(item.textContent.trim(), item.dataset.category || "info"));
  document.querySelectorAll("[data-saas-toast]").forEach(button => button.addEventListener("click", () => showToast(button.dataset.saasToast)));

  requestAnimationFrame(() => requestAnimationFrame(() => document.body.classList.add("saas-ready")));

  const command = document.getElementById("saasCommand");
  const commandTrigger = document.getElementById("saasCommandTrigger");
  const commandInput = document.getElementById("saasCommandInput");
  const commandLinks = command ? [...command.querySelectorAll("[data-command-label]")] : [];
  const commandEmpty = command?.querySelector(".saas-command-empty");
  const openCommand = () => {
    if (!command) return;
    command.hidden = false;
    document.body.style.overflow = "hidden";
    commandInput?.focus();
  };
  const closeCommand = () => {
    if (!command) return;
    command.hidden = true;
    document.body.style.overflow = "";
    if (commandInput) commandInput.value = "";
    commandLinks.forEach(link => { link.hidden = false; });
    if (commandEmpty) commandEmpty.hidden = true;
  };
  commandTrigger?.addEventListener("click", openCommand);
  command?.querySelector(".saas-command-backdrop")?.addEventListener("click", closeCommand);
  commandInput?.addEventListener("input", () => {
    const query = commandInput.value.trim().toLowerCase();
    let visible = 0;
    commandLinks.forEach(link => {
      const matches = link.dataset.commandLabel.toLowerCase().includes(query);
      link.hidden = !matches;
      if (matches) visible += 1;
    });
    if (commandEmpty) commandEmpty.hidden = visible > 0;
  });
  document.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); command?.hidden ? openCommand() : closeCommand(); }
    if (event.key === "Escape" && command && !command.hidden) closeCommand();
  });

  if (!reduceMotion && window.matchMedia("(min-width: 992px) and (pointer: fine)").matches) {
    document.querySelectorAll(".card-glass, .stat-card, .chart-card, .reports-metric-card, .profile-section, [data-tilt]").forEach(card => {
      let ticking = false;
      card.addEventListener("pointermove", event => {
        if (!ticking) {
          requestAnimationFrame(() => {
            const rect = card.getBoundingClientRect();
            const rotateX = ((event.clientY - rect.top) / rect.height - .5) * -3.2;
            const rotateY = ((event.clientX - rect.left) / rect.width - .5) * 3.2;
            card.style.transform = `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-3px)`;
            ticking = false;
          });
          ticking = true;
        }
      }, { passive: true });
      card.addEventListener("pointerleave", () => { card.style.transform = ""; });
    });
  }

  if (!reduceMotion && "IntersectionObserver" in window) {
    const counterObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const element = entry.target;
        const original = element.textContent.trim();
        const match = original.match(/^([0-9]+(?:\.[0-9]+)?)(.*)$/);
        if (!match || element.children.length) return;
        const target = Number(match[1]);
        const suffix = match[2];
        const started = performance.now();
        const tick = now => {
          const progress = Math.min(1, (now - started) / 900);
          const eased = 1 - Math.pow(1 - progress, 3);
          element.textContent = `${Math.round(target * eased)}${suffix}`;
          if (progress < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
        counterObserver.unobserve(element);
      });
    }, { threshold: .45 });
    document.querySelectorAll(".stat-card-value, .metric-value").forEach(element => counterObserver.observe(element));
  }

  document.querySelectorAll("[data-counter]").forEach(element => {
    if (reduceMotion) return;
    const target = Number(element.dataset.counter || 0);
    const suffix = element.querySelector("small")?.textContent || "";
    const started = performance.now();
    const animate = now => {
      const progress = Math.min(1, (now - started) / 950);
      const value = Math.round(target * (1 - Math.pow(1 - progress, 3)));
      element.firstChild.textContent = String(value);
      if (!element.querySelector("small") && suffix) element.insertAdjacentHTML("beforeend", `<small>${suffix}</small>`);
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  });

  const themeChoices = [...document.querySelectorAll("[data-setting-theme]")];
  const syncSettingsTheme = () => themeChoices.forEach(button => button.classList.toggle("is-active", button.dataset.settingTheme === document.documentElement.dataset.theme));
  themeChoices.forEach(button => button.addEventListener("click", () => {
    const theme = button.dataset.settingTheme;
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("interviewai-theme", theme);
    window.dispatchEvent(new CustomEvent("interviewai:themechange", { detail: { theme } }));
    syncSettingsTheme();
  }));
  syncSettingsTheme();

  const notifications = document.getElementById("settingsNotifications");
  if (notifications) {
    notifications.checked = localStorage.getItem("interviewai-preparation-notifications") !== "off";
    notifications.addEventListener("change", () => {
      localStorage.setItem("interviewai-preparation-notifications", notifications.checked ? "on" : "off");
      showToast(`Preparation notifications ${notifications.checked ? "enabled" : "paused"}.`, "success");
    });
  }

  document.querySelectorAll('a[href]').forEach(link => link.addEventListener("click", event => {
    if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || link.target === "_blank" || link.hasAttribute("download")) return;
    const destination = new URL(link.href, window.location.href);
    if (destination.origin !== window.location.origin || destination.hash) return;
    document.body.classList.add("saas-leaving");
  }));
});
