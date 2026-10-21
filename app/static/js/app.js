/**
 * Auto-QA PR Sentinel - Client Application
 * Handles reactive UI, WebSockets, multi-agent pipeline orchestration, and metrics charts.
 */

let scenarios = [];
let currentScenario = null;
let currentTaskId = null;
let socket = null;
let qualityRadarChart = null;
let complexityBarChart = null;

// Initialize Application
document.addEventListener("DOMContentLoaded", async () => {
  setupTabs();
  setupEventListeners();
  await loadHealth();
  await loadScenarios();
  await loadRAGDocuments();
  initCharts();
});

// Tab Navigation
function setupTabs() {
  const tabs = document.querySelectorAll(".tab-btn");
  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const target = document.getElementById(btn.dataset.tab);
      if (target) target.classList.add("active");
    });
  });
}

// Event Listeners
function setupEventListeners() {
  document.getElementById("btn-run-swarm").addEventListener("click", runSwarmPipeline);
  document.getElementById("btn-run-benchmark").addEventListener("click", runBatchBenchmark);
  document.getElementById("btn-search-rag").addEventListener("click", searchRAG);
  document.getElementById("rag-query-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") searchRAG();
  });
  document.getElementById("btn-clear-terminal").addEventListener("click", () => {
    document.getElementById("terminal-logs").innerHTML = "";
  });
}

// System Health Check
async function loadHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    const statusText = document.getElementById("system-status-text");
    statusText.textContent = `Active • ${data.concurrency} Workers • Sandbox: ${data.sandbox_mode}`;
  } catch (e) {
    console.error("Health check failed:", e);
  }
}

// Load Preset Scenarios
async function loadScenarios() {
  try {
    const res = await fetch("/api/scenarios");
    scenarios = await res.json();
    const container = document.getElementById("scenario-selector-container");
    container.innerHTML = "";

    scenarios.forEach((sc, idx) => {
      const card = document.createElement("div");
      card.className = `scenario-card ${idx === 0 ? "selected" : ""}`;
      card.dataset.id = sc.id;

      const tagClass = `tag-${sc.category.toLowerCase()}`;
      card.innerHTML = `
        <span class="scenario-tag ${tagClass}">${sc.category}</span>
        <div style="font-size: 0.82rem; font-weight: 600; margin-bottom: 0.2rem;">${sc.title}</div>
        <div style="font-size: 0.72rem; color: var(--text-muted);">${sc.description.slice(0, 95)}...</div>
      `;

      card.addEventListener("click", () => selectScenario(sc.id));
      container.appendChild(card);
    });

    if (scenarios.length > 0) {
      selectScenario(scenarios[0].id);
    }
  } catch (e) {
    console.error("Failed to load scenarios:", e);
  }
}

// Select Scenario
function selectScenario(scenarioId) {
  document.querySelectorAll(".scenario-card").forEach(c => {
    c.classList.toggle("selected", c.dataset.id === scenarioId);
  });

  currentScenario = scenarios.find(s => s.id === scenarioId);
  if (!currentScenario) return;

  document.getElementById("current-filename").textContent = currentScenario.filename;
  document.getElementById("pr-meta-author").textContent = `Author: ${currentScenario.author} • Branch: ${currentScenario.branch}`;
  document.getElementById("input-code").value = currentScenario.content;
  document.getElementById("input-test-code").value = currentScenario.test_content || "";

  // Reset visualizer & output
  resetPipelineVisualizer();
  document.getElementById("diff-output").innerHTML = `<span style="color: var(--text-muted);">Selected scenario: <strong>${currentScenario.title}</strong>.<br>Click 'Run Autonomous QA Swarm' to initiate review.</span>`;
  document.getElementById("verified-commit-pill").style.display = "none";
  document.getElementById("issues-list").innerHTML = `<div style="font-size: 0.8rem; color: var(--text-muted); padding: 1rem 0;">Ready for review...</div>`;
  document.getElementById("issue-count-badge").textContent = "0 issues";
}

// Reset Visualizer
function resetPipelineVisualizer() {
  ["node-ingest", "node-fanout", "node-rag", "node-fix", "node-sandbox", "node-verdict"].forEach(id => {
    const el = document.getElementById(id);
    el.className = "pipeline-node";
  });
  document.getElementById("pipeline-status-badge").textContent = "Idle";
  document.getElementById("pipeline-status-badge").style.color = "#38bdf8";
}

