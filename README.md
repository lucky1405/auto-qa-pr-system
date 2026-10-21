# 🛡️ Auto-QA PR Sentinel
### Autonomous Multi-Agent AI Software Quality Team for GitHub PRs

> An end-to-end autonomous software-quality platform that ingests Pull Requests, fans out to specialized review agents, retrieves project-specific conventions via Hybrid RAG, synthesizes automated patches (APR), verifies candidate code inside an isolated execution sandbox with iterative retry loops, generates verified Git commits, and evaluates software reliability and quality telemetry.

---

## 📌 Architecture Overview

```
                                      +------------------------------------+
                                      |        Developer Creates PR        |
                                      +-----------------+------------------+
                                                        |
                                                        v
                                      +------------------------------------+
                                      |    PR Ingestion & Orchestrator     |
                                      +-----------------+------------------+
                                                        |
                            +---------------------------+---------------------------+
                            |                           |                           |
                            v                           v                           v
                 +--------------------+      +--------------------+      +--------------------+
                 | Code Quality Agent |      |   Security Agent   |      |    Test Agent      |
                 | (PEP8/Lint/Smells) |      | (OWASP/CWE/CVSS)   |      | (Coverage/Boundary)|
                 +----------+---------+      +----------+---------+      +----------+---------+
                            |                           |                           |
                            +---------------------------+---------------------------+
                                                        |
                                          (Consolidated Issue Diagnostics)
                                                        |
                                                        v
                                      +------------------------------------+
                                      |         Hybrid RAG Engine          |
                                      |  (BM25 + Cosine Similarity Vector) |
                                      +-----------------+------------------+
                                                        |
                                                        v
                                      +------------------------------------+
                                      |  Fix Agent (Auto Software Repair)  |
                                      |     (Synthesizes Unified Diff)     |
                                      +-----------------+------------------+
                                                        |
                                                        v
+------------------------+            +------------------------------------+
|  Retry Feedback Loop   | <--(Fail)--|    Docker / Subprocess Sandbox     |
| (Max N=3 with error AST|            |    (Pytest, Linters, Security AST) |
+-----------+------------+            +-----------------+------------------+
            |                                           | (Pass)
            +-----------> (Regenerate Patch)            v
                                      +------------------------------------+
                                      |     Verified Git Commit on PR      |
                                      |  (e.g., commit '9f2a8b3c1d')       |
                                      +-----------------+------------------+
                                                        |
                                                        v
                                      +------------------------------------+
                                      |  Quality & Reliability Metrics Hub |
                                      | (SRI, MTBF, Defect Density, MI, DRE|
                                      +------------------------------------+
```

---

## 🌟 Key System Capabilities

1. **Multi-Agent AI Review Swarm:**
   - **Orchestrator:** Coordinates asynchronous review fan-out, retry state machine, and commit generation.
   - **Code Quality Agent:** Analyzes PEP8 compliance, naming rules, docstrings, resource descriptor leaks, and cyclomatic complexity.
   - **Security Agent:** Scans for OWASP Top 10 vulnerabilities (CWE-89 SQL Injection, CWE-78 Command Injection, CWE-798 Hardcoded Secrets, CWE-502 Unsafe Deserialization) with CVSS 3.1 scoring.
   - **Test Coverage Agent:** Identifies boundary condition risks (strict `<` vs `<=`), negative input bypasses, and synthesizes parameterized unit tests.
   - **Fix Agent (Automated Software Repair):** Combines defect locations, RAG guidelines, and previous sandbox failure feedback to synthesize verified patches.

2. **Retrieval-Augmented Generation (RAG):**
   - Indexes project conventions, architectural guidelines, and historical bug fix patterns.
   - Computes RAG evaluation metrics: Retrieval Precision, Recall, Context Relevance, and Groundedness.

3. **Isolated Sandbox Verification (Zero-Trust AI):**
   - Candidate patches are executed in an isolated environment (Docker container or restricted subprocess jail with execution timeouts).
   - Runs full `pytest` suites, AST-level security analyzers, and static linters before any commit is accepted.
   - **Iterative Retry Loop:** If test suites or linters fail, traceback and diagnostic outputs are fed back to the Fix Agent for progressive refinement (up to 3 attempts).

4. **Scalable Worker Architecture:**
   - Non-blocking asynchronous task queue (`ScalableWorkerPool`).
   - Pub/Sub WebSocket event stream broadcasting real-time pipeline status and telemetry.
   - Decoupled worker pool ready for horizontal scale across container clusters.

---

