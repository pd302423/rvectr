# rvector — Handoff Document

**Last updated:** 2026-07-13
**Working directory:** `C:\Users\Parth Dalal\rvector`
**Web app root:** `C:\Users\Parth Dalal\rvector\web`
**Repo state:** Local git initialised, not yet pushed to remote.

---

## 1. Main goal

rvector is a **biomechanical precision coaching system for calisthenics athletes** — positioned as "the Qoves of calisthenics." It measures every rep, diagnoses form deviations against peer-reviewed standards, and adapts programming in real time using *Overcoming Gravity* (Low, 2016) periodisation principles.

### Two-phase strategy

| Phase | Target | Deadline / criteria |
|---|---|---|
| **Phase 1 — Science exhibition demo** | Ship a working prototype that demos: AI-generated workouts + live CV form check + adaptive responses | ~6–8 weeks from 2026-05-23 |
| **Phase 2 — B2C SaaS launch** | 500–1K paying subscribers (~$60–120K ARR) via consistent content marketing on TikTok/IG Reels/YouTube Shorts | 12 months from launch |

### Hard-won positioning decisions

- **NOT** "Strava for calisthenics" (social-graph plays lose without distribution)
- **NOT** "AI coach + form check as a feature" (form check IS the moat)
- **YES** "Clinical biomechanical analysis system grounded in peer-reviewed sports science" — Qoves-tier specificity, citation-backed, measurement-obsessed

### Founder context

- Solo learner-builder, new to web stack and ML
- Using coding assistant as primary co-builder
- Has **RTX 5060** locally → can train CV models and run local GPU inference workers
- Has Python 3.10+ installed
- Will create content consistently for distribution
- User does calisthenics personally — this is their niche

---

## 2. 3D Vision & Form Detection Architecture

To accurately extract 3D spatial data, calculate joint angles, and handle complex self-occlusion during advanced calisthenics movements (e.g., Planches, Front Levers), rvector utilizes a two-tier monocular-to-depth vision system:

### A. Hardware Inputs
* **Consumer Tier (2D RGB)**: Users record sets using standard smartphone cameras. The system relies on software-driven **Monocular 3D Human Mesh Recovery** to infer depth.
* **Pro/Dataset Tier (RGB-D / Time-of-Flight)**: Uses depth sensors for millimeter-accurate, ground-truth 3D data.
  * *Development/Budget*: Xbox One Kinect V2 (using `libfreenect2` drivers on Windows/Linux).
  * *Premium/Studio*: Orbbec Femto Bolt.

### B. Core Vision Stack
* **WHAM (World-Grounded Human Motion Capture)**: Reconstructs a 3D skeleton in absolute world space from flat 2D videos, successfully handling fast motion and self-occlusion.
* **SMPL / SMPL-X**: Fits 3D body meshes (72 structural parameters) to calculate precise geometric angles (e.g., assessing pelvic tilt or spinal alignment during a hollow-body hold).
* **2D Alternatives (Fallback)**: YOLO26-Pose or ViTPose++ for highly efficient, occlusion-resistant 2D pose estimation if full 3D mesh recovery isn't required for simpler movements.

### C. Event-Driven Asynchronous Inference Pipeline
Because processing 3D meshes is computationally heavy, the system bypasses Next.js server bottlenecks using an asynchronous pipeline:
1. **Ingestion**: The client uploads the raw video file directly to Object Storage (S3/GCS).
2. **Queue**: The API pushes a processing job to a message queue (RabbitMQ or Redis).
3. **GPU Workers**: An isolated Python/FastAPI worker running on the local RTX 5060 pulls the job, downloads the video, and runs the WHAM/SMPL models.
4. **Data Extraction**: The worker calculates the necessary joint angles, determines form multipliers ($F$), and compiles a diagnosis.
5. **Callback**: The worker returns a structured JSON payload to the main API, updating the Supabase/PostgreSQL database and firing a WebSocket event to notify the user's client app that analysis is complete.

---

## 3. Current status

**Currently:** End of **Week 2** / Beginning of **Week 3** of the build plan.

**Just completed:** Installed `@mediapipe/tasks-vision` and built the telemetry visualizer route `/test/squat`. Created the vector-based joint angle library `web/src/lib/cv/angles.ts` to calculate elbow, hip, knee, and shoulder angles. Set up client-side Pose Landmarker tracking running in a requestAnimationFrame loop with mirrored mode and mobile orientation aspect ratio handling. Verified production build compiles cleanly.

**Next up:** Week 3 Squat Grading: Implement the rules engine, rep counter state machine, per-rep scoring, live score UI, and the rep breakdown panel.

---

## 4. Errors encountered

### ✅ Solved

