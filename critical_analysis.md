# rvectr — Critical Analysis

**Written:** 2026-07-26
**Revised:** 2026-07-26 (second remediation pass — findings 20–24 added from an independent
re-audit; 4, 6, 14, 15 reopened and then closed; 2 reclassified as a regression)
**Scope:** Full repository audit against the goals in [`docs/RESEARCH_ROADMAP.md`](docs/RESEARCH_ROADMAP.md)
**Posture:** Adversarial. This document lists what is wrong, not what works. Every item cites a file or a command output that was actually checked.

---

## How to read this

Items are ordered by severity, not by area. **Tier 1** items can end the project or the submission — a data-loss event, a research-integrity finding, a license violation. **Tier 2** items are why the current project would not score well at an ISEF-aligned fair. **Tier 3** and **Tier 4** are engineering debt and positioning problems that cost points but do not sink anything.

Twenty-five findings. Five were Tier 1 at first writing; the re-audit added two more.

Each carries a status: **FIXED**, **PARTIAL**, or **OPEN**.

---

# TIER 1 — Critical

## 0. The EasyMocap pipeline does not perform motion capture — PARTIAL

**Found during remediation, not in the original audit.** This is the most serious finding in the document.

`backend/run_easymocap_videos2.py` runs in three steps. Step 1 calibrates cameras from chessboard images — real. Step 2 runs MediaPipe across both views and writes per-frame 2D keypoints — real. Step 3 was named `fit_easymocap_3d_smpl()`, its docstring read *"Runs EasyMocap multi-view 3D triangulation and SMPL/SMPL-X body fitting"*, and it printed the same claim to the console.

It does none of that. The dataset is loaded and used **only** for `len(dataset)`. The step-2 keypoints are never read. No triangulation runs, no fitting runs. The pose vector is filled in by hand:

```python
progress = np.sin(np.pi * t)
raw_poses[f, 12] = 1.45 * progress   # Left Knee
raw_poses[f, 15] = 1.45 * progress   # Right Knee
```

Every downstream artifact inherits this: `videos2/obj_sequence/`, `squat_multiview_animated.glb`, `squat_3d_mesh.glb`, `squat_vertices_anim.npy`. These are the assets `WORKSPACE_SUMMARY.md` described as multi-view capture results. **They are an authored animation with no relationship to the recorded video beyond its frame count.**

This is worse than finding 1. Fabricated numbers in a document are a documentation problem; a function that announces triangulation while hardcoding its output means the pipeline's headline capability does not exist, and any demo built on those meshes misrepresents what the system does.

**Done:** function renamed to `synthesize_scripted_squat_smpl()`, docstring and console output now state plainly that no capture occurs, module docstring rewritten, warning added to `backend/README.md`.

**Still open — you must decide:** either implement real triangulation in step 3 against the step-2 keypoints, or convert the script into the ground-truth generator it is already 80% of the way toward being (authored θ → render → recover → compare). The authored-pose synthesis is genuinely valuable for the latter. Pick one; do not leave it ambiguous.

**Also open:** verify the provenance of every existing result file. `squat_kinematics.json` reads OBJs from `squat_demo_out/` (the 4D-Humans output path) so it is probably genuine, but this script writes OBJs too. Assume nothing until each file is traced.

## 1. Four accuracy claims have no code behind them — FIXED

`docs/writeups/cbse_science_exhibition_final_writeup.md` states, as experimental results:

| Claim | Line |
|---|---|
| Squat knee flexion: **0.8° MAE (99.1% accuracy)** | 114 |
| Squat hip depth: **1.5° MAE (98.1% accuracy)** | 115 |
| Push-up elbow lockout: **1.6° MAE (99.1% accuracy)** | 116 |
| Planche extension: **2.4° MAE (94.6% accuracy)** | 117 |

The abstract (line 22) and the conclusion (line 147) both repeat `MAE < 2.4°`, and section 5.1 is titled "Joint Angle Accuracy (Goniometer Validation)."