function updatePipelineStep(step, state) {
  // state: 'active', 'done', 'failed'
  const stepMap = {
    "INGESTION": "node-ingest",
    "FAN_OUT": "node-fanout",
    "REVIEW_AGGREGATION": "node-fanout",
    "RAG_RETRIEVAL": "node-rag",
    "REPAIR_ATTEMPT": "node-fix",
    "SANDBOX_DISPATCH": "node-sandbox",
    "SANDBOX_PASSED": "node-sandbox",
    "SANDBOX_FAILED": "node-sandbox",
    "PIPELINE_COMPLETE": "node-verdict",
    "CLEAN_PR": "node-fanout",
    "VERDICT": "node-verdict"
  };

  const nodeId = stepMap[step];
  if (!nodeId) return;

  const node = document.getElementById(nodeId);
  if (!node) return;

  if (state === "active") {
    node.className = "pipeline-node active";
  } else if (state === "done") {
    node.className = "pipeline-node done";
  } else if (state === "failed") {
    node.className = "pipeline-node failed";
  }
}

// Append Terminal Log
function appendLog(time, stage, msg) {
  const terminal = document.getElementById("terminal-logs");
  const row = document.createElement("div");
  row.className = "log-entry";
  row.innerHTML = `
    <span class="log-time">[${typeof time === 'number' ? time.toFixed(2) + 's' : time}]</span>
    <span class="log-stage">[${stage}]</span>
    <span class="log-msg">${escapeHtml(msg)}</span>
  `;
  terminal.appendChild(row);
  terminal.scrollTop = terminal.scrollHeight;
}

// Run Swarm Pipeline
async function runSwarmPipeline() {
  const code = document.getElementById("input-code").value;
  const testCode = document.getElementById("input-test-code").value;
  const filename = document.getElementById("current-filename").textContent;

  const btn = document.getElementById("btn-run-swarm");
  btn.disabled = true;
  btn.innerHTML = `<span>⏳ Orchestrating Swarm...</span>`;
  resetPipelineVisualizer();
  updatePipelineStep("INGESTION", "active");

  appendLog("0.00s", "ORCHESTRATOR", `Received PR review request for '${filename}'`);

  try {
    // 1. Submit PR to async task queue
    const res = await fetch("/api/pr/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: currentScenario ? currentScenario.title : "Custom PR Review",
        description: currentScenario ? currentScenario.description : "",
        filename: filename,
        code: code,
        test_code: testCode,
        run_synchronous: false
      })
    });

    const data = await res.json();
    currentTaskId = data.task_id;

    // 2. Open WebSocket connection for real-time telemetry streaming
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${window.location.host}/api/ws/task/${currentTaskId}`;
    
    if (socket) {
      socket.close();
    }

    socket = new WebSocket(wsUrl);

    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === "PIPELINE_EVENT") {
        const ev = msg.event;
        appendLog(ev.timestamp, ev.stage, ev.message);
        updatePipelineStep(ev.stage, "active");

        if (ev.stage === "SANDBOX_PASSED") {
          updatePipelineStep("SANDBOX_DISPATCH", "done");
          updatePipelineStep("REPAIR_ATTEMPT", "done");
        } else if (ev.stage === "SANDBOX_FAILED") {
          updatePipelineStep("SANDBOX_DISPATCH", "failed");
        }
      }

      if (msg.type === "TASK_COMPLETED") {
        updatePipelineStep("PIPELINE_COMPLETE", "done");
        document.getElementById("pipeline-status-badge").textContent = "Completed";
        document.getElementById("pipeline-status-badge").style.color = "#34d399";
        btn.disabled = false;
        btn.innerHTML = `<span>⚡ Run Autonomous QA Swarm</span>`;

        // Render Results
        renderPipelineResult(msg.pipeline_result);
        renderQualityReport(msg.quality_report);
        socket.close();
      }

      if (msg.type === "TASK_FAILED") {
        document.getElementById("pipeline-status-badge").textContent = "Failed";
        document.getElementById("pipeline-status-badge").style.color = "#f43f5e";
        appendLog("ERR", "ERROR", msg.error);
        btn.disabled = false;
        btn.innerHTML = `<span>⚡ Run Autonomous QA Swarm</span>`;
        socket.close();
      }
    };

    socket.onerror = (err) => {
      console.warn("WebSocket fallback to polling:", err);
      pollTask(currentTaskId);
    };

  } catch (err) {
    console.error("Pipeline invocation error:", err);
    appendLog("ERR", "ERROR", err.message);
    btn.disabled = false;
    btn.innerHTML = `<span>⚡ Run Autonomous QA Swarm</span>`;
  }
}

// Fallback Polling
async function pollTask(taskId) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/api/pr/task/${taskId}`);
      const data = await res.json();
      if (data.status === "COMPLETED") {
        clearInterval(interval);
        renderPipelineResult(data.pipeline_result);
        renderQualityReport(data.quality_report);
        document.getElementById("btn-run-swarm").disabled = false;
        document.getElementById("btn-run-swarm").innerHTML = `<span>⚡ Run Autonomous QA Swarm</span>`;
      } else if (data.status === "FAILED") {
        clearInterval(interval);
        document.getElementById("btn-run-swarm").disabled = false;
        document.getElementById("btn-run-swarm").innerHTML = `<span>⚡ Run Autonomous QA Swarm</span>`;
      }
    } catch (e) {
      clearInterval(interval);
    }
  }, 300);
}

