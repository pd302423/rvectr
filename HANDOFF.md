# Vector — Handoff Document

**Last updated:** 2026-05-23
**Working directory:** `C:\Users\Parth Dalal\FitnessApp`
**Web app root:** `C:\Users\Parth Dalal\FitnessApp\web`
**Repo state:** Local git initialised, not yet pushed to remote.

---

## 1. Main goal

Vector is a **biomechanical precision coaching system for calisthenics athletes** — positioned as "the Qoves of calisthenics." It measures every rep, diagnoses form deviations against peer-reviewed standards, and adapts programming in real time using *Overcoming Gravity* (Low, 2016) periodisation principles.

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
- Using Claude Code as primary co-builder
- Has **RTX 5060** locally → can train CV models without Colab
- Has Python 3.10+ installed
- Will create content consistently for distribution
- User does calisthenics personally — this is their niche

---

## 2. Current status

**Currently:** End of **Week 1** of the 8-week build plan.

**Just completed:** Supabase setup — schema migration ran successfully, awaiting user to finish URL config + email template, then test the end-to-end sign-in flow.

**Next up:** Once auth verified working → start **Week 2: AI coach v1 (workout generation)**. User has elected to build the UI scaffolding with mocked Claude responses since no Anthropic API key yet.

### 8-week plan progress

| Week | Subject | Status |
|---|---|---|
| 1 | Scaffold + Supabase + onboarding | ✅ Complete (pending auth verification) |
| 2 | AI coach v1 — workout generation with mocked responses | 🟡 Next |
| 3 | Workout logging UI + session flow | ⬜ Pending |
| 4 | Progression engine (adaptive next-workout) | ⬜ Pending |
| 5 | Form classifier training (local, RTX 5060) | ⬜ Pending |
| 6 | CV form check integration (MediaPipe + ONNX classifier) | ⬜ Pending |
| 7 | AI-written weekly review + Google Fit sync | ⬜ Pending |
| 8 | Polish + (stretch) photo calorie + exhibition prep | ⬜ Pending |

---

## 3. Steps accomplished

### Infrastructure
- Next.js 16 + TypeScript + Tailwind 4 scaffolded in `web/`
- shadcn 4.8 with Base UI primitive set installed
- 19 shadcn components added (button, card, input, label, form, dialog, etc.)
- Supabase client/server/proxy plumbing in `web/src/lib/supabase/`
- `env.ts` safety guard — app renders gracefully without Supabase keys
- Git initialised at project root, `.gitignore` excludes node_modules, .env files, `.claude/settings.local.json`

### Database (Supabase)
- Migration ran: `web/supabase/migrations/001_init.sql`
- `profiles` table extending `auth.users` with: `display_name`, `experience_level`, `current_skills[]`, `goal_skills[]`, `equipment[]`, `days_per_week`, `session_minutes`, `injuries`, `onboarded`
- Row Level Security policies (users only see/edit own row)
- Auto-update `updated_at` trigger
- Auto-create-profile-on-signup trigger via `handle_new_user()` function

### Auth
- `/signin` page with passwordless magic link UI
- `sendMagicLink` server action with env-guard
- `/auth/confirm` route handler with OTP verification + onboarded-based routing
- `/auth/signout` POST route
- `proxy.ts` (renamed from deprecated `middleware.ts` in Next 16) refreshes Supabase session on every request

### UI pages
- `/` — editorial homepage with hero, methodology essay (with citations + pull quote), sample session report mockup (rep-by-rep table + SVG velocity curve + diagnosis prose), spec table of measurements, minimal CTA, footer
- `/signin` — split layout, data callout strip
- `/onboarding` — 6-section validated form (zod + react-hook-form): athlete ID, training frequency, equipment, current skills, goal skills, contraindications
- `/dashboard` — protected, displays athlete profile data in clinical grid layout

### Knowledge base
- `web/src/lib/calisthenics.ts` — 33-skill catalog (push/pull/core/legs/skill) with difficulty ratings 1–5
- `web/src/lib/knowledge/biomechanics.ts` — joint angle standards (pull-up, push-up, squat, planche, muscle-up) with `optimal_min/max/caution/error` thresholds, clinical notes, and citations; 9 skill progression mechanics; periodisation volume landmarks by experience level; muscle activation reference; helper functions (`getJointStandard`, `getAngleStatus`, `getProgressionPath`)

### Brand + design system
- Name: **Vector**
- Positioning: "Qoves of calisthenics" — clinical, citation-backed, measurement-obsessed
- Light editorial theme (warm cream background, near-black text, sharp 2px radius)
- Typography: Instrument Serif (display) + Geist Sans (body) + Geist Mono (data)
- Color palette: deep status colors (emerald-700, amber-700, red-700) for measurement indicators
- `color-scheme: light` + `data-darkreader-ignore` on SVGs for Dark Reader compatibility
- All copy rewritten in clinical voice: "Athlete identification," "Run initial assessment," "Contraindications," etc.

### Memory (persisted in `~/.claude/projects/.../memory/`)
- User profile (learner-builder, RTX 5060, content creator)
- Vector project context (calisthenics, AI coach + CV layered, business model)
- Business model (pricing, conversion math, distribution plan)
- Stack decisions and rationale
- Next.js 16 caveats (proxy.ts rename, async cookies, Turbopack default)
- shadcn 4.8 Base UI quirks

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

### 🟡 Unsolved / open items

