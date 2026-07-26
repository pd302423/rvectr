# rvectr — Research Roadmap

**Program:** Velocity-dependent error in markerless 3D human pose estimation
**Author:** Parth Dalal · solo researcher
**Written:** 2026-07-26 · **Revised:** 2026-07-26 (relocation constraint)
**Supersedes:** `ROADMAP.md` (SaaS launch plan, retired)

---

## The constraint that defines this document

**Relocation to Japan in 2027 makes IRIS a one-shot competition.**

IRIS requires enrollment at a school based in India. Students studying abroad are ineligible regardless of citizenship. There is no second attempt, no rehearsal year, no fallback cycle.

| Date | Event | Status |
|---|---|---|
| **Oct 15, 2026** | IRIS submission deadline | **The only shot.** 12 weeks out. |
| **Jan 2027** | IRIS National Fair, ~100 shortlisted exhibit | If selected |
| **May 2027** | Regeneron ISEF, if Grand Award | ⚠️ see open question |
| 2027 onward | Relocation to Japan | IRIS permanently closed |
| **Nov 1, 2028** | MIT Early Action | Unaffected — program continues |

### Two questions only IRIS can answer — ask this week

1. Confirm the exact Oct 15, 2026 deadline and the entry fee (sources conflict: ₹5,000 + taxes per project with EWS waiver, vs. free).
2. **If selected for Team India in January 2027, does relocating to Japan before May 2027 affect ISEF participation?** This determines whether ISEF is reachable at all. Nobody but IRIS can tell you.

### Second life: JSEC