| # | Error / issue | Cause | Resolution |
|---|---|---|---|
| 1 | `create-next-app` rejected "FitnessApp" folder name | npm naming rules: no capitals | Scaffolded into subdirectory `web/` — cleaner anyway |
| 2 | `npx shadcn add form` silently failed | shadcn 4.8 + base-ui registry quirk for form component specifically | Wrote `form.tsx` manually; installed `@radix-ui/react-slot` for the Slot primitive (Base UI doesn't ship it) |
| 3 | `⚠ The "middleware" file convention is deprecated` warning on every request | Next.js 16 renamed `middleware.ts` → `proxy.ts` | Renamed file, changed exported function name from `middleware` to `proxy` |
| 4 | Runtime error: "Your project's URL and Key are required" when submitting signin form | Server action called `createClient()` without env-guard | Added `isSupabaseConfigured()` check in `sendMagicLink` returning a friendly redirect with error message |
| 5 | UI "looked built by AI" (generic shadcn dark theme, card grids, gradient hero text, glassmorphism) | Out-of-the-box shadcn defaults | Full visual rebuild: removed card grids, switched to editorial asymmetric layout, added Instrument Serif display font, replaced feature grids with one detailed lab-report mockup, removed all gradients and backdrop-blur |
| 6 | Dev server V8 crash after adding large biomechanics knowledge file | Turbopack memory pressure with large TS file | Use `node --max-old-space-size=4096 node_modules/.bin/next dev` flag when needed |
| 7 | Dynamic Tailwind classes `text-${tone}-400` purged at build | Tailwind needs literal class names | Replaced with conditional lookups (`tone === "emerald" ? "text-emerald-400" : ...`) |
| 8 | Dark Reader browser extension corrupting the SVG velocity curve colors | Extension auto-inverts any page | Added `color-scheme: light` in `globals.css` (web standard), and `data-darkreader-ignore` on the specific SVG. User can also pause the extension on localhost. |
| 9 | "failure threshold" SVG text too small | `fontSize="8"` SVG units too tiny | Bumped to 11, repositioned `y="86"`, added explicit monospace font-family |
| 10 | User asked for `rm -rf .next` cleanup but is on Windows | Linux/Mac syntax | Provided PowerShell equivalent: `Remove-Item -Recurse -Force .next` |
| 11 | Next.js build failed complaining about duplicate middleware and proxy files | Both `web/src/middleware.ts` and `web/src/proxy.ts` were present in the directory | Deleted the duplicate `middleware.ts` file and restored `web/src/proxy.ts` as the sole proxy route |

---

## 5. Next steps — Week 3 plan

### Week 3 deliverable
**Goal:** A squat set gets graded 0–100 in real time with rep counting, live scoring UI, and a rep-by-rep breakdown panel.

### Tasks in order

1. **Squat rule engine (`web/src/lib/cv/grade-squat.ts`)**
   * Check minimum knee angle at bottom (depth check, below 90° is good)
   * Check hip-knee tracking (hip angle reaching appropriate depth)
   * Check torso stability (torso lean angle should be 15-45°)
   * Check left vs right knee angle symmetry

2. **Rep counter state machine (`web/src/lib/cv/rep-counter.ts`)**
   * Define states: `up` (elbow > 150°), `descending`, `down` (elbow < 100°), `ascending`
   * Trigger count on `down -> up` transition with time-smoothing hysteresis (≥150ms)

3. **Per-rep scoring**
   * Store joint angles per rep and compute 0–100 score based on depth, hip stability, body line, and tempo

4. **Live score UI & Breakdown Panel**
   * Render large monospaced score that updates per rep with color coding (green/amber/red)
   * Add a table breakdown of completed reps showing exact sub-scores and detected flaws

---

## 6. Tech reference (for AI assistants resuming this project)

### Stack
- Next.js **16.2.6** (App Router) + TypeScript 5
- Tailwind 4 + shadcn **4.8** (Base UI, NOT Radix — except `@radix-ui/react-slot` for form)
- Supabase (free tier, project name: "rvector", project ref: `dshalwuzxoprtqxfdskv`)
- React Hook Form + zod for forms
- Sonner for toasts
- Instrument Serif (display) + Geist Sans (body) + Geist Mono (data)

### Critical Next.js 16 gotchas
- `middleware.ts` is deprecated; use `proxy.ts` with exported `proxy` function
- `cookies()` is async → must `await cookies()`
- Turbopack is default bundler (use `--max-old-space-size=4096` if it crashes)
- Server components handle auth checks (see `page.tsx` pattern)

### Critical shadcn 4.8 gotcha
- Components import from `@base-ui/react/*` not `@radix-ui/react-*`
- Form component (`form.tsx`) was hand-written because shadcn registry doesn't deliver it cleanly; uses `@radix-ui/react-slot` as the one Radix dependency

### Run commands (Windows PowerShell)
```powershell
cd "C:\Users\Parth Dalal\rvector\web"
npm run dev                                    # standard
node --max-old-space-size=4096 node_modules/.bin/next dev   # if Turbopack crashes
Remove-Item -Recurse -Force .next             # clear cache
```

### Environment variables (in `web/.env.local`)
```
NEXT_PUBLIC_SUPABASE_URL=https://dshalwuzxoprtqxfdskv.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<JWT>
ANTHROPIC_API_KEY=(not set yet)
```

### Path conventions
- All app code: `web/src/`
- Pages/routes: `web/src/app/`
- Components: `web/src/components/`
- Libraries: `web/src/lib/`
- Knowledge base: `web/src/lib/knowledge/`
- Migrations: `web/supabase/migrations/`

### Style/voice rules
- **rvector copy is clinical, never motivational.** "Run initial assessment" not "Build your coach". "Contraindications" not "Anything to avoid". "Athlete identification" not "About you".
- **Numbers always tabular-nums + monospace.**
- **Status colors:** emerald-700 = nominal, amber-700 = caution, red-700 = error. Same semantics throughout.
- **Citations matter** — wherever a claim is made, cite the source (NSCA, JSCR, Low, FIG).

---

*This document is maintained manually. Update at the end of every significant work session.*