**A recursive grep for `goniomet|ground.?truth|MAE|mean_absolute` across every Python file outside the two submodules returns nothing.** There is no validation script, no goniometer protocol, no reference dataset, and no file recording paired measurements. The numbers cannot be reproduced because nothing produced them.

**Why this is Tier 1 rather than a documentation bug:** at a regional exhibition, unbacked numbers cost points. At IRIS or ISEF, "walk me through how you obtained the goniometer reference" with no answer stops being a scoring deduction and starts being a research-integrity question. Affiliated fairs treat misrepresented data far more seriously than absent data. **A stated 2.4° MAE you cannot reproduce is strictly worse for you than "I have not measured this yet."**

**Fix:** delete all four numbers and the accuracy percentages before this writeup is reused in any submission. Restate `H₁` as an open hypothesis. Reintroduce numbers only when a script regenerates them from committed data.

## 2. 4,467 uncommitted files in EasyMocap, with nowhere to push them — PARTIAL

```
4D-Humans:    1 changed
EasyMocap: 4467 changed
```

`.gitmodules` points both submodules at their **upstream** remotes (`zju3dv/EasyMocap`, `shubham-goel/4D-Humans`). You have no write access to either. This work — `export_glb.py`, `create_dummy.py`, the modified `init_cnn.py`, the squat configs, the entire `test_data/annots/` tree — exists on exactly one disk, is backed up nowhere, and **cannot be pushed by any command in the parent repository**. The `docs` commit pushed earlier today did not include a byte of it.

This is your roadmap's Day 1 item ("rescue the submodules"). It is listed second here only because the integrity finding above is harder to undo.

**Fix:** fork both repositories to your own account, add your forks as a second remote inside each submodule, commit and push there, then update `.gitmodules`. Until that happens, a disk failure ends the project.

## 3. License contradiction — MIT claimed over a non-commercial dependency → FIXED

`README.md:105` states: *"This project is licensed under the MIT License."*

There is **no `LICENSE` file at the repository root** (`ls LICENSE*` → no such file). And `backend/EasyMocap/LICENSE` reads:

> Permission to use, copy, modify and distribute this software and its documentation for **educational, research and non-profit purposes only**. Any modification based on this work must be **open-source and prohibited for commercial use**.

You are distributing an EasyMocap-dependent pipeline under an MIT claim, while the pipeline's own runner (`backend/run_easymocap_videos2.py`) and every downstream artifact derive from a source that forbids commercial use and imposes an open-source condition on modifications. The README's attribution section names the restriction correctly at line 109, which makes the MIT claim at line 105 self-contradicting rather than merely uninformed.

**Fix:** relicense the repository research/non-commercial to match the most restrictive dependency, add an actual `LICENSE` file, and state the EasyMocap constraint prominently rather than in a footnote. Your roadmap already calls for "relicense research-only" — do it before the repo goes public for judging.

## 4. The demo presents fabricated analysis as real pipeline output — FIXED

Two separate places generate fake results that are labeled as genuine:

**`src/app/api/v1/analyze/route.ts`** — the entire endpoint is a mock. It ignores the uploaded video beyond reading its file size, invents a `video_id`, and returns hardcoded joint angles, a `posture_report` of `94.2 / "Excellent"`, and 180 frames of synthetic data generated by `90 + Math.sin(i / 10) * 30`.

**`src/lib/store.ts:86`** — the app boots with `mockDefaultAnalysis` as `currentAnalysis`, so `/analysis` renders fabricated data on first load with no upload at all. It is labeled `analysis_type: "EasyMocap 3D Triangulation & SMPL Mesh Fitting"`, carries a `94.8 / "Excellent"` grade, and describes the result as *"Parallel squat depth achieved with optimal lumbar neutrality, zero knee valgus collapse, and butter-smooth temporal acceleration curves."*

A judge who opens the deployed site sees confident clinical numbers attributed by name to a real motion-capture pipeline that never ran. That is the same integrity problem as finding 1, but interactive and harder to explain away in the moment. The landing page's rep-by-rep telemetry table (`src/app/page.tsx:355–362`) is illustrative markup rather than measured data, and carries no label saying so.