[JSEC](https://isef.jp/about/perticipation/) is one of Japan's two ISEF-affiliated contests, run by Asahi Shimbun and TV Asahi. No regional preliminaries — direct application to the national contest. **Eligibility for a foreign student enrolled in Japan is undocumented; contact them directly once relocated.** If eligible, the 2027–28 running study finds a home there.

---

## Why 12 weeks is survivable

One design decision makes this feasible: **synthetic ground truth plus self-only filming requires no IRB, no recruitment, no scheduling, no consent forms.**

Filming yourself to test your own invention is generally exempt from IRB pre-approval. Authoring known SMPL poses and rendering them requires no human participants at all. Every logistical dependency that would have eaten the twelve weeks is removed by construction.

The multi-subject study, the ethics packet, the mentor recruitment — all of it moves past October. None of it is needed to submit.

---

## The research question

> How does markerless 3D human pose error scale with movement velocity, and at what joint angular velocity does consumer-hardware capture stop being clinically meaningful?

**The experimental trick:** take one motion sequence and time-warp it — 0.5×, 1×, 2×, 4× playback. Identical kinematics, different angular velocity. This isolates velocity as a clean independent variable, free of the confound you'd get by comparing squats to running as different *movements*. Then confirm the synthetic finding holds on real self-captured squat and treadmill running footage.

**Three backends under test:** EasyMocap (multi-view) · 4D-Humans/HMR2 (monocular) · MediaPipe Tasks (realtime).

**Novelty claim for the synopsis:** the first open, reproducible benchmark characterising consumer-hardware markerless pose error as a function of joint angular velocity, with a stated threshold beyond which the measurement is not clinically meaningful.

---

# PART 1 — The 12-week sprint

## W1–2 · Jul 27 – Aug 9 · Clear and commit

- **Day 1: rescue the submodules.** `backend/4D-Humans` and `backend/EasyMocap` hold uncommitted work that exists nowhere else.
- Delete the unbacked results in `cbse_science_exhibition_final_writeup.md`. No number ships without a script behind it.
- Strip the SaaS: `dashboard`, `onboarding`, `signin`, `workouts`, `roster`, `supabase/`, `anthropic.ts`, `knowledge/`, mock `api/v1/analyze`. Relicense research-only.
- Open `docs/log/` — dated entry every session, starting now.
- **Pre-register on OSF.** Hypotheses and analysis plan, timestamped, before any data. Costs an evening; almost no pre-college researcher does it.
- `smplx` loads; pose a mesh from known θ; render one frame offscreen (pyrender + EGL).

## W3–5 · Aug 10 – Aug 30 · The harness

- Virtual multi-camera rig, known intrinsics/extrinsics. **Sanity check:** triangulate your own renders and recover the pose you authored.
- Time-warp sequence generator — 0.5× / 1× / 2× / 4×.
- Motion blur synthesis: 8× temporal supersampling, averaged. Blur is the mechanism by which speed breaks these models; you must simulate it to study it.
- **Backend adapter interface** — all three pipelines emit one versioned `JointAngleSeries` schema. Architectural keystone.
- Golden-file regression tests.

**Gate (Aug 30):** one command yields per-joint MAE for one backend on one synthetic sequence, and corrupting the input makes the number go up. *If this slips past Sep 6, drop to the minimum-viable submission below.*

## W6–8 · Aug 31 – Sep 20 · Run the experiment

- Full sweep: velocity × off-axis angle × camera distance × occlusion × frame rate.
- Per-joint, per-frame error against authored θ.
- **Real capture, self only:** squat and treadmill running, both phones, 120/240 fps, ChArUco calibration, audio-clap sync. Treadmill belt speed gives exact ground-truth velocity.
- Cross-check: does the synthetic velocity-error curve hold on real footage?

## W9–10 · Sep 21 – Oct 4 · Analysis

- **The money figure:** error vs. joint angular velocity, three backends, bootstrap confidence bands, with the crossover threshold marked.
- Phase-normalised gait curve comparison (`spm1d`) if running data supports it.
- Every figure regenerable from committed CSV by script.

## W11–12 · Oct 5 – Oct 15 · Submit

IRIS requires three components:

1. **Synopsis** — Abstract (250 w) · Introduction & Objective (100–150) · **Innovation** (50–100) · Methodology (150–250) · **Results & Conclusions** (100–150) · Acknowledgement & References (50–100).
2. **Full research paper.**
3. **90-second video.**

Also: repo public, README honest about what is and isn't measured, `CITATION.cff`, Zenodo DOI if time permits.

**Submit by Oct 15. Do not touch code after Oct 11.**

---

## Minimum-viable submission

If the schedule slips, this still constitutes a legitimate entry — novelty claim intact, results real:

- Synthetic only, no real-capture cross-check
- Two velocities (1× and 4×) instead of four
- Two backends instead of three
- One figure, one table, honest error bars

**A thin honest submission beats a padded one.** Judges ask questions.

## Cut ruthlessly — all of this moves past October

Web viewer · 3DPW/EMDB benchmark calibration · multi-subject study · IRB packet · TRAM/WHAM fourth backend · Blender pipeline work · paper publication · upstream PRs · mentor recruitment.

None of it is needed to submit. All of it still serves Nov 2028.

---

# PART 2 — Post-October, through Nov 2028

**Relocation does not touch this.** The research program is geography-independent; only the fair pathway changed.

| Window | Work |
|---|---|
| Nov 2026 – Jan 2027 | IRIS fair prep if shortlisted. Benchmark calibration vs. 3DPW/EMDB. Paper draft. |
| Feb – May 2027 | ISEF if reachable. Otherwise: workshop paper submission, Zenodo dataset, upstream PRs. |
| Jun 2027 – Mar 2028 | Japan. Contact JSEC re: eligibility. Multi-subject running study **with local IRB approval first**. Extended benchmark. |
| Apr – Sep 2028 | v1.0.0, publication, real external users, leaderboard submissions. |
| Oct 2028 | Portfolio assembly — 27 months of log → 10 SlideRoom items. |

### The 10 portfolio items

1. The rig — two phones, checkerboard, your actual floor. Unstaged.
2. **Video, 60–90 s:** one stride through all three pipelines, error overlaid live.
3. Drift bug: before/after, with the root-translation diagnosis.
4. Orientation bug: sideways mesh + your rotation math on paper.
5. Harness diagram: known θ → render → recover → error.
6. **The money figure:** error vs. angular velocity.
7. Real-world validation: measurement photo + Bland–Altman plot.
8. Repo: README, CI badge, DOI badge, real issues and stars.
9. Engineering log spread — dated, messy, authentic.
10. What I deleted and why — the SaaS, one honest paragraph.

Every description answers: what broke, how you found it, what *you* did versus what the library did.

---

## Stack

**Core** — Python 3.10 (4D-Humans constraint) · `uv` · Docker on CUDA base · GitHub Actions

**Body model & synthesis** — `smplx` · `trimesh` · `pyrender` + EGL · `bpy` as pip module · motion blur via 8× temporal supersampling

**Backends** — 4D-Humans/HMR2 · EasyMocap · MediaPipe Tasks · *(TRAM or WHAM — post-October)*

**Numerics** — numpy · scipy · pandas · `roma` for every rotation conversion (hand-rolled axis-angle math is the likely source of the orientation bugs) · **Savitzky–Golay** filtering, not Gaussian — Gaussian flattens the peak angles being measured, which matters enormously at running velocities

**Gait** — Zeni kinematic event detection · `scipy.signal` stride segmentation · `spm1d` for curve statistics

**Capture** — 120/240 fps phone slow-mo · OpenCV ChArUco · audio/LED sync · treadmill for known ground-truth speed

**Experiments** — Hydra sweeps · Weights & Biases (public dashboards double as portfolio evidence)

**Validation** — authored-θ synthetic ground truth · *(3DPW, EMDB — post-October)* · Bland–Altman · bootstrap CIs

**Quality** — pytest + pytest-regressions · `ruff` · pre-commit · CI fails on MAE regression

**Web** — *(post-October)* Vite + TypeScript + Three.js, static on GitHub Pages. No Next.js, React, Supabase, or server.

**Publication** — Zenodo (DOI) · OSF (pre-registration) · Overleaf/LaTeX · `CITATION.cff`

---

## How this fails

- **Building the harness perfectly instead of finishing it.** Twelve weeks. Ship the ugly version.
- **Building the viewer.** It's the fun part and contributes least. It is cut.
- **A number without a script.** The reason `ROADMAP.md` was retired.
- **Retroactive log-writing.** Reviewers can tell. Write it the day it happens.
- **Discovering the deadline moved.** Confirm with IRIS this week.
