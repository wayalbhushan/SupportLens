/**
 * app/static/js/app.js
 * --------------------
 * SupportLens Demo UI Client Logic.
 * Handles tab navigation, theme persistence, live vs. cached inference,
 * visual pipeline rendering, benchmark dashboard data, SVG chart rendering,
 * and paginated golden-set exploration with modal inspection.
 */

(function () {
  "use strict";

  // State
  let appState = {
    theme: localStorage.getItem("supportlens_theme") || "light",
    activeTab: "demo",
    health: null,
    curatedExamples: [],
    resultsData: null,
    activeStratum: "stratum_a", // 'stratum_a' or 'blended'
    // Explorer pagination & filtering
    filterIntent: "all",
    filterEscalate: "all",
    filterCorrect: "all",
    searchQuery: "",
    currentPage: 1,
    pageSize: 10,
    filteredItems: [],
  };

  // DOM Elements
  const htmlEl = document.documentElement;
  const themeToggleBtn = document.getElementById("theme-toggle-btn");
  const tabBtnDemo = document.getElementById("tab-btn-demo");
  const tabBtnResults = document.getElementById("tab-btn-results");
  const panelDemo = document.getElementById("panel-demo");
  const panelResults = document.getElementById("panel-results");
  const backendStatusPill = document.getElementById("backend-status-pill");

  // Demo Tab Elements
  const customerInput = document.getElementById("customer-input");
  const exampleChipsContainer = document.getElementById("example-chips");
  const classifyBtn = document.getElementById("classify-btn");
  const clearBtn = document.getElementById("clear-btn");
  const executionModeBadge = document.getElementById("execution-mode-badge");
  const keysNoticeBanner = document.getElementById("keys-notice-banner");
  const pipelineContainer = document.getElementById("pipeline-container");
  const pipelineSourceTag = document.getElementById("pipeline-source-tag");

  // Pipeline Stage Elements
  const stageBadgeA = document.getElementById("stage-badge-a");
  const stageBadgeB = document.getElementById("stage-badge-b");
  const pathAIntent = document.getElementById("path-a-intent");
  const pathAReason = document.getElementById("path-a-reason");
  const pathBSeverity = document.getElementById("path-b-severity");
  const pathBReason = document.getElementById("path-b-reason");
  const escalateBadge = document.getElementById("escalate-decision-badge");
  const escalateReason = document.getElementById("escalate-reason");
  const replyDraftText = document.getElementById("reply-draft-text");
  const replyWordCount = document.getElementById("reply-word-count");
  const replySimTag = document.getElementById("reply-sim-tag");
  const evidenceCountBadge = document.getElementById("evidence-count-badge");
  const evidenceList = document.getElementById("evidence-list");

  // Dashboard Elements
  const sliceStratumABtn = document.getElementById("slice-stratum-a");
  const sliceBlendedBtn = document.getElementById("slice-blended");
  const filterIntent = document.getElementById("filter-intent");
  const filterEscalate = document.getElementById("filter-escalate");
  const filterCorrect = document.getElementById("filter-correct");
  const searchInput = document.getElementById("search-input");
  const datasetTbody = document.getElementById("dataset-tbody");
  const itemsCounter = document.getElementById("items-counter");
  const prevPageBtn = document.getElementById("prev-page-btn");
  const nextPageBtn = document.getElementById("next-page-btn");
  const pageIndicator = document.getElementById("page-indicator");

  // Modal Elements
  const detailModal = document.getElementById("detail-modal");
  const modalCloseBtn = document.getElementById("modal-close-btn");
  const modalTitle = document.getElementById("modal-title");
  const modalStratumBadge = document.getElementById("modal-stratum-badge");
  const modalCustomerText = document.getElementById("modal-customer-text");
  const modalPredIntent = document.getElementById("modal-pred-intent");
  const modalTrueIntent = document.getElementById("modal-true-intent");
  const modalIntentReason = document.getElementById("modal-intent-reason");
  const modalSeverityPill = document.getElementById("modal-severity-pill");
  const modalEscalatePill = document.getElementById("modal-escalate-pill");
  const modalEscalateReason = document.getElementById("modal-escalate-reason");
  const modalReplyDraft = document.getElementById("modal-reply-draft");
  const modalEvidenceBox = document.getElementById("modal-evidence-box");
  const modalScoreG = document.getElementById("modal-score-g");
  const modalReasonG = document.getElementById("modal-reason-g");
  const modalScoreA = document.getElementById("modal-score-a");
  const modalReasonA = document.getElementById("modal-reason-a");
  const modalScoreB = document.getElementById("modal-score-b");
  const modalReasonB = document.getElementById("modal-reason-b");

  /* ==========================================================================
     Theme Management
     ========================================================================== */
  function applyTheme(theme) {
    appState.theme = theme;
    htmlEl.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("supportlens_theme", theme);
    } catch (e) {
      // Ignored if storage is restricted
    }
  }

  themeToggleBtn.addEventListener("click", () => {
    applyTheme(appState.theme === "light" ? "dark" : "light");
  });

  applyTheme(appState.theme);

  /* ==========================================================================
     Tab Navigation
     ========================================================================== */
  function switchTab(tabId) {
    appState.activeTab = tabId;
    if (tabId === "demo") {
      tabBtnDemo.classList.add("active");
      tabBtnDemo.setAttribute("aria-selected", "true");
      tabBtnResults.classList.remove("active");
      tabBtnResults.setAttribute("aria-selected", "false");
      panelDemo.classList.add("active");
      panelResults.classList.remove("active");
    } else {
      tabBtnResults.classList.add("active");
      tabBtnResults.setAttribute("aria-selected", "true");
      tabBtnDemo.classList.remove("active");
      tabBtnDemo.setAttribute("aria-selected", "false");
      panelResults.classList.add("active");
      panelDemo.classList.remove("active");
      // Render dashboard chart and tables when visible
      renderDashboard();
    }
  }

  tabBtnDemo.addEventListener("click", () => switchTab("demo"));
  tabBtnResults.addEventListener("click", () => switchTab("results"));

  /* ==========================================================================
     Backend Health & Initialization
     ========================================================================== */
  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      if (!res.ok) throw new Error("Health check failed");
      const data = await res.json();
      appState.health = data;

      backendStatusPill.className = "status-pill";
      if (data.live_inference_ready) {
        backendStatusPill.classList.add("online");
        backendStatusPill.querySelector(".status-text").textContent = "Live API Ready";
        keysNoticeBanner.style.display = "none";
      } else {
        backendStatusPill.classList.add("cached");
        backendStatusPill.querySelector(".status-text").textContent = "Cached Mode (Zero Keys)";
        keysNoticeBanner.style.display = "flex";
      }
    } catch (err) {
      backendStatusPill.className = "status-pill";
      backendStatusPill.querySelector(".status-text").textContent = "Offline";
    }
  }

  async function loadExamples() {
    try {
      const res = await fetch("/api/examples");
      if (!res.ok) throw new Error("Failed to load examples");
      const examples = await res.json();
      appState.curatedExamples = examples;
      renderExampleChips(examples);
    } catch (e) {
      console.error("Failed to load curated examples", e);
    }
  }

  function renderExampleChips(examples) {
    exampleChipsContainer.innerHTML = "";
    examples.forEach((ex) => {
      const chip = document.createElement("button");
      chip.className = "chip-btn";
      chip.type = "button";
      chip.innerHTML = `
        <span class="chip-tag">${escapeHtml(ex.tag)}</span>
        <span>${escapeHtml(ex.label)}</span>
      `;
      chip.title = ex.description;
      chip.addEventListener("click", () => {
        customerInput.value = ex.text;
        // Trigger classification with explicit cached replay ID
        runClassification({ text: ex.text, force_cached_id: ex.tweet_id });
      });
      exampleChipsContainer.appendChild(chip);
    });
  }

  /* ==========================================================================
     Classification & Visual Pipeline
     ========================================================================== */
  clearBtn.addEventListener("click", () => {
    customerInput.value = "";
    pipelineContainer.style.display = "none";
    executionModeBadge.style.display = "none";
    customerInput.focus();
  });

  customerInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      runClassification({ text: customerInput.value });
    }
  });

  classifyBtn.addEventListener("click", () => {
    runClassification({ text: customerInput.value });
  });

  async function runClassification({ text, force_cached_id = null }) {
    const trimmed = (text || "").trim();
    if (!trimmed) {
      alert("Please enter a customer message or click one of the example chips.");
      customerInput.focus();
      return;
    }

    // Set UI loading state
    classifyBtn.disabled = true;
    classifyBtn.querySelector(".btn-text").textContent = "Processing...";
    classifyBtn.querySelector(".btn-spinner").style.display = "inline-block";

    // Show pipeline container with progressive pending state
    pipelineContainer.style.display = "flex";
    stageBadgeA.className = "stage-status-badge pending";
    stageBadgeA.textContent = "Classifying...";
    stageBadgeB.className = "stage-status-badge pending";
    stageBadgeB.textContent = "Extracting...";

    try {
      const response = await fetch("/api/classify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: trimmed, force_cached_id }),
      });

      if (!response.ok) {
        const errJson = await response.json();
        if (response.status === 422 && errJson.error === "api_key_missing") {
          keysNoticeBanner.style.display = "flex";
          keysNoticeBanner.scrollIntoView({ behavior: "smooth" });
          alert("Live inference requires GEMINI_API_KEY.\nPlease click one of the pre-selected example chips above to run zero-key cached replay.");
          pipelineContainer.style.display = "none";
          return;
        }
        throw new Error(errJson.message || `Server returned ${response.status}`);
      }

      const data = await response.json();
      renderPipelineResults(data);
    } catch (err) {
      alert(`Classification error: ${err.message}`);
      pipelineContainer.style.display = "none";
    } finally {
      classifyBtn.disabled = false;
      classifyBtn.querySelector(".btn-text").textContent = "Run Decoupled Pipeline";
      classifyBtn.querySelector(".btn-spinner").style.display = "none";
    }
  }

  function renderPipelineResults(data) {
    // 1. Visually distinguish Live Inference vs. Cached Example Replay (Requirement 1)
    const isLive = data.execution_mode === "live_inference";
    executionModeBadge.style.display = "inline-flex";
    executionModeBadge.className = `mode-badge ${isLive ? "live" : "cached"}`;
    executionModeBadge.innerHTML = isLive
      ? `<span class="badge-icon">⚡</span><span class="badge-label">Live Inference (Fresh API Call)</span>`
      : `<span class="badge-icon">📦</span><span class="badge-label">Cached Example Replay (Committed Data)</span>`;

    pipelineSourceTag.className = `mode-badge ${isLive ? "live" : "cached"}`;
    pipelineSourceTag.innerHTML = isLive
      ? `<span>⚡ Live Execution via Gemini 3.5 Flash</span>`
      : `<span>📦 Replaying Tweet ${data.tweet_id || ""} from Committed Cache</span>`;

    // 2. Stage Badges Complete
    stageBadgeA.className = "stage-status-badge complete";
    stageBadgeA.textContent = "Complete";
    stageBadgeB.className = "stage-status-badge complete";
    stageBadgeB.textContent = "Complete";

    // 3. Path A Content
    pathAIntent.textContent = data.path_a.intent || "other";
    pathAReason.textContent = data.path_a.reasoning || "Predicted via zero-shot intent classifier.";

    // 4. Path B Content
    const sev = data.path_b.severity || "none";
    pathBSeverity.textContent = sev;
    pathBSeverity.className = `severity-pill ${sev === "none" ? "none" : "override"}`;
    pathBReason.textContent = data.path_b.reason || "Evaluated by independent zero-gated severity extractor.";

    // 5. Orchestrator Decision
    const isEscalate = Boolean(data.orchestrator.escalate);
    escalateBadge.className = `decision-badge ${isEscalate ? "escalate" : "auto-handle"}`;
    escalateBadge.innerHTML = isEscalate
      ? `<span class="decision-icon">⚠️</span><span class="decision-text">HUMAN ESCALATE</span>`
      : `<span class="decision-icon">✓</span><span class="decision-text">AUTO-HANDLE</span>`;
    escalateReason.textContent = data.orchestrator.reason || "Deterministic routing rule applied.";

    // 6. Grounded Reply Draft
    const replyText = data.reply.draft || "No draft generated.";
    replyDraftText.textContent = replyText;
    const words = replyText.trim() ? replyText.trim().split(/\s+/).length : 0;
    replyWordCount.textContent = `${words} words`;

    const sim = Number(data.reply.retrieval_similarity || 0);
    replySimTag.textContent = `Sim: ${sim.toFixed(2)}`;

    // 7. Retrieved Evidence
    const evList = data.reply.evidence_used || [];
    evidenceCountBadge.textContent = `${evList.length} items`;
    evidenceList.innerHTML = "";
    if (evList.length === 0) {
      evidenceList.innerHTML = `<div class="evidence-item">No historical brand evidence retrieved. Standard prompt guidelines applied.</div>`;
    } else {
      evList.forEach((evText) => {
        const itemEl = document.createElement("div");
        itemEl.className = "evidence-item";
        itemEl.textContent = evText;
        evidenceList.appendChild(itemEl);
      });
    }

    // Scroll to pipeline smoothly
    pipelineContainer.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  /* ==========================================================================
     Tab 2: Results Dashboard Logic
     ========================================================================== */
  async function loadDashboardData() {
    if (appState.resultsData) return;
    try {
      const res = await fetch("/api/results");
      if (!res.ok) throw new Error("Failed to load results data");
      const data = await res.json();
      appState.resultsData = data;
      appState.filteredItems = data.items || [];
      renderDashboard();
    } catch (e) {
      console.error("Dashboard data load failure", e);
    }
  }

  // Stratum toggle buttons
  sliceStratumABtn.addEventListener("click", () => {
    appState.activeStratum = "stratum_a";
    sliceStratumABtn.classList.add("active");
    sliceBlendedBtn.classList.remove("active");
    renderHeadlineCards();
    renderTradeoffChart();
  });

  sliceBlendedBtn.addEventListener("click", () => {
    appState.activeStratum = "blended";
    sliceBlendedBtn.classList.add("active");
    sliceStratumABtn.classList.remove("active");
    renderHeadlineCards();
    renderTradeoffChart();
  });

  function renderDashboard() {
    if (!appState.resultsData) {
      loadDashboardData();
      return;
    }
    renderHeadlineCards();
    renderTradeoffChart();
    applyFiltersAndRenderTable();
  }

  function renderHeadlineCards() {
    const data = appState.resultsData.headline_comparison[appState.activeStratum];
    if (!data) return;

    const b1 = data[0];
    const b2 = data[1];
    const agent = data[2];

    document.getElementById("acc-b1").textContent = `${b1.intent_accuracy.toFixed(1)}%`;
    document.getElementById("acc-b2").textContent = `${b2.intent_accuracy.toFixed(1)}%`;
    document.getElementById("acc-agent").textContent = `${agent.intent_accuracy.toFixed(1)}%`;

    document.getElementById("f1-b1").textContent = b1.macro_f1.toFixed(3);
    document.getElementById("f1-b2").textContent = b2.macro_f1.toFixed(3);
    document.getElementById("f1-agent").textContent = agent.macro_f1.toFixed(3);

    document.getElementById("prec-b1").textContent = `${b1.escalation_precision.toFixed(1)}%`;
    document.getElementById("prec-b2").textContent = `${b2.escalation_precision.toFixed(1)}%`;
    document.getElementById("prec-agent").textContent = `${agent.escalation_precision.toFixed(1)}%`;

    document.getElementById("rec-b1").textContent = `${b1.escalation_recall.toFixed(1)}%`;
    document.getElementById("rec-b2").textContent = `${b2.escalation_recall.toFixed(1)}%`;
    document.getElementById("rec-agent").textContent = `${agent.escalation_recall.toFixed(1)}%`;
  }

  // Visualizing the "Safe in the wrong direction" Trade-off Chart (SVG)
  function renderTradeoffChart() {
    const chartContainer = document.getElementById("tradeoff-chart");
    const data = appState.resultsData.headline_comparison[appState.activeStratum];
    if (!data) return;

    // Dimensions
    const width = 600;
    const height = 200;
    const padding = { top: 20, right: 30, bottom: 40, left: 50 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    const systems = [
      { name: "Baseline 1 (Keyword)", prec: data[0].escalation_precision, rec: data[0].escalation_recall },
      { name: "Baseline 2 (LogReg)", prec: data[1].escalation_precision, rec: data[1].escalation_recall },
      { name: "SupportLens Agent", prec: data[2].escalation_precision, rec: data[2].escalation_recall },
    ];

    const groupWidth = chartW / systems.length;
    const barW = 28;

    let svgHtml = `
      <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" style="width: 100%; height: 100%;">
        <!-- Y-Axis Gridlines & Labels -->
        <g class="gridlines">
    `;

    [0, 25, 50, 75, 100].forEach((val) => {
      const y = padding.top + chartH - (val / 100) * chartH;
      svgHtml += `
        <line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" stroke="var(--color-border)" stroke-dasharray="2 2" />
        <text x="${padding.left - 8}" y="${y + 4}" font-size="10" fill="var(--color-text-subtle)" text-anchor="end">${val}%</text>
      `;
    });

    svgHtml += `</g><g class="bars">`;

    systems.forEach((sys, i) => {
      const groupX = padding.left + i * groupWidth + (groupWidth / 2);
      
      // Precision Bar
      const precH = (sys.prec / 100) * chartH;
      const precY = padding.top + chartH - precH;
      const precX = groupX - barW - 2;

      // Recall Bar
      const recH = (sys.rec / 100) * chartH;
      const recY = padding.top + chartH - recH;
      const recX = groupX + 2;

      svgHtml += `
        <!-- ${sys.name} -->
        <rect x="${precX}" y="${precY}" width="${barW}" height="${precH}" fill="#2563EB" rx="3">
          <title>${sys.name} Precision: ${sys.prec.toFixed(1)}%</title>
        </rect>
        <text x="${precX + barW / 2}" y="${precY - 4}" font-size="10" font-weight="700" fill="#2563EB" text-anchor="middle">${sys.prec.toFixed(0)}%</text>

        <rect x="${recX}" y="${recY}" width="${barW}" height="${recH}" fill="#EA580C" rx="3">
          <title>${sys.name} Recall: ${sys.rec.toFixed(1)}%</title>
        </rect>
        <text x="${recX + barW / 2}" y="${recY - 4}" font-size="10" font-weight="700" fill="#EA580C" text-anchor="middle">${sys.rec.toFixed(0)}%</text>

        <!-- X Label -->
        <text x="${groupX}" y="${height - 10}" font-size="11" font-weight="600" fill="var(--color-text)" text-anchor="middle">${sys.name}</text>
      `;
    });

    svgHtml += `</g></svg>`;
    chartContainer.innerHTML = svgHtml;
  }

  /* ==========================================================================
     Dataset Explorer: Filtering & Pagination
     ========================================================================== */
  filterIntent.addEventListener("change", (e) => {
    appState.filterIntent = e.target.value;
    appState.currentPage = 1;
    applyFiltersAndRenderTable();
  });

  filterEscalate.addEventListener("change", (e) => {
    appState.filterEscalate = e.target.value;
    appState.currentPage = 1;
    applyFiltersAndRenderTable();
  });

  filterCorrect.addEventListener("change", (e) => {
    appState.filterCorrect = e.target.value;
    appState.currentPage = 1;
    applyFiltersAndRenderTable();
  });

  searchInput.addEventListener("input", (e) => {
    appState.searchQuery = e.target.value.toLowerCase().trim();
    appState.currentPage = 1;
    applyFiltersAndRenderTable();
  });

  prevPageBtn.addEventListener("click", () => {
    if (appState.currentPage > 1) {
      appState.currentPage--;
      renderTableRows();
    }
  });

  nextPageBtn.addEventListener("click", () => {
    const totalPages = Math.ceil(appState.filteredItems.length / appState.pageSize) || 1;
    if (appState.currentPage < totalPages) {
      appState.currentPage++;
      renderTableRows();
    }
  });

  function applyFiltersAndRenderTable() {
    if (!appState.resultsData) return;
    const all = appState.resultsData.items || [];

    appState.filteredItems = all.filter((item) => {
      // 1. Intent filter
      if (appState.filterIntent !== "all" && item.pred_intent !== appState.filterIntent) {
        return false;
      }
      // 2. Escalation filter
      if (appState.filterEscalate !== "all") {
        const boolVal = appState.filterEscalate === "true";
        if (Boolean(item.pred_escalate) !== boolVal) return false;
      }
      // 3. Accuracy filter
      if (appState.filterCorrect !== "all") {
        const isMatch = Boolean(item.intent_correct);
        if (appState.filterCorrect === "correct" && !isMatch) return false;
        if (appState.filterCorrect === "mismatch" && isMatch) return false;
      }
      // 4. Search query
      if (appState.searchQuery) {
        const q = appState.searchQuery;
        const msg = String(item.text_clean || "").toLowerCase();
        const tid = String(item.tweet_id || "");
        if (!msg.includes(q) && !tid.includes(q)) return false;
      }
      return true;
    });

    renderTableRows();
  }

  function renderTableRows() {
    const total = appState.filteredItems.length;
    const totalPages = Math.ceil(total / appState.pageSize) || 1;
    appState.currentPage = Math.min(appState.currentPage, totalPages);

    const startIdx = (appState.currentPage - 1) * appState.pageSize;
    const endIdx = startIdx + appState.pageSize;
    const pageItems = appState.filteredItems.slice(startIdx, endIdx);

    itemsCounter.textContent = `Showing ${total === 0 ? 0 : startIdx + 1}–${Math.min(endIdx, total)} of ${total} items`;
    pageIndicator.textContent = `Page ${appState.currentPage} of ${totalPages}`;
    prevPageBtn.disabled = appState.currentPage <= 1;
    nextPageBtn.disabled = appState.currentPage >= totalPages;

    datasetTbody.innerHTML = "";

    if (pageItems.length === 0) {
      datasetTbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 24px; color: var(--color-text-subtle);">No items match the active filters.</td></tr>`;
      return;
    }

    pageItems.forEach((item) => {
      const isMatch = Boolean(item.intent_correct);
      const isEsc = Boolean(item.pred_escalate);
      const tr = document.createElement("tr");
      if (!isMatch) tr.classList.add("mismatch-row");

      const g = item.judge_groundedness > 0 ? item.judge_groundedness : "—";
      const a = item.judge_actionability > 0 ? item.judge_actionability : "—";
      const b = item.judge_brand > 0 ? item.judge_brand : "—";

      tr.innerHTML = `
        <td style="font-family: monospace; font-weight: 600;">${item.tweet_id}</td>
        <td class="cell-snippet" title="${escapeHtml(item.text_clean)}">${escapeHtml(item.text_clean)}</td>
        <td><span class="badge-tag" style="background-color: var(--color-primary-light); color: var(--color-primary);">${item.pred_intent}</span></td>
        <td><span class="badge-tag" style="background-color: var(--color-bg); color: var(--color-text);">${item.true_intent}</span></td>
        <td><span class="badge-tag ${item.pred_severity === 'none' ? '' : 'severity-pill override'}">${item.pred_severity}</span></td>
        <td><span class="badge-tag ${isEsc ? 'escalate' : 'autohandle'}">${isEsc ? 'Escalate' : 'Auto'}</span></td>
        <td style="font-family: monospace; white-space: nowrap;">${g} / ${a} / ${b}</td>
        <td><button class="inspect-btn" type="button" data-id="${item.tweet_id}">Inspect</button></td>
      `;

      tr.querySelector(".inspect-btn").addEventListener("click", () => {
        openDetailModal(item);
      });

      datasetTbody.appendChild(tr);
    });
  }

  /* ==========================================================================
     Item Detail Modal Inspection
     ========================================================================== */
  function openDetailModal(item) {
    modalTitle.textContent = `Item Inspection: Tweet ${item.tweet_id}`;
    modalStratumBadge.textContent = `Stratum ${item.stratum || "A"}`;
    modalCustomerText.textContent = item.text_clean;

    modalPredIntent.textContent = item.pred_intent;
    modalTrueIntent.textContent = item.true_intent;
    modalIntentReason.textContent = item.path_a_reasoning || "Predicted via Path A intent classifier.";

    modalSeverityPill.textContent = item.pred_severity;
    modalSeverityPill.className = `severity-pill ${item.pred_severity === "none" ? "none" : "override"}`;

    const isEsc = Boolean(item.pred_escalate);
    modalEscalatePill.className = `decision-badge ${isEsc ? "escalate" : "auto-handle"}`;
    modalEscalatePill.textContent = isEsc ? "HUMAN ESCALATE" : "AUTO-HANDLE";
    modalEscalateReason.textContent = item.escalation_reason || "Deterministic routing policy applied.";

    modalReplyDraft.textContent = item.reply_draft || "No reply draft generated (excluded / other).";

    // Evidence
    modalEvidenceBox.innerHTML = "";
    const evList = item.resolved_evidence || [];
    if (evList.length === 0) {
      modalEvidenceBox.innerHTML = `<span style="color: var(--color-text-subtle);">No historical evidence retrieved.</span>`;
    } else {
      evList.forEach((evText) => {
        const p = document.createElement("p");
        p.textContent = evText;
        modalEvidenceBox.appendChild(p);
      });
    }

    // Judge Scores
    modalScoreG.textContent = item.judge_groundedness > 0 ? `Score ${item.judge_groundedness}` : "Not Evaluated";
    modalReasonG.textContent = item.judge_groundedness_reason || "—";

    modalScoreA.textContent = item.judge_actionability > 0 ? `Score ${item.judge_actionability}` : "Not Evaluated";
    modalReasonA.textContent = item.judge_actionability_reason || "—";

    modalScoreB.textContent = item.judge_brand > 0 ? `Score ${item.judge_brand}` : "Not Evaluated";
    modalReasonB.textContent = item.judge_brand_reason || "—";

    detailModal.style.display = "flex";
    document.body.style.overflow = "hidden";
  }

  function closeDetailModal() {
    detailModal.style.display = "none";
    document.body.style.overflow = "";
  }

  modalCloseBtn.addEventListener("click", closeDetailModal);
  detailModal.addEventListener("click", (e) => {
    if (e.target === detailModal) closeDetailModal();
  });

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && detailModal.style.display === "flex") {
      closeDetailModal();
    }
  });

  /* ==========================================================================
     Utilities
     ========================================================================== */
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Initial Boot
  checkHealth();
  loadExamples();
  loadDashboardData();

})();