**Fix:** the roadmap already cuts the web app. Until it is removed, no mock result may be labeled with a real backend's name, and any illustrative figure needs a visible "sample data" marker.

---

# TIER 2 — Research validity

## 5. The actual research contribution does not exist yet — OPEN

The synthetic ground-truth harness — author a known θ, render it, recover it through a backend, compare to the θ you authored — is the entire novelty claim and the only source of defensible numbers. None of it is built. There is no `smplx` usage, no offscreen renderer, no time-warp generator, no virtual camera rig, no backend adapter emitting a common `JointAngleSeries`, and no error computation.

Everything currently in `backend/` is *capture and export* tooling. Nothing *measures*. This is the single gate between "impressive demo" and "study with results," and it is at zero.

## 6. Test suite is real but tests almost nothing that matters — FIXED

`python3 -m pytest tests/ -q` → **12 passed, 1 skipped**. The suite runs clean, which is genuinely more than most projects have.

But `tests/test_angles.py` verifies `calculate_angle` against hand-built triangles — that a right angle returns 90°, an equilateral returns 60°. That is pure geometry, and it would pass identically if the pose pipeline feeding it were completely wrong. Total suite: 161 lines.

Untested entirely: `pipeline/gait_events.py`, `pipeline/pelvic_analysis.py`, `pipeline/stride_metrics.py`, `pipeline/running_kinematics.py`, `pipeline/smartphone_sync.py`, and every mesh script. There is no golden-file regression, so nothing detects an accuracy regression when a filter or a rotation convention changes.

## 7. Smoothing biases the exact quantity being measured — FIXED

> [!NOTE]
> **Correction to this finding as originally written.** It claimed `backend/zero_drift_perfect_smpl_builder.py` applied Gaussian filtering, citing `docs/WORKSPACE_SUMMARY.md:58`. That was wrong — that script already used `savgol_filter`. The **documentation** was inaccurate, not the code, and this audit repeated the error by trusting the project's own docs instead of reading the source. The finding stands, but in two different files.

The real Gaussian usages were:

- `backend/run_easymocap_videos2.py:210` — `gaussian_filter1d(raw_poses, sigma=3.5)` applied directly to the 72 joint pose parameters. The heaviest and most consequential instance.
- `backend/recalibrate_and_reconstruct_3d.py:128` — a hand-rolled Gaussian kernel over joint trajectories.

Your roadmap specifies Savitzky–Golay *"not Gaussian — Gaussian flattens the peak angles being measured, which matters enormously at running velocities."* That reasoning is correct. A Gaussian filter attenuates local extrema — peak knee flexion, peak hip angle — which are exactly the values a velocity-error study reports. Attenuation worsens as movement speeds up, so **the smoothing would manufacture a velocity-dependent error trend even from a perfect estimator**, in the direction of your hypothesis. That is what made it the most dangerous methodological bug in the repo.

**A second bug found in the same function:** `recalibrate_and_reconstruct_3d.py` used `np.convolve(..., mode='same')` under a comment claiming "reflect padding." `mode='same'` zero-pads, dragging the first and last `kernel_size//2` frames toward the origin — corrupting exactly the frames at the start and end of every captured movement.

**Fixed:** both replaced with `savgol_filter` (window 15, polyorder 3), which handles boundaries correctly and preserves peak amplitude at comparable noise rejection.

**Still open:** the pose parameters are axis-angle rotations, and filtering axis-angle components independently is not rotation-correct — it ignores the manifold and misbehaves near π. A `TODO` marks this in the source. The roadmap's choice of `roma` for all rotation handling is the right fix, and it should happen before any error number is computed.

## 8. No engineering log, and the portfolio depends on 27 months of one — FIXED

`docs/log/` does not exist. Roadmap item, week 1, not started.

Portfolio item #9 is "engineering log spread — dated, messy, authentic," and your own failure list names retroactive log-writing as a way this fails, correctly: reviewers can tell. Every day without an entry is a day that cannot be reconstructed honestly later.

## 9. No pre-registration — PARTIAL

