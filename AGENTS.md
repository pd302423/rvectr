<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Project Agent Architecture & System Prompts

This workspace is configured with a 6-agent team designed for end-to-end full-stack development, design quality, security auditing, and orchestrator-led workflow execution.

---

## Agent Roster & Workflow Topology

```mermaid
graph TD
    User([User Request]) --> Orchestrator[1. Orchestrator Agent]
    
    Orchestrator --> FE_Dev[2. Frontend Designer]
    Orchestrator --> BE_Dev[3. Backend Developer]
    
    FE_Dev --> FE_Critic[4. Frontend Critic]
    BE_Dev --> BE_Critic[5. Backend Critic]
    
    FE_Critic --> Universal[6. Universal Critic]
    BE_Critic --> Universal
    
    Universal -->|Approved| Orchestrator
    Universal -->|Needs Fixes| Orchestrator
```

---

## Subagent Definitions & Prompts

### 1. `orchestrator`
- **Role**: Master Architect & Task Planner
- **Responsibilities**: Translates user goals into structured execution plans, assigns tasks to builder agents (`frontend-designer`, `backend-developer`), triggers critic agents, and maintains workflow momentum.

### 2. `frontend-designer`
- **Role**: UI/UX Developer & Frontend Architect
- **Responsibilities**: Implements modern, responsive, highly accessible (WCAG 2.2 AA) visual UI components using 8px grid spacing, design tokens, CSS container queries, and glassmorphism styling.

### 3. `frontend-critic`
- **Role**: Visual & UX Quality Audit Agent
- **Responsibilities**: Evaluates UI code for visual hierarchy, layout breaks, color harmony, responsiveness across devices, keyboard navigation, semantic HTML, and fluid micro-animations.

### 4. `backend-developer`
- **Role**: API & Database Engineer
- **Responsibilities**: Designs REST/RPC endpoints, database schemas (Supabase/PostgreSQL), business logic, input validation (Zod), authentication middleware, and unit tests.

### 5. `backend-critic`
- **Role**: Security & Backend Architecture Audit Agent
- **Responsibilities**: Audits APIs and database queries for OWASP vulnerabilities, SQL injection, auth bypass, N+1 query performance issues, atomic transactions, and strict type safety.

### 6. `universal-critic`
- **Role**: End-to-End Quality & Integration Overseer
- **Responsibilities**: Verifies full-stack contract alignment (Frontend props <-> Backend endpoints), verifies build integrity, checks user goal satisfaction, and resolves conflicts between subagent branches.


# Current runtime and working-copy guidance (27 October 2026)

Read docs/LINUX_FIRST.md for native Linux and WSL setup. Use the declared Python
3.11 project and uv.lock. Run `bash tools/bootstrap-linux.sh` for the CPU test
environment. Add `--pose` for CPU pose inference, `--cuda --pose` for NVIDIA GPU
inference, and `--web` for the site. Normal runs use `uv run --no-sync`.

Private data and model locations are supplied through .env.local. Capture JSON
files contain relative recording and calibration names, not machine-specific
drive paths. Keep private data, recordings, calibration and model weights outside
published source. Preserve timestamps, missing observations, failed attempts and
run IDs. An environment check, a passing test or a plausible 3D model is not an
accuracy result.

See docs/TWO_CAMERA_PIPELINE.md for the squat pipeline. The owner keeps a private
audit of older files in the Git history.

## Luna delegation policy (user preference)

- The parent agent owns architecture, task decomposition, acceptance criteria, integration, and final review.
- Delegate bounded implementation, research, or testing tasks to model `gpt-6-luna` explicitly. Give each worker a fresh context and concise, self-contained brief; request a short evidence summary.
- Normally use one worker, with at most two independent workers concurrently.
- Use medium reasoning by default and low for simple scans; increase reasoning only when justified by the task.
- Do not use Astra or any other non-Luna worker unless the user explicitly authorizes it.
- Do not spawn agents just to fill roles. Avoid duplicate investigations and concurrent edits to the same file.
- This user preference supersedes the earlier generic six-agent roster above.