| # | Item | Status / next action |
|---|---|---|
| 1 | End-to-end auth flow not yet verified working in browser | User is finishing Supabase URL config + email template setup. **Verification pending.** Watch for: (a) email arrives, (b) clicking link lands on `/onboarding`, (c) profiles row gets created in Supabase. |
| 2 | No Anthropic API key yet | Week 2 will use **mocked Claude responses** during UI scaffolding. User will add key (`ANTHROPIC_API_KEY` in `.env.local`) before final integration. |
| 3 | Not deployed to Vercel | Deferred to Week 8 or sooner if user wants a shareable demo URL |
| 4 | Python + CUDA + PyTorch env for ML training not yet set up | Needed by Week 5. Has Python 3.10+; needs CUDA 12.x toolkit, PyTorch with CUDA wheels, `mediapipe`, `onnx`, `onnxruntime`. |
| 5 | No real session/workout data tables yet | Will be added in Week 2 (workouts) and Week 3 (logging) — schema migrations `002_workouts.sql` and `003_logs.sql` |
| 6 | "Defying Gravity" → Confirmed user means *Overcoming Gravity* by Steven Low | Knowledge base file `overcoming_gravity.ts` to be added in Week 2 alongside Claude integration — will encode Low's 1–15 difficulty rating, push/pull/core 3-day structure, intra-week intensity oscillation, prerequisite gating, 8–12 week connective tissue adaptation windows |

---

## 5. Next steps — Week 2 plan

### Week 2 deliverable
**Goal:** A user can sign in, complete onboarding, and see a Vector-generated workout on screen — even if the "AI" is mocked behind the scenes.

### Tasks in order

1. **Add Overcoming Gravity framework to knowledge base**
   - New file: `web/src/lib/knowledge/overcoming_gravity.ts`
   - Encode: difficulty ratings, push/pull/core structure, volume guidelines per intensity, connective-tissue windows, prerequisite gating between progressions, hard/easy intra-week oscillation

2. **Workout schema migration**
   - New file: `web/supabase/migrations/002_workouts.sql`
   - Tables: `workouts` (id, user_id, generated_at, target_focus, status, ai_rationale), `workout_exercises` (id, workout_id, exercise_slug, target_sets, target_reps, intent, biomechanical_note, order_index)
   - RLS policies (users see only own workouts)

3. **Anthropic SDK setup with mock fallback**
   - File: `web/src/lib/anthropic.ts`
   - `generateWorkout(profile)` function — returns real Claude response if `ANTHROPIC_API_KEY` set, otherwise returns a curated mock workout (1× push, 1× pull, 1× core, 1× skill — calibrated to user's experience level)
   - System prompt references biomechanics + overcoming_gravity knowledge bases

4. **`/workouts/new` route**
   - Server action: read profile, call `generateWorkout()`, save workout + exercises to DB, redirect to `/workouts/[id]`
   - Display: clinical exercise cards with target volume, intent, biomechanical rationale per exercise

5. **Dashboard integration**
   - Replace the "Up next · Week 2" placeholder card with a "Generate today's session" CTA
   - Show recent workouts list once any exist

### Acceptance criteria (Week 2 done when…)

- [ ] User can click "Generate session" from dashboard
- [ ] System produces a structurally-valid calisthenics workout matching the user's experience level + equipment
- [ ] Workout is persisted to Supabase
- [ ] Workout display shows: exercise name, set × rep target, intent ("hypertrophy / strength / skill"), biomechanical note ("scapular depression cue critical for lat engagement"), and progression context ("week 3 of 8 in current progression")
- [ ] Even with no Anthropic key, the mocked workout looks indistinguishable from a real one

---

## 6. Tech reference (for AI assistants resuming this project)

### Stack
- Next.js **16.2.6** (App Router) + TypeScript 5
- Tailwind 4 + shadcn **4.8** (Base UI, NOT Radix — except `@radix-ui/react-slot` for form)
- Supabase (free tier, project name: "Vector", project ref: `dshalwuzxoprtqxfdskv`)
- React Hook Form + zod for forms
- Sonner for toasts
- Instrument Serif (display) + Geist Sans (body) + Geist Mono (data)

### Critical Next.js 16 gotchas
- `middleware.ts` deprecated → use `proxy.ts` with exported `proxy` function
- `cookies()` is async → must `await cookies()`
- Turbopack is default bundler (memory-hungry; use `--max-old-space-size=4096` if it crashes)
- Server components handle auth checks (see `page.tsx` pattern)

### Critical shadcn 4.8 gotcha
- Components import from `@base-ui/react/*` not `@radix-ui/react-*`
- Form component (`form.tsx`) was hand-written because shadcn registry doesn't deliver it cleanly; uses `@radix-ui/react-slot` as the one Radix dependency

### Run commands (Windows PowerShell)
```powershell
cd "C:\Users\Parth Dalal\FitnessApp\web"
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
- Memory files: `~/.claude/projects/C--Users-Parth-Dalal-FitnessApp/memory/`

### Style/voice rules
- **Vector copy is clinical, never motivational.** "Run initial assessment" not "Build your coach". "Contraindications" not "Anything to avoid". "Athlete identification" not "About you".
- **Numbers always tabular-nums + monospace.**
- **Status colors:** emerald-700 = nominal, amber-700 = caution, red-700 = error. Same semantics throughout.
- **Citations matter** — wherever a claim is made, cite the source (NSCA, JSCR, Low, FIG).

---

## 7. Resume instructions for next session

If you're picking this up cold:

1. Read this file end-to-end
2. Check `~/.claude/projects/C--Users-Parth-Dalal-FitnessApp/memory/MEMORY.md` and the linked files for additional context
3. Confirm with user: did the auth flow work end-to-end? (If yes → Week 2. If no → debug first.)
4. If Week 2: start with task 1 (add `overcoming_gravity.ts` knowledge file)

---

*This document is maintained manually. Update at the end of every significant work session.*