OSF pre-registration is a roadmap item ("costs an evening; almost no pre-college researcher does it"). Not done. Its value is entirely front-loaded — a pre-registration filed *after* you have seen the data is worth nothing and looks worse than none. The window closes the moment the harness produces its first number.

## 10. Two of the three stated hypotheses are not testable as written — FIXED

From `docs/writeups/cbse_science_exhibition_final_writeup.md:49–51`:

- **H₂** claims multi-camera triangulation will *"eliminate self-occlusion errors."* "Eliminate" is unfalsifiable in practice and certainly false — triangulation *reduces* occlusion error, and by an amount nobody has measured here. Restate as a bounded, quantified reduction.
- **H₃** claims SMPL rotations enable humanoid teleoperation and exoskeleton control. There is no ROS2 code, no inverse-kinematics implementation, no robot, and no simulation anywhere in the repository. This is an assertion about what would be possible, presented in the position where a tested hypothesis belongs.

A judge will find H₃ in under a minute and it will cost more than it gains, because it invites the question of what else is claimed but not built.

## 11. Scope inflation across three domains — FIXED

The writeup positions rvectr across athletics, clinical rehabilitation, **and** robotic teleoperation (abstract, and the `F1/F2/F3` branches of the architecture diagram). Each additional domain multiplies the surface a judge can probe while adding nothing to the measurement. Rehabilitation implies clinical validation you do not have; robotics implies an implementation that does not exist.

The research roadmap correctly narrows to one question. The writeups have not caught up.

---

# TIER 3 — Reproducibility & engineering

## 12. Hardcoded absolute paths make the pipeline unrunnable elsewhere — FIXED

Eleven scripts contain machine-specific absolute paths. Representative:

| File | Path |
|---|---|
| `process_video_3d.py:259` | `/home/pd/Downloads/20260723_121036.mp4` |
| `fix_jitter.py:7` | `/home/pd/Documents/rvector/backend/squat_demo_out` |
| `smooth_and_center_mesh.py:64` | `/home/pd/Downloads/20260723_121036_3d_mesh/obj_sequence` |
| `make_video.py:52` | `/home/pd/Documents/rvector/backend/squat_demo_out` |
| `import_objs_blender.py:55` | `/home/pd/.gemini/antigravity-cli/brain/0ee7170b-…/animated_squat.blend` |
| `make_video.py:53` | `/home/pd/.gemini/antigravity-cli/brain/0ee7170b-…/final_squat_overlay_blackbox.mp4` |

Nothing runs on another machine without editing source. Reproducibility is a graded criterion, and "clone and run" failing at line 7 is the first thing a technically curious judge would hit.

The last two entries write project output into **another AI tool's scratch directory**. Beyond being unreproducible, an uncleaned generated-tooling artifact sitting in your source is exactly the kind of detail that raises the "how much of this did you write?" question you least want asked. Clean these regardless of the reproducibility argument.

## 13. No dependency specification for the backend — FIXED

There is no `requirements.txt`, no lockfile, no environment file, and no Docker image at `backend/`. The only setup path is `setup_env.sh`, which covers EasyMocap alone and pins **Python 3.11**, while your roadmap records that 4D-Humans constrains you to **Python 3.10**. The two-environment split is real, undocumented, and unautomated.

Nobody — including you in three months, and including a judge who wants to verify a result — can rebuild this environment.

## 14. Mesh-processing script sprawl with no entry point — FIXED

Seven overlapping scripts, ~1,018 lines, all transforming SMPL output with unclear precedence:

```
fix_jitter.py                          37
smooth_and_center_mesh.py              66
make_perfect_squat_anim.py            151
lock_stationary_smpl.py               162
fix_smpl_orientation_and_centering.py 169
enhance_muscular_anchored_smpl.py     215
zero_drift_perfect_smpl_builder.py    218
```

Nothing documents which to run, in what order, or which superseded which. `backend/` holds 30+ loose top-level scripts with no `main` or CLI.