// Render Pipeline Results
function renderPipelineResult(result) {
  if (!result) return;

  // 1. Render Commit Hash Pill
  const commitPill = document.getElementById("verified-commit-pill");
  if (result.verified_commit_hash) {
    commitPill.style.display = "inline-flex";
    document.getElementById("commit-hash-val").textContent = result.verified_commit_hash;
  } else {
    commitPill.style.display = "none";
  }

  // 2. Render Diff
  const diffBox = document.getElementById("diff-output");
  if (result.final_patch && result.final_patch.unified_diff) {
    const lines = result.final_patch.unified_diff.split("\n");
    diffBox.innerHTML = lines.map(line => {
      let cls = "";
      if (line.startsWith("+") && !line.startsWith("+++")) cls = "diff-line-add";
      else if (line.startsWith("-") && !line.startsWith("---")) cls = "diff-line-del";
      else if (line.startsWith("@@") || line.startsWith("---") || line.startsWith("+++")) cls = "diff-line-hdr";
      return `<div class="${cls}">${escapeHtml(line)}</div>`;
    }).join("");
  } else {
    diffBox.innerHTML = `<div style="color: #34d399; padding: 1rem;">✅ Clean PR! All baseline unit tests and security checks passed without requiring patch synthesis.</div>`;
  }

  // 3. Render Issues
  const issuesContainer = document.getElementById("issues-list");
  issuesContainer.innerHTML = "";
  const allIssues = [];
  result.agent_results.forEach(a => allIssues.push(...a.issues));

  document.getElementById("issue-count-badge").textContent = `${allIssues.length} issues identified`;

  if (allIssues.length === 0) {
    issuesContainer.innerHTML = `<div style="color: #34d399; font-size: 0.8rem; padding: 0.5rem 0;">Zero defects detected! Code adheres to all security and style standards.</div>`;
  } else {
    allIssues.forEach(issue => {
      const card = document.createElement("div");
      card.className = `issue-card ${issue.severity}`;
      card.innerHTML = `
        <div class="issue-header">
          <span style="color:#f8fafc;">${escapeHtml(issue.title)}</span>
          <span style="font-size: 0.7rem; font-weight:700;">${issue.severity}</span>
        </div>
        <div class="issue-desc">${escapeHtml(issue.description)}</div>
        ${issue.suggested_fix ? `<div class="issue-fix">🔧 Fix: ${escapeHtml(issue.suggested_fix)}</div>` : ""}
      `;
      issuesContainer.appendChild(card);
    });
  }
}

// Render Quality and Reliability Metrics
function renderQualityReport(report) {
  if (!report) return;

  // Grade
  const gradeBadge = document.getElementById("grade-badge");
  gradeBadge.textContent = report.overall_quality_grade;
  gradeBadge.className = `grade-badge grade-${report.overall_quality_grade[0]}`;
  document.getElementById("metrics-grade-expl").textContent = report.grade_explanation;

  // KPIs
  document.getElementById("metric-ddr").textContent = `${(report.accuracy.recall_defect_detection_rate * 100).toFixed(0)}%`;
  document.getElementById("metric-fpr").textContent = `${(report.accuracy.false_positive_rate * 100).toFixed(1)}%`;
  document.getElementById("metric-fix-rate").textContent = `${(report.repair.auto_fix_success_rate * 100).toFixed(0)}%`;
  document.getElementById("metric-sri").textContent = report.reliability.software_reliability_index.toFixed(1);
  document.getElementById("metric-mtbf").textContent = `${report.reliability.projected_mtbf_hours.toLocaleString()}h`;
  document.getElementById("metric-density").textContent = report.reliability.defect_density_per_kloc.toFixed(1);
  document.getElementById("metric-mi").textContent = report.post_patch_complexity.maintainability_index.toFixed(1);
  document.getElementById("metric-mttr").textContent = `${report.repair.mean_time_to_repair_ms.toFixed(0)}ms`;

  // Formulas
  const formulasContainer = document.getElementById("formulas-container");
  formulasContainer.innerHTML = "";
  for (const [name, desc] of Object.entries(report.formulas_and_explanations || {})) {
    const box = document.createElement("div");
    box.className = "formula-box";
    box.innerHTML = `
      <div class="formula-name">${name}</div>
      <div class="formula-text">${desc}</div>
    `;
    formulasContainer.appendChild(box);
  }

  // Update Charts
  updateCharts(report);
}