## 📊 Software Quality & Reliability Metrics Suite

The system implements rigorous mathematical formulations according to IEEE and SEI standards:

### 1. Defect Detection & Accuracy Metrics
- **Defect Detection Rate (Recall / Sensitivity):**
  $$\text{DDR} = \frac{TP}{TP + FN}$$
- **False Positive Rate (FPR):**
  $$\text{FPR} = \frac{FP}{FP + TN}$$
- **Precision:**
  $$\text{Precision} = \frac{TP}{TP + FP}$$
- **F1-Score:**
  $$F_1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$

### 2. Software Reliability Metrics (IEEE Standard)
- **Defect Density ($DD$):**
  $$\text{Defect Density} = \frac{\text{Total Defects Found}}{\text{KLOC}} = \frac{\text{Defects}}{\text{LOC} / 1000}$$
- **Software Reliability Index ($SRI$):**
  Evaluates operational failure probability weighted by defect severity and test pass ratio:
  $$SRI = \max\left(0, 100 - (25 N_{\text{crit}} + 15 N_{\text{high}} + 6 N_{\text{med}} + 2 N_{\text{low}})\right) \times \left(\frac{\text{Tests Passed}}{\text{Total Tests}}\right)$$
- **Failure Rate ($\lambda$):**
  Projected failures per 1,000 runtime hours:
  $$\lambda = (N_{\text{crit}} \times 0.12) + (N_{\text{high}} \times 0.05) + (N_{\text{med}} \times 0.015) + (N_{\text{low}} \times 0.002)$$
- **Mean Time Between Failures ($MTBF$):**
  $$\text{MTBF} = \frac{1}{\max(\lambda, 0.0001)} \text{ hours}$$
- **Defect Removal Efficiency ($DRE$):**
  $$\text{DRE} = \frac{\text{Defects Repaired}}{\text{Total Defects Discovered}} \times 100\%$$

### 3. Maintainability & Complexity Metrics
- **McCabe Cyclomatic Complexity ($V(G)$):**
  Number of linearly independent paths through program control flow graph:
  $$V(G) = E - N + 2P$$
- **Halstead Volume ($V$):**
  $$V = (N_1 + N_2) \log_2(n_1 + n_2)$$
- **Maintainability Index ($MI$, SEI Normalized 0-100 scale):**
  $$MI = \max\left(0, \frac{171 - 5.2 \ln(V) - 0.23 V(G) - 16.2 \ln(\text{LOC})}{171} \times 100\right)$$
  *(Score $\ge 85$: High Maintainability, $65-85$: Moderate, $<65$: Low / Technical Debt).*

### 4. Automated Software Repair (APR) Metrics
- **Auto-Fix Success Rate:**
  $$\text{Success Rate} = \frac{\text{Verified Patches Passing Sandbox}}{\text{Total Repair Attempts}}$$
- **Mean Time to Repair ($MTTR$):**
  Average latency in milliseconds from PR ingestion to verified commit.

---

## 🚀 Quickstart & Working Demo

### Prerequisites
- Python 3.10+ (macOS / Linux / Windows)
- Node / Docker optional (Subprocess sandbox runs out-of-the-box with zero extra setup)

### 1. Launch the Server
```bash
cd /Users/lucky/.gemini/antigravity/scratch/auto-qa-pr-system
./run_demo.sh
```
Or run directly:
```bash
./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Access the Application
- **Interactive Web Dashboard:** `http://127.0.0.1:8000`
- **Interactive Swagger REST API:** `http://127.0.0.1:8000/docs`

### 3. Run Automated Tests
```bash
./venv/bin/pytest tests/ -v
```

---

## 🧪 Pre-loaded Scenarios
1. **🛡️ CWE-89 SQL Injection (Security):**
   - User authentication service vulnerable to dynamic string interpolation. Fixed with parameterized query syntax.
2. **💧 File Descriptor Leak (Reliability):**
   - Data exporter opening file without context manager. Wrapped in `with open(...)` to prevent socket/handle starvation.
3. **⚖️ Boundary Off-By-One (Correctness):**
   - Tiered discount calculation with strict `<` missing threshold value 100. Corrected to `<=` with defensive ValueError checks.
4. **✨ Clean Production PR (Quality Baseline):**
   - Clean cryptographic token module passing all linters and tests with 100% reliability.

---

## 🐳 Docker Deployment
To launch with Docker Compose:
```bash
docker-compose up --build
```
To scale the worker pool horizontally to 4 worker containers:
```bash
docker-compose up --scale worker=4
```