The naming is its own finding. `perfect`, `enhance_muscular`, `zero_drift` describe **desired appearance**, not operations — the vocabulary of making output look right rather than measuring how wrong it is. `enhance_muscular_anchored_smpl.py` adjusts body shape for visual appeal, which in a measurement study is a confound: shape parameters affect joint centers, and therefore angles.

**Done (second pass):** the two fully superseded scripts (`fix_jitter.py`,
`lock_stationary_smpl.py`) deleted; four renamed to describe what they do rather
than how the output should look —

| Was | Now |
|---|---|
| `make_perfect_squat_anim.py` | `synthesize_scripted_squat_anim.py` |
| `zero_drift_perfect_smpl_builder.py` | `build_root_anchored_smpl.py` |
| `rebuild_accurate_3d_skeleton.py` | `rebuild_3d_skeleton.py` |
| `enhance_muscular_anchored_smpl.py` | `restyle_body_shape_for_render.py` |
| `copy_perfect_blend_to_videos2.py` | `copy_blend_to_videos2.py` |

— and the duplicated helpers consolidated into `backend/meshio.py` (see finding
25), which replaced the appearance-asserting file headers with provenance.

## 15. No CI — FIXED

No `.github/workflows/`. Nothing runs the 12 passing tests automatically, so nothing prevents a regression between now and October, and the roadmap's "CI fails on MAE regression" has no foundation. Portfolio item #8 specifies a CI badge.

## 16. The retired SaaS is still fully shipped — FIXED

Fourteen page routes remain, including `dashboard/`, `dashboard/social/`, `dashboard/profile/`, `roster/`, `onboarding/`, `signin/`, and three `workouts/[id]/` routes. Also present: eight Supabase migrations (`001_init` … `008_fix_workout_exercises_rls_update`), `src/lib/anthropic.ts` with AWS Bedrock integration, and the mock `api/v1/analyze`.

The roadmap's week-1 instruction is to strip all of it. Keeping it costs three ways: it is dead weight you maintain, it contradicts a research framing when a judge browses the repo, and — per finding 4 — the parts that still run produce fabricated output.

## 17. Configuration silently falls back to placeholders — FIXED

`src/lib/supabase/client.ts:4–5` and `server.ts:7–8` default to `"https://local-placeholder.supabase.co"` and `"local-placeholder-key"` when env vars are missing. A misconfigured deploy therefore fails at request time with a confusing auth error rather than at boot with a clear one. `src/lib/anthropic.ts` reads AWS credentials directly from env with non-null assertions (`process.env.AWS_ACCESS_KEY_ID!`), which will throw at an unhelpful point if unset.

Low impact given the app is slated for removal, but if any of it survives, fail fast at startup instead.

---

# TIER 4 — Positioning

## 18. "Clinical" is used throughout with nothing clinical behind it — FIXED

`README.md`, `docs/WORKSPACE_SUMMARY.md`, the writeups, and `src/app/page.tsx:70,77,229` all use "clinical," "clinical-grade," or "clinical diagnostic evaluation." There is no clinical validation, no IRB, no comparison against a gold-standard system, no licensed practitioner involved, and no patient population.

Judges attack this specific word, because it is a regulated-sounding claim with a well-defined evidentiary bar. "Clinical-grade" invites "compared against which reference system, with what agreement statistics?" You currently have no answer. Say "consumer-hardware markerless" and claim only what you measured.

## 19. Category framing is unresolved — OPEN

The writeup targets "Emerging Technologies (AI, Computer Vision & Robotics)" and spans athletics, rehab, and robotics. The research roadmap describes a **benchmark and measurement methodology**, which is Systems Software.

This matters more than it sounds: framing the work as a coaching or rehab application invites "where is the clinical validation?", while framing it as a reproducible benchmark for a class of algorithms puts you on ground you can fully defend. Decide before drafting the synopsis, because the framing shapes every section.

---

# What is actually right

Kept short deliberately, but it is real and worth not discarding:

- Three independent capture backends genuinely integrated and running locally (4D-Humans/HMR2, EasyMocap multi-view, MediaPipe) — that is substantial systems work, and most people underestimate how much.
- `extract_kinematics.py` produces real per-frame joint data: 161 frames of squat, 90 of running, with sensible bilateral values.
- Non-trivial problems were found and solved: root drift, mesh orientation, temporal jitter. These are the raw material for portfolio items 3 and 4, and they are worth more as documented debugging narratives than the code is as code.
- A test suite exists and passes cleanly. Trivial in coverage, correct in habit.
- The pivot in `docs/RESEARCH_ROADMAP.md` diagnoses most of the above independently. The plan is right. Nothing in it has been executed yet.


---

# Findings added by the independent re-audit (2026-07-26, second pass)

These were missed by the first audit, or introduced by the first remediation pass.

## 20. The repository cannot be cloned as documented — OPEN (needs your GitHub auth)

A **regression** created by the fix for finding 2. Committing the submodule work
locally, without pushing it anywhere, converted "work that is backed up nowhere"
into "work that is backed up nowhere *and* a parent repo recording gitlinks that
resolve nowhere."

```
backend/EasyMocap  00d4b82  ->  0 matches on zju3dv/EasyMocap
backend/4D-Humans  ec0e8c9  ->  0 matches on shubham-goel/4D-Humans
```

`git branch -r --contains HEAD` is empty in both. `git clone --recursive` — step 1
of the README quickstart — therefore fails for everyone, including you on a second
machine.

**Done:** `scripts/rescue-submodules.sh` performs the whole fix and `--check`
verifies it; a `submodule-pointers` CI job fails the build while the condition
persists; the README quickstart warns and drops `--recursive`.

**Still open — needs your credentials:** fork both repos, then run
`./scripts/rescue-submodules.sh --fork-owner <you>`.

## 21. `/demo` still attributed the fabricated animation to EasyMocap — FIXED

Finding 4 was marked FIXED; `src/lib/store.ts` was fixed and the demo page was
not. `src/app/demo/page.tsx` labelled the viewport `EasyMocap Output:
public/squat_3d_mesh.glb` — a file `backend/README.md` names explicitly as
hand-authored — listed "EasyMocap SMPL/SMPL-X Parametric Fitting" as a working
stage, described a "1D Gaussian temporal low-pass filter (sigma = 3.5)" when the
code uses Savitzky–Golay, and claimed to eliminate "100% of monocular 3D depth
noise". The banner and page header claimed "sub-centimeter accurate" and
"industrial-grade".

Also found: `src/app/layout.tsx` set the site's **search-result and link-preview
description** to "Industrial-grade markerless 3D computer vision… for
professional athletes" — the most-read sentence in the project, describing a
product that does not exist.

**Done:** provenance banner added to `/demo`; every pipeline stage tagged BUILT or
NOT BUILT; the filter described correctly along with its bias on peak angular
velocity; "innovations" restated as goals; site metadata rewritten. Three CI
greps now fail the build if an accuracy claim, an "industrial-grade"-class
adjective, or a synthetic asset credited to a real backend reappears in `src/`.

## 22. Gait event detection dropped events, and got worse at higher frame rates — FIXED

`pipeline/gait_events.py:_detect_crossings` tested `signal[i-1]` against one edge
of the hysteresis band and `signal[i]` against the other in a single comparison,
requiring the signal to clear the entire band between two adjacent samples. Any
sample landing inside the band silently dropped the event. Because a higher frame
rate means a smaller per-frame step, **a better camera lost more events**:

| | 30 fps | 60 fps | 120 fps | 240 fps |
|---|---|---|---|---|
| mid-range threshold | 16/16 | 16/16 | 8/16 | 8/16 |
| threshold near ground contact | 16/16 | 12/16 | 4/16 | 4/16 |

`stride_metrics` (GCT, cadence, flight time) and `pelvic_analysis` all consume
these events. Replaced with a two-state Schmitt trigger that takes event timing
from the nominal threshold crossing, so widening the band rejects noise without
shifting event times. Now 16/16 in every cell above.

## 23. The test suite was structurally unable to catch finding 22 — FIXED