// Initialize Charts
function initCharts() {
  const radarCtx = document.getElementById("qualityRadarChart").getContext("2d");
  qualityRadarChart = new Chart(radarCtx, {
    type: "radar",
    data: {
      labels: ["Security Defense", "Maintainability", "Test Reliability", "Bug Defect Density", "RAG Grounding", "Repair Accuracy"],
      datasets: [{
        label: "Quality Score",
        data: [95, 88, 92, 90, 96, 100],
        backgroundColor: "rgba(59, 130, 246, 0.25)",
        borderColor: "#3b82f6",
        pointBackgroundColor: "#60a5fa",
        pointBorderColor: "#fff"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          min: 0,
          max: 100,
          ticks: { color: "#94a3b8", backdropColor: "transparent" },
          grid: { color: "rgba(255, 255, 255, 0.08)" },
          angleLines: { color: "rgba(255, 255, 255, 0.08)" }
        }
      },
      plugins: {
        legend: { labels: { color: "#e2e8f0" } }
      }
    }
  });

  const barCtx = document.getElementById("complexityBarChart").getContext("2d");
  complexityBarChart = new Chart(barCtx, {
    type: "bar",
    data: {
      labels: ["Cyclomatic Complexity", "Cognitive Complexity", "Lines of Code (LOC)"],
      datasets: [
        {
          label: "Pre-Patch",
          data: [6, 4, 25],
          backgroundColor: "rgba(244, 63, 94, 0.6)",
          borderColor: "#f43f5e",
          borderWidth: 1
        },
        {
          label: "Post-Patch (Repaired)",
          data: [4, 2, 28],
          backgroundColor: "rgba(16, 185, 129, 0.6)",
          borderColor: "#10b981",
          borderWidth: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(255, 255, 255, 0.05)" } },
        y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(255, 255, 255, 0.05)" } }
      },
      plugins: {
        legend: { labels: { color: "#e2e8f0" } }
      }
    }
  });
}

function updateCharts(report) {
  if (qualityRadarChart) {
    const sri = report.reliability.software_reliability_index;
    const mi = report.post_patch_complexity.maintainability_index;
    const rag = report.rag.groundedness_faithfulness_score * 100;
    const fix = report.repair.auto_fix_success_rate * 100;
    qualityRadarChart.data.datasets[0].data = [
      Math.min(100, sri * 1.02),
      mi,
      report.test_coverage_pct,
      Math.max(60, 100 - report.reliability.defect_density_per_kloc * 2),
      rag,
      fix
    ];
    qualityRadarChart.update();
  }

  if (complexityBarChart) {
    complexityBarChart.data.datasets[0].data = [
      report.pre_patch_complexity.cyclomatic_complexity,
      report.pre_patch_complexity.cognitive_complexity,
      report.pre_patch_complexity.loc
    ];
    complexityBarChart.data.datasets[1].data = [
      report.post_patch_complexity.cyclomatic_complexity,
      report.post_patch_complexity.cognitive_complexity,
      report.post_patch_complexity.loc
    ];
    complexityBarChart.update();
  }
}

// Run Batch Benchmark
async function runBatchBenchmark() {
  const btn = document.getElementById("btn-run-benchmark");
  btn.disabled = true;
  btn.innerHTML = `<span>⏳ Evaluating Scenarios...</span>`;

  try {
    const res = await fetch("/api/benchmark/run", { method: "POST" });
    const data = await res.json();

    document.getElementById("benchmark-summary-box").style.display = "block";
    document.getElementById("bench-count").textContent = data.benchmark_summary.scenarios_evaluated;
    document.getElementById("bench-ddr").textContent = `${data.benchmark_summary.defect_detection_rate_pct}%`;
    document.getElementById("bench-fpr").textContent = `${data.benchmark_summary.false_positive_rate_pct}%`;
    document.getElementById("bench-fix-rate").textContent = `${data.benchmark_summary.auto_fix_success_rate_pct}%`;
    document.getElementById("bench-sri").textContent = data.benchmark_summary.mean_software_reliability_index.toFixed(1);
    document.getElementById("bench-latency").textContent = `${data.benchmark_summary.mean_latency_ms.toFixed(0)}ms`;

    const tbody = document.getElementById("benchmark-tbody");
    tbody.innerHTML = "";

    data.results.forEach(r => {
      const tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border-color)";

      const q = r.quality_report;
      const pipe = r.pipeline_result;

      tr.innerHTML = `
        <td style="padding: 0.75rem; font-weight:600;">${escapeHtml(r.title)}</td>
        <td style="padding: 0.75rem;"><span class="scenario-tag tag-${r.category.toLowerCase()}">${r.category}</span></td>
        <td style="padding: 0.75rem; color:#34d399;">${pipe ? pipe.status : "COMPLETED"}</td>
        <td style="padding: 0.75rem;">${q ? q.accuracy.true_positives : 0} fixed</td>
        <td style="padding: 0.75rem; font-weight:700;">${q ? q.reliability.software_reliability_index.toFixed(1) : 100}</td>
        <td style="padding: 0.75rem;">${q ? q.post_patch_complexity.maintainability_index.toFixed(1) : 90}</td>
        <td style="padding: 0.75rem; color:var(--text-muted);">${pipe ? pipe.total_latency_ms.toFixed(0) + 'ms' : '-'}</td>
      `;
      tbody.appendChild(tr);
    });

  } catch (err) {
    console.error("Benchmark error:", err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span>▶ Run Benchmark Suite</span>`;
  }
}

// Load RAG Documents
async function loadRAGDocuments() {
  try {
    const res = await fetch("/api/rag/documents");
    const docs = await res.json();
    document.getElementById("rag-doc-count").textContent = `${docs.length} documents`;

    const container = document.getElementById("rag-documents-container");
    container.innerHTML = "";

    docs.forEach(doc => {
      const card = document.createElement("div");
      card.className = "card";
      card.style.marginBottom = "0.75rem";
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; margin-bottom:0.35rem;">
          <span style="font-size:0.75rem; color:#60a5fa; font-weight:700;">${doc.id} • ${doc.category}</span>
        </div>
        <div style="font-size:0.85rem; font-weight:600; margin-bottom:0.25rem;">${escapeHtml(doc.title)}</div>
        <div style="font-size:0.76rem; color:var(--text-muted); margin-bottom:0.5rem;">${escapeHtml(doc.content)}</div>
        ${doc.fix_pattern ? `<pre style="font-size:0.7rem; background:#0d121d; padding:0.5rem; border-radius:6px; color:#34d399; overflow:auto;">${escapeHtml(doc.fix_pattern)}</pre>` : ""}
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error("Failed to load RAG docs:", err);
  }
}

// Search RAG
async function searchRAG() {
  const query = document.getElementById("rag-query-input").value.trim();
  if (!query) return;

  const resultsBox = document.getElementById("rag-search-results");
  resultsBox.innerHTML = `<div style="color:var(--text-muted); font-size:0.8rem;">Searching vector space...</div>`;

  try {
    const res = await fetch("/api/rag/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, top_k: 3 })
    });
    const data = await res.json();

    resultsBox.innerHTML = "";
    if (data.results.length === 0) {
      resultsBox.innerHTML = `<div style="color:var(--text-muted); font-size:0.8rem;">No documents exceeded similarity threshold.</div>`;
      return;
    }

    data.results.forEach(d => {
      const card = document.createElement("div");
      card.className = "card";
      card.style.marginBottom = "0.75rem";
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; margin-bottom:0.25rem;">
          <span style="font-size:0.72rem; color:#93c5fd; font-weight:700;">${d.id} • ${d.category}</span>
          <span style="font-size:0.72rem; background:rgba(59,130,246,0.2); color:#60a5fa; padding:0.1rem 0.4rem; border-radius:4px;">Score: ${(d.similarity_score * 100).toFixed(0)}%</span>
        </div>
        <div style="font-size:0.82rem; font-weight:600; margin-bottom:0.25rem;">${escapeHtml(d.title)}</div>
        <div style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(d.content)}</div>
      `;
      resultsBox.appendChild(card);
    });
  } catch (err) {
    console.error("RAG search failed:", err);
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