`tests/test_gait_events.py` built its fixtures as a **square wave** — values
exactly 0.0 and 1.0, instantaneous transitions — which clears any hysteresis band
by construction. The file's own docstring said "A test that merely asserts
'returns a list' would pass against a broken detector." So did this one.

Added smooth-sinusoid fixtures swept across four frame rates and two threshold
placements, a slow-traversal case, and a jitter case. Verified these fail 6 ways
against the old implementation and pass against the new one — the check that
distinguishes a regression test from a test.

## 24. The CI could never have gone green, and was never run — FIXED

Three compounding problems:

1. `.github/workflows/ci.yml` was listed in `.gitignore`, so the workflow was on
   disk but not in git. The commit titled "ci: add workflow config" added
   `docs/ci-workflow.yml`, a copy GitHub will never execute. **The
   fabricated-results guard had never run once.**
2. The `backend-tests` job would have **errored on its first run**:
   `test_load_j_regressor` loads `SMPL_NEUTRAL.pkl` from inside the EasyMocap
   submodule, which is gitignored *and* which the job deliberately does not
   fetch. The fixture raised rather than skipped.
3. The job ran `tsc` and `build` but never `npm run lint`, which was reporting
   7 errors and 9 warnings.

Also: bare `pytest` from `backend/` crashed with `INTERNALERROR` — no `testpaths`
config, so collection recursed into `EasyMocap/3rdparty/pybind11/tests/conftest.py`,
which calls `sys.exit(1)`.

**Done:** workflow un-ignored and tracked, redundant copy deleted; SMPL path moved
behind `rvectr_paths.have_smpl_model()` so it skips with an actionable message;
`get_joints` given synthetic-input contract tests that run everywhere, so its
coverage no longer depends on a licensed file; `pytest.ini` pins `testpaths`;
lint added to CI and driven to zero.

## 25. Assorted hygiene found during the re-audit — FIXED

* **`ThreeMeshCanvas` hardcoded the filename** `squat_multiview_animated.glb` in
  its footer regardless of the `glbUrl` prop, so `/demo` named a file it was not
  rendering. It also carried "Sub-centimeter SMPL Surface Mesh" and an
  "EASYMOCAP … VIEWPORT" header on every page that used it.
* **OBJ loads had no cancellation.** Scrubbing the timeline fires one request per
  frame; a slow earlier load could resolve last and leave the viewport on a frame
  already scrubbed past. Added a `cancelled` guard, which also resolved the
  `setState`-in-effect lint error.
* **7 unused runtime dependencies** — `@anthropic-ai/sdk`,
  `@aws-sdk/client-bedrock-runtime`, both Supabase packages, `@hookform/resolvers`,
  `zod`, `@vercel/analytics` — plus an unused `ui/form.tsx` dragging in
  `react-hook-form`. 28 dependencies → 17. `@types/three` moved to devDependencies;
  package renamed from `web` to `rvectr`.
* **`haarcascade_frontalface_default.xml` was tracked despite an explicit
  `.gitignore` rule naming it**, which made the rule silently inert. It is the
  largest tracked file in the repo. Resolved in favour of tracking: OpenCV 5 no
  longer ships the Haar cascades in the wheel (`cv2.data.haarcascades` exists but
  is empty), so vendoring it is what makes `make_video.py` work on a fresh clone.
  `rvectr_paths` still prefers a packaged copy when one exists.
* **`load_smpl_faces` was copy-pasted byte-identically into 7 scripts**, and the
  OBJ writer into 7 more under two names, differing only in a header comment
  asserting qualities of the output ("Perfect Anchored", "Muscular"). Consolidated
  into `backend/meshio.py`, whose header records **provenance** instead:
  `RECOVERED`, `SYNTHETIC`, or `INHERITED`. `measured` is a required argument with
  no default — deciding whether an artefact is a measurement should not happen by
  accident.
* **Two Blender scripts were named `test_*.py`** and would be collected by pytest.
  Renamed to `check_*`.
* **`~400 MB of mesh assets in `public/` are gitignored**, so a fresh clone
  rendered an empty viewport with only a console error. Documented in
  `docs/ASSETS.md`; the viewer now shows a panel naming the missing file.

---

# Remediation status

## Done (2026-07-26)

| # | Finding | What changed |
|---|---|---|
| 1 | Unbacked MAE claims | Removed from all three writeups; replaced with explicit "not yet measured"; CI check fails if they reappear |
| 3 | License contradiction | Root `LICENSE` added (research/non-commercial); README corrected; medical-device disclaimer added |
| 4 | Fabricated demo output | Mock `/api/v1/analyze` deleted; store placeholder relabelled and de-graded; visible sample-data banners; **silent mock fallback on upload removed** — it now fails loudly |
| 6 | Trivial tests | 12 → 31 → **44 tests**. See finding 23: the 31 included fixtures that could not fail |
| 7 | Gaussian smoothing | Savitzky–Golay in both real locations; zero-padding bug fixed |
| 8 | No engineering log | `docs/log/` opened with today's entry |
| 10, 11 | Untestable hypotheses, scope inflation | Robotics claim removed from hypotheses; H₂ made falsifiable; velocity hypothesis stated |
| 12 | Hardcoded paths | All eliminated via `backend/rvectr_paths.py` with env overrides |
| 13 | No dependency spec | `requirements-core.txt`, `requirements-hmr2.txt`, three-environment split documented |
| 15 | No CI | `.github/workflows/ci.yml` written. It was gitignored and would have errored on first run — see finding 24. Now tracked, green, and extended with lint, three claim guards and a submodule-pointer job |
| 16 | SaaS still shipped | 42 files removed; 14 routes → 5; build passes clean |
| 17 | Silent config fallbacks | Removed with the Supabase layer |
| 18 | "Clinical" language | Removed from README and WORKSPACE_SUMMARY |

**A test written during this pass found a real bug:** `pipeline/stride_metrics.py:cadence()` divided step count by elapsed time between the first and last step onset. N onsets span N−1 intervals, so it overestimated cadence by N/(N−1) — 33% at four steps. Fixed, with a regression test.

## Partial

| # | Finding | Remaining |
|---|---|---|
| 0 | EasyMocap synthesises instead of capturing | Labelled honestly everywhere now, including the web UI (finding 21), and every mesh carries a provenance header. **You must still decide** whether to implement real triangulation or convert it into the ground-truth harness. Provenance of existing result files still unverified. |
| 2 / 20 | Submodule work unbacked-up, and now unclonable | Reclassified as a regression — see finding 20. Tooling and CI enforcement are in place; **forking and pushing needs your GitHub auth.** |
| 9 | No pre-registration | Full draft at `docs/osf_preregistration_draft.md`; needs an OSF account and submission |

## Open

| # | Finding | Note |
|---|---|---|
| 5 | **The harness does not exist** | The gate. Everything above is prerequisite hygiene; this is the project. |
| 19 | Category framing | Your call: Systems Software is the defensible framing |
| 20 | Submodules unfetchable | Needs your GitHub auth — one command once the forks exist |

## Next actions, in order

1. **Fork both submodules and push.** Still the highest priority, and now also the
   only thing making the repository unclonable:
   `./scripts/rescue-submodules.sh --fork-owner <you>`
2. **Push, and confirm CI goes green.** The `no-fabricated-results` and
   `submodule-pointers` jobs have never run on GitHub. Job 2 is expected to fail
   until action 1 is done — that is the job working.
3. **Decide what `run_easymocap_videos2.py` becomes.** Real triangulation, or the
   ground-truth generator. Not ambiguous.
4. **Trace the provenance of every result file** before citing any of it. Meshes
   regenerated from now on carry their own header; anything already on disk does not.
5. **Submit the OSF pre-registration** before the harness produces a number.
6. **Build the harness.**

## What a second audit should look at next

Untouched by either pass, and not yet known to be wrong:
`pipeline/pelvic_analysis.py` and `pipeline/running_kinematics.py` remain
untested, and `stride_metrics.flight_time` pairs consecutive cycles regardless of
side while its docstring assumes they alternate — correct on the clean synthetic
case that was checked, unverified on real overlapping strides.
