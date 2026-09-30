# rvectr — Implementation Roadmap

**Written:** 2026-09-29 · **Status:** plan only — nothing in this document is implemented yet
**Scope:** (1) the research question — *where does consumer-hardware motion capture stop being trustworthy, per exercise?*; (2) a local Studio — drag in a recorded video, get a 3D model and an analysis; (3) a capture setup simple enough for other people to use.
**Relationship to other docs:** builds on [`RESEARCH_ROADMAP.md`](RESEARCH_ROADMAP.md) (research question, relocation context, portfolio plan — all still valid). It replaces that document's "no web app, no server" stance, which a capture app for other people makes untenable. Every finding in §1 was checked against source code on 2026-09-29. Where this document contradicts [`critical_analysis.md`](../critical_analysis.md), this one is newer.

> [!NOTE]
> **Near-term venue: CBSE Science Exhibition 2026–27 (Emerging technologies).** Stage 1 (§7) is sized for the regional round. IRIS 2026–27 is skipped (decided 2026-09-29), and JSEC is the later route to ISEF. See §0.

## Summary

1. **Near-term venue: CBSE Science Exhibition 2026–27.** Stage 1 is sized for the regional round (last year it ran from late October to November). IRIS is skipped. JSEC is the later route to ISEF, pending eligibility. See §0.
2. **Recordings from other people can't measure accuracy.** Accuracy needs a reference. Crowd data can measure *reliability* and *robustness*, which also matter for trust, but they are different claims. See §3.5.
3. **Average phone-mocap accuracy is already published.** With a biomechanically constrained pipeline it is about 4.5–4.8° MAE. In a 2025 study, off-the-shelf monocular estimators gave 14–26° on knee angles. What remains open, and what you can own, is *under which conditions* a reading can be trusted, and how a user would know at runtime. See §3.1–3.3.
4. **Measurement defects come first.** Several defects in the current pipeline are larger than the 5° threshold the study tests against. Collecting data before fixing them wastes the data. See §1.2.
5. **The study and the demo share one code path.** The demo should display the study's error bars live, never an angle the study didn't evaluate. See §2.
6. **The demo is a local platform with two faces.** In the Studio, the person recorded drops one or more videos and gets a 3D body with trusted angles. The Lab shows you every processing stage. Multiple phones are combined without calibration first, and calibrated later. See §4.
7. **Clothing is part of the trust map.** On a multi-camera lab system during walking, clothing barely changed joint angles. Whether that holds for one phone during a deep squat is untested. See §3.7.
8. **The headline question:** how accurate can a normal person get with the phones they own, and what does each extra step (a second phone, a calibration board, fitted clothes, good light) buy? See §3.3.

---

## 0. Competitions: CBSE now, IRIS skipped, JSEC later

**Near-term venue: CBSE Science Exhibition 2026–27.** You'll enter under the Emerging technologies sub-theme, as a team of two with a mentor teacher, and the school registers the project. Last year the regional round ran 29 Oct – 29 Nov and the national round was in January. Stage 1 (§7) is sized to be ready by late October.

**Decision (2026-09-29): IRIS 2026–27 is skipped.** Search results from the official site list the window as closing 3 Oct 2026. The fee is ₹5,000 + tax (about ₹6,000) and pays for screening only, with no guaranteed presentation. Four days from a standing start would have produced a synthetic-only entry. Because IRIS requires enrolment at a school in India, this was the only possible IRIS cycle, so the India → ISEF route is now closed.

Nothing has been pushed since 26 Jul (`main` and this branch were both at `8626ce6` on 29 Sep). If you have unpushed harness work locally, commit it; Stage 1 shrinks accordingly.

What the decision changes:

- **JSEC is the remaining ISEF route.** Whether a foreign student enrolled in Japan is eligible is still undocumented (`RESEARCH_ROADMAP.md`). Ask JSEC now rather than after relocating, because the answer decides whether this project has any fair deadline at all.
- **ISEF judges only research inside a 12-month window.** For ISEF 2027 the window begins no earlier than January 2026 ([rules](https://www.societyforscience.org/isef/international-rules/rules-for-all-projects/)). By the same pattern, ISEF 2028, the cycle JSEC 2027 would feed, likely begins January 2027; confirm this in the 2027–28 rules. Work from 2026 would then be prior research in a continuation project (Form 7), and only a substantive expansion would be judged. The stages already split that way, so nothing needs delaying:
  - Stage 1 and the 2026 part of Stage 2 would be prior research.
  - The 2027 work (model improvements, new exercises, data from other people) would be the expansion.
- **The ethics rules still apply.** JSEC follows ISEF's human-participant rules, and consent and privacy law cover recording other people whether or not a fair is involved (§5.3, §6).
- **The portfolio doesn't depend on IRIS.** None of the ten items in `RESEARCH_ROADMAP.md` Part 2 requires a fair result.
- **Relocation (mid-2027 per `RESEARCH_ROADMAP.md`) is the last hard date.** It bounds the Stage 3 pilot with other people, which needs participants and approval from your current school in India. It doesn't bound the research itself.

---

## 1. What the repository actually does (verified 2026-09-29)

### 1.1 Capability audit

| Capability | Claimed in README / docs | Actual state |
|---|---|---|
| Monocular SMPL recovery (HMR2) | Working | **Real**, but affected by defects M2–M5 and M11. |
| Multi-view triangulation | "Multi-View 3D Spatial Triangulation (EasyMocap)" | **Not performed anywhere in rvectr's own code.** Three scripts claim to triangulate and none does, and no script invokes EasyMocap's own triangulation. Searching `backend/*.py` for `triangulatePoints`, `svd`, `solvePnP`, `stereoCalibrate`, projection matrices and EasyMocap's `mv1p` / `apps/demo` entry points finds nothing (M7). |
| Kinematics extraction | Working | **Real**, but affected by convention bugs M5 and M6. |
| Live in-browser pose (`/test/squat`) | "zero-latency" | **Runs, but angles read +8° to +24° high** on typical squat knee angles (M1). |
| 3D viewer | Plays captured mesh | Defaults to `squat_multiview_animated.glb`, which only the authored sine-wave generator produces (critical_analysis finding 0). Frame count and duration are hardcoded to 291 frames and 9.7 s (`ThreeMeshCanvas.tsx:224`). The companion OBJ, `.blend` and `.npy` assets have unknowable provenance (M12). |
| Upload → analysis | — | No backend exists, and the page fails loudly, which is the correct behaviour. |
| `squat_kinematics.json` (161 frames) | Real | Plausibly genuine HMR2 output, but provenance is unverified. Femur length varies from 0.355 to 0.392 m within one clip, which indicates per-frame shape instability (M4). |
| `running_kinematics.json` (90 frames) | "real per-frame joint data" (`critical_analysis.md:247`) | **Procedurally generated** (see below). |
| Tests | "31 tests pass" | On a clean clone: **30 pass, 1 skip, 1 error.** The fixture at `tests/conftest.py:18` needs the licensed `SMPL_NEUTRAL.pkl`, so the CI workflow as written would fail on its first run. |
| CI | Written | Not active: `docs/ci-workflow.yml` is waiting on a token with `workflow` scope. |
| Submodule backup (finding 2) | Open risk | **Resolved in practice.** The pinned commits `00d4b82` and `ec0e8c9`, authored 26 Jul, can be fetched from GitHub. `.gitmodules` still points at the upstream repositories, so fetching relies on GitHub sharing objects across a fork network. Point it at your forks. |
| Unbacked claims in the UI (finding 18) | "FIXED" | **Still present** (M10). |

How `running_kinematics.json` was produced: `download_and_extract_running.py:24` downloads a Chromecast advert (`ForBiggerBlazes.mp4`) and never uses its frames. Line 101 then shears the SMPL template's leg vertices along z. Across the "running" sequence, knee angle only ranges over 170.5–171.3° (real running swings through roughly 80–100°), and the ankle angle is exactly constant.

### 1.2 Measurement defects, ranked by damage to a number

Each defect is sized against the 5° threshold used in the study.

**M1 — Live angles are computed on normalized image coordinates.**
`src/app/test/squat/page.tsx:289` passes `results.landmarks` into `lib/cv/angles.ts`. In those coordinates x is divided by the frame width, y by the frame height, and z is on roughly the x scale. Angles therefore distort on any non-square frame. In a 2D simulation of a side-view squat at 1280×720, the error on common knee angles was +8° to +24°; the worst case over the grid was 28° (landscape) and 32° (portrait). The noisier z coordinate adds error on top of that.
*Fix:* use `worldLandmarks` (metric 3D, hip-centred), or multiply x by width and y by height before computing angles. Add shared test vectors (§2.3).

**M2 — Frames are subsampled, and the kinematics code assumes a different frame rate.**
`process_video_3d.py:33` defaults to `target_fps=15`, `run_4d_humans_videos2.py:57` uses `step = 2`, and `extract_kinematics.py:293` assumes 30 fps. When these disagree, velocities are wrong by 2×. Sampling alone also misses peaks. The error is about ½·|θ̈|·(Δt/2)², which for a fast squat bottom (θ̈ ≈ 5000°/s²) is **≈2.8° at 15 fps** and ≈0.7° at 30 fps.
*Fix:* process every frame, carry per-frame timestamps from the container, and never assume a frame rate.

**M3 — Detection failures are silently imputed or dropped.**
`run_4d_humans_videos2.py:108` copies the previous mesh forward when detection fails, or writes an all-zero mesh if the first frame fails. `process_video_3d.py` skips the frame (`continue`), after which `extract_kinematics.py` renumbers the files from `sorted(glob)` and shifts the time base. Velocities are corrupted around every dropout. This also violates the pre-registration draft ("not imputed and not silently dropped").
*Fix:* keep an explicit `detected[]` mask, and write NaN rather than copies.

**M4 — Body shape (β) is re-estimated every frame.**
As a result, joint centres move from frame to frame; femur length varies by about 10% within one squat clip.
*Fix:* fix β per subject, either as the median over the clip or from a static A-pose trial (§2.3), and re-pose with the per-frame θ.

**M5 — "Vertical" is the camera's y-axis, not gravity.**
At `extract_kinematics.py:176`, phone pitch or roll goes directly into trunk lean: a 10° phone tilt is a 10° error.
*Fix:* record the gravity vector from the phone's IMU at capture (§5.2), or estimate the floor plane from stationary feet.

**M6 — Angle conventions are inconsistent.**
- 3-point included angles mix anatomical planes.
- `torso_lean` is reported as 180° − lean; the most upright frame reads 166.7°.
- Shoulder and pelvic tilt wrap at ±180°, so near-level shoulders read about −179.9° and a small tilt the other way flips to +179°.
*Fix:* one angle module with defined degrees of freedom (§2.3).

**M7 — Multi-view reconstruction is not a measurement.**
- `recalibrate_and_reconstruct_3d.py:160` averages two MediaPipe skeletons that are each expressed relative to their own camera (`(pts1 + pts2) / 2.0`). There are no extrinsics and no triangulation, yet line 193 prints "zero reprojection drift".
- `run_easymocap_videos2.py:157` writes MediaPipe's first 25 landmarks into OpenPose's BODY25 field (`pose_keypoints_2d`), but the two orderings differ: BODY25 index 1 is the neck, MediaPipe index 1 is the left-eye-inner.
- Calibration uses one chessboard image per camera, which is underdetermined, and falls back to invented values (`T2 = [0.5, 0, 0.1]`).
- `sync_and_recalibrate_videos2.py` claims to produce extrinsics and RANSAC triangulation. In fact it writes hardcoded intrinsics and made-up distortion coefficients, and its audio-sync offset has the wrong sign: in testing, a 0.5 s offset became 1.0 s.

*Fix:* replace the multi-view path wholesale: angle fusion in Stage 1, calibrated triangulation in Stage 2 (§4.2).

**M8 — Variable-frame-rate video is resampled to a constant frame rate.**
`pipeline/smartphone_sync.py:62` uses `-r 30 -vsync cfr`. This adds up to half a frame (16.7 ms) of timing jitter per camera, which at 300°/s is about 5° of disagreement between views.
*Fix:* keep the native timestamps and interpolate poses, not frames.

**M9 — `batch_process.py` falls back to all-zero mocks.**
Lines 12–18 import `load_regressor` and `extract_joints_from_meshes`, which don't exist, and silently fall back to mocks that return zeros.
*Fix:* remove the fallback and fail loudly.

**M10 — Unbacked claims remain in the UI.**
- "sub-centimeter accurate", "Industrial-grade" (`app/demo/page.tsx:28`)
- "EasyMocap Output" shown on the synthetic mesh (`:48`)
- "A clinical system", "clinical diagnostic evaluation" (`app/page.tsx:54,61,213`)
- `app/layout.tsx:27`
- "Sub-centimeter SMPL Surface Mesh" (`ThreeMeshCanvas.tsx:364`)
- "Clinical Posture & Kinematic Diagnostic" (`analysis/page.tsx:134`)

This is an integrity problem rather than a measurement error.
*Fix:* remove them, and extend the CI claims check to `src/`.

**M11 — HMR2's assumed focal length does not match a phone.**
The assumed focal length is `5000/256 ×` the image size, about 19.5× (a field of view of ~3°), whereas a phone is about 0.7–0.8×. Camera-space translations, and therefore `squat_depth` and its velocity, are not metric. Angles are affected mildly by perspective error.
*Fix:* use estimated or EXIF intrinsics, or a backend that estimates intrinsics.

**M12 — Output provenance is unknowable.**
More than a dozen scripts write to the same fixed paths in `videos2/`: `obj_sequence/`, `squat_3d_mesh.{obj,blend}`, `squat_multiview_animated.blend`, `squat_vertices_anim.npy` and `squat_multiview_anim.npy`. The writers mix every kind of output: real HMR2 (`run_4d_humans_videos2.py`), synthetic (`run_easymocap_videos2.py`, `make_perfect_squat_anim.py`), averaged MediaPipe (`recalibrate_and_reconstruct_3d.py`), and shape- or position-altered meshes (`enhance_muscular_anchored_smpl.py`, `zero_drift_perfect_smpl_builder.py`, `lock_stationary_smpl.py`). Whatever sits in those paths now came from whichever script ran last, and nothing records which one. This is why July's "trace the provenance of every result file" item can't be closed by inspection.
*Fix:* write each run to its own directory with a manifest recording backend and version, input SHA-256, git commit and parameters. Treat existing unmanifested assets as unknown and regenerate them rather than trying to trace them.

**Leftovers that don't belong in the project:**
- `train_biomechanics_llm.py` and `pipeline/biomechanics_training_data.jsonl`, whose hand-written outputs include claims such as "INJURY RISK: … L4/L5 shear"
- `squat_dataset.json`
- `src/lib/knowledge/*`
- `src/lib/calisthenics.ts`

Archive them.

**What is genuinely usable:**
- the HMR2 inference loop
- `J_regressor` joint extraction
- the SMPL posing code in the scripted-squat generator, which is the seed of the ground-truth generator
- MediaPipe integration in both Python and the browser
- the rep-counter state machine, once M1 is fixed
- the viewer components (`DualViewport`, `TimelineScrubber`, `KinematicWaveformChart`)
- `rvectr_paths.py`
- the gait-event tests, as a pattern for testing against synthetic signals with known truth

---

## 2. Target system

### 2.1 One pipeline, two consumers

```mermaid
graph TD
    S["Synthetic θ → render<br/>blur · rolling shutter · fps · codec"] --> I
    R["OpenCap / Fit3D<br/>video + marker mocap"] --> I
    P["Phone recording<br/>demo · capture app"] --> I
    I["Ingest<br/>rotation · frame timestamps · gravity"] --> A
    A["Backend adapters<br/>MediaPipe · HMR2 · SAM 3D Body · OpenCap Monocular"] --> PS[("PoseSequence v1")]
    PS --> K["Kinematics<br/>one angle module"]
    K --> J[("JointAngleSeries v1")]
    J --> E["Eval vs reference<br/>trust map · figures"]
    E --> T[("Trust table")]
    J --> V["Viewer / capture app<br/>angles + trust badges"]
    T --> V
```

**Rule:** the demo never displays an angle the study didn't evaluate, computed by code the study didn't run.

### 2.2 Schemas: the adapter contract

- **`PoseSequence` v1**
  - backend id and version, video SHA-256
  - per-frame timestamps in seconds, `detected` mask, confidence
  - `joints3d [N,J,3]` with a declared coordinate frame and joint set
  - optional `rotations [N,J,3,3]`, fixed β, optional 2D keypoints
  - camera intrinsics, flagged as calibrated, estimated or assumed
  - gravity vector, if known
- **`JointAngleSeries` v1**
  - named degrees of freedom (below), definition version
  - timestamps, validity mask

### 2.3 Angle definitions: one module, mirrored in TypeScript

- **Degrees of freedom, per side:**
  - knee flexion
  - hip flexion, adduction and rotation
  - ankle dorsiflexion
  - trunk lean relative to gravity (sagittal and frontal)
  - elbow flexion
  - shoulder elevation
- **Evaluate in angle space, not model-parameter space.** SMPL, MHR (SAM 3D Body), OpenSim and MediaPipe landmarks then all become comparable.
- **Compute angles two ways and compare them:**
  - (a) segment-frame angles from joint positions plus gravity
  - (b) angles read directly from SMPL/MHR rotation matrices with a per-joint calibration table. [Kardolus et al., Jul 2026](https://arxiv.org/abs/2607.17639) report 4.50° pooled MAE this way (4.66° on SAM 3D Body).
- **OpenSim naming for OpenCap-data comparisons.** Output OpenSim coordinate names (`knee_angle_r`, `hip_flexion_r`, …) there, because the reference is OpenSim inverse kinematics.
- **Shared JSON test vectors.** Known poses and their expected angles run in both pytest and the TypeScript tests, so the Python and browser implementations can't drift apart. This check alone would have caught M1.
- **Static A-pose trial.** Put a 3 s trial at the start of every recording. It provides per-subject neutral offsets (standard practice in motion-capture labs), a fixed β (M4), and a sanity check: a standing knee should read about 175–180°.

### 2.4 Code layout

- **Backend package.** Build `backend/rvectr/{ingest, backends/, kinematics, harness/, eval, trust, export, cli}` as an installable package with one CLI (`rvectr process clip.mp4 --backend hmr2`).
- **Old scripts.** Move the ~30 loose scripts into `backend/legacy/` together with their status table. Don't delete history.
- **Frontend.** Keep Next.js. The frontend is already built, and uploads need a server anyway. Before touching Next 16 APIs, read `node_modules/next/dist/docs/` (see `AGENTS.md`).
- **GPU worker.** Run the GPU work as a separate Python FastAPI worker with a SQLite-backed job queue.

---

## 3. The research: from one velocity threshold to a trust map

### 3.1 What is already known, so you don't re-measure it

| Work | Setup | Result |
|---|---|---|
| [OpenCap](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1011462) (2023) | 2 calibrated iPhones | **4.5° MAE** against marker mocap (walking, squat, sit-to-stand, drop jump; 1.7–10.3° range) |
| [OpenCap Monocular](https://github.com/utahmobl/opencap-monocular) (2026 preprint) | 1 phone; WHAM + optimisation + OpenSim | **4.8° MAE** on rotational DOFs; walking, squat, sit-to-stand |
| [Kardolus et al.](https://arxiv.org/abs/2607.17639) (Jul 2026) | Angles read from SMPL / SAM 3D Body rotations | **4.50° / 4.66°** pooled MAE over 15 DOFs |
| [Sci Rep 2025](https://www.nature.com/articles/s41598-025-22626-7) | 11 off-the-shelf monocular estimators; 25 people exercising | Knee **14.1–25.8°** MAE in 3D; **none below 5°** |
| [Fit3D benchmark](https://doi.org/10.3390/jimaging12070311) (Jul 2026) | 19 methods; fitness exercises; Vicon reference | Position error in mm; fitness-specific fine-tuning helps the hardest exercises most (12.3 mm vs 4.2 mm) |
| [Turner et al.](https://arxiv.org/abs/2608.24384) (Aug 2026) | BlazePose on squat, bench and deadlift | Strongly view-dependent; non-sagittal views distort angles |
| [McGinley et al. 2009](https://doi.org/10.1016/j.gaitpost.2008.09.003) | Systematic review of marker-based reliability | 2–5° reasonable, >5° a concern; **transverse-plane hip and knee angles are least reliable even with markers** |

**Implications:**
1. The current pipeline computes raw angles from off-the-shelf outputs, the approach that landed at 14–26° in the Sci Rep study. Don't assume you are anywhere near 5° until §2.3 is done and measured.
2. "Is phone mocap accurate on average?" is answered: about 5° with the right pipeline.
3. What is not answered is which *conditions* break it and how a user would know at runtime. I searched for a controlled study of error against angular velocity and did not find one. That is not proof none exists, so run a proper literature search before claiming novelty.

### 3.2 Treat velocity as a set of mechanisms

A per-frame model can only perceive speed through the image, so "velocity" decomposes into separate mechanisms:

| Mechanism | Scales with | Consumer-hardware knob |
|---|---|---|
| Motion blur | angular velocity × exposure time | Lighting: phones lengthen exposure indoors, up to about 1/fps |
| Rolling-shutter skew | angular velocity × sensor readout time | Sensor: phones are typically in the ~10–30 ms range; lab cameras use global shutters |
| Peak sampling | angular acceleration × (frame interval)² | Frame rate (30/60/120/240) |
| Temporal model or filter lag | velocity × window length | Backend: video models, MediaPipe VIDEO mode (tracking plus smoothing), post-filters |
| Multi-view sync residual | velocity × sync error | Sync method: ±½ frame with audio sync plus constant-frame-rate resampling |

**Implications worth testing:**
- **Renders without simulated blur can't show a velocity effect.** A per-frame model, given a time-warped render without blur, sees the same set of sharp images, just fewer of them per rep. H1 would then fail for a trivial reason and tell you nothing.
- **The "velocity threshold" is not a property of the pose model.** It depends on model × exposure × readout × fps × filter. The same squat speed can be trustworthy in daylight and untrustworthy under a dim ceiling light. For blur, report the boundary in *blur displacement* (ω·t_exp) rather than ω alone, and turn the result into advice ("bright light, 60 fps").
- **Pre-registered H3 may be wrong for consumer rigs.** H3 says multi-view degrades most slowly, but sync residuals add a velocity-proportional error that single-camera setups don't have. Test it by injecting sync offsets of 0, 8, 17 and 33 ms in the harness.
- **Compare MediaPipe IMAGE mode with VIDEO mode.** The difference between them isolates the tracking and smoothing mechanism for free.
- **Filters can also create velocity-dependent error.** Savitzky–Golay still attenuates sharp peaks, though less than a Gaussian. Rule: any filter must pass a "ground truth through the filter" test with <0.5° peak error at the fastest condition, with its window set in seconds, not frames.

### 3.3 Factors: the axes of the trust map

**Exercise class**, grouped by failure mechanism rather than gym taxonomy:

| Class | Examples | Expected failure |
|---|---|---|
| Upright, sagittal | squat, lunge, deadlift / RDL, sit-to-stand | Depth ambiguity unless filmed side-on |
| Upright, frontal | lateral lunge, lateral raise | Invisible from a side view |
| Prone / horizontal | push-up, plank | Poses rare in training data; floor occlusion |
| Supine | glute bridge, sit-up | Rare poses; self-occlusion |
| Overhead | press, pull-up | Arms occlude the head and trunk |
| Ballistic, in place | jump squat, kettlebell swing, burpee | Blur and rolling shutter; highest ω |

**Other factors:**
- **Joint × plane:** sagittal flexion, frontal (valgus / adduction), transverse (rotation). Expect a steep ordering (McGinley).
- **Camera:** azimuth 0/30/45/60/90°, elevation (floor, hip or head height), and distance.
- **Capture settings:** fps, exposure, readout time, resolution, codec bitrate.
- **Backend:** MediaPipe, HMR2, SAM 3D Body, OpenCap Monocular.
- **Setup:** the number of phones (1, 2 or 3), and how their positions are given (label only vs calibration board). Paired with setup time, this answers the headline question: how accurate can a normal person get, and what does each extra step buy? (§4.2)
- **Clothing:** fitted (shorts or leggings), track pants, loose pants. Tested on real footage in §3.7.
- **Body:** you and your teammate give two real bodies; synthetic data adds a wider range of shapes (β).

**Don't run the full factorial.** Sweep one factor at a time around a nominal condition, then run a Latin-hypercube sample to probe interactions.

**On "in-place movements now, running later":** in-place exercises remove translation and tracking confounds, so the focus is sound. There are two consequences:
- In-place exercises reach lower angular velocities, so the ballistic class must be included, otherwise the 5° boundary may never be crossed.
- Treadmill running is also in-place from the camera's point of view, with belt speed as a known reference. It reuses this entire pipeline rather than needing new alignment work. Only overground running needs the harder alignment.

### 3.4 Analysis rules (put these in the OSF draft before registering)

1. **Angular velocity comes from the reference** (the authored θ or mocap), never from the estimate. Estimate-derived velocity shares noise with the error, which produces a spurious correlation between error and velocity (an errors-in-variables problem).
2. **Bootstrap by sequence, rep or subject, not by frame.** Frames are autocorrelated, so a frame-level bootstrap gives falsely narrow confidence intervals. The current draft says "10,000 resamples" without naming the resampling unit.
3. **Report bias and precision separately:** Bland–Altman mean ± 1.96 SD, plus the percentage of frames within 5°.
4. **Report detection failure as a separate outcome and never impute it.** The draft already says this; the code violates it (M3).
5. **Use a 5° threshold, citing McGinley et al. 2009.** That review is a primary source, stronger than citing goniometer reliability, and the Sci Rep 2025 study uses the same line.
6. **Trust boundary:** the condition at which the upper 95% confidence bound of the MAE crosses 5°.
7. **Lead with the change in error, not only its level.** A backend's joint set rarely matches the reference's exactly (MediaPipe's hip landmark is not SMPL's hip joint), so absolute comparisons carry a constant definitional bias. Within-backend changes across conditions (1× → 4×, blur off → on) cancel that bias. Report absolute levels separately, alongside the bias.

### 3.5 Data tiers: only some data can measure accuracy

| Tier | Source | Reference ("truth") | Answers | Ethics approval needed? |
|---|---|---|---|---|
| **T1** | Synthetic renders: authored θ, textured SMPL, Blender | Exact | Causal effect of each mechanism in §3.2 | No |
| **T2** | [OpenCap lab dataset](https://simtk.org/projects/opencap): ~10 participants; squat, sit-to-stand, drop jump, walking; 5 synchronized smartphone views plus markers and force plates. [Fit3D](https://fit3d.imar.ro/): ~47 exercises, 13 subjects, 4 RGB cameras plus Vicon, scored on an evaluation server | Marker mocap | Real-world validity; whether T1 predicts real error | No: public data (check the licences) |
| **T3** | You and your teammate: held positions measured with a phone angle-meter, under different clothing and camera views (§3.7) | Consumer-grade reference | Clothing and view effects on real bodies, with your own phones in your own rooms | No: as the student researchers, you two are exempt |
| **T4** | Other people using the capture app | **None** | Reliability (test–retest ICC, SEM, MDC95), robustness, failure rates, backend disagreement | **Yes: IRB approval before recruiting** |

**Notes on the tiers:**
- **OpenCap's 5 views are a gift.** Each trial is seen from 5 azimuths with one marker-based truth, which gives the camera-view axis of the trust map on *real* footage.
- **Validity of the phone reference (T3).** Smartphone goniometer apps agree with a universal goniometer on static knee angles with a concordance correlation coefficient above 0.96 ([Milanese 2014](https://www.sciencedirect.com/science/article/abs/pii/S1356689X14001118)). Use the phone as a reference for held positions; treat its use during movement as exploratory.
- **T4 cannot measure accuracy.** It measures whether the system gives the *same* answer twice, and whether it survives real rooms and phones. For progress tracking, MDC95 (the smallest detectable change) is arguably *the* trust number, and it needs no ground truth.
- **A free red flag at runtime.** If two backends disagree by *d*, at least one of them is wrong by at least *d*/2 (triangle inequality). Disagreement is observable without ground truth.
- **Cheap physical constraints for T4.** A box squat to a chair fixes the bottom position, and a wall sit is a static hold. Both give within-subject consistency checks across views and sessions without any reference equipment.

### 3.6 Deliverables

- **Figure 1:** error vs blur displacement (ω·t_exp), per backend, with confidence intervals and the 5° line.
- **Figure 2:** trust-map heatmap of exercise class × DOF × camera view. Each cell holds the predicted MAE; cells whose upper confidence bound exceeds 5° are hatched.
- **Figure 3:** error predicted from synthetic data vs error measured on OpenCap footage. This is the sim-to-real check.
- **Table:** MAE per backend and DOF on OpenCap squat and sit-to-stand trials, with Bland–Altman limits of agreement.
- **Figure 4:** error vs clothing type, per camera view (§3.7).
- **Figure 5:** error vs setup effort: 1 phone → 2 labelled phones → 2 calibrated phones, with setup time on the x-axis (§4.2).
- **Released artifact:** a JSON trust table, which the Studio and capture app consume (§4.1).

### 3.7 Experiment B: clothing and camera view

On a multi-camera lab system (Theia3D) during walking, switching between sport and street clothing changed joint angles by only 2.6° on average ([Keller et al. 2022](https://www.researchgate.net/publication/361538327_Clothing_condition_does_not_affect_meaningful_clinical_interpretation_in_markerless_motion_capture)). That setting makes clothing least likely to matter: many cameras see through gaps in the fabric, and walking barely bends the hips and knees. Whether the result holds for **one phone during a deep squat**, where loose fabric bunches at the hip and knee, hasn't been tested. Either answer is a result.

- **Subjects:** you and your teammate. As the student researchers you can be your own subjects, and two bodies beat one. Take turns: one holds the position while the other measures and records.
- **Reference:** a phone angle-meter app (e.g. phyphox, which is free) measures the knee angle during each hold. Holds take speed out of the problem.
- **Holds:** standing, quarter squat, half squat and a wall sit at about 90°, 5 s each. A wall sit is easy to repeat at the same depth.
- **Conditions:** 3 clothing types (shorts, track pants, loose pants) × 2 camera views (side, 45°), with both phones recording at once and synced by a clap. Record following §4.7. The same clips also test fusion: side alone, 45° alone, and fused.
- **Result:** error vs clothing type for each view. Headline the change in error from shorts to loose pants; that cancels the constant offset between a surface angle-meter and a skeleton angle (§3.4 rule 7).
- **Limit:** holds capture what fabric hides when still. Fabric swinging during fast reps is a later, harder test.

---

## 4. The platform: Studio for the person recorded, Lab for you

Two faces on one system, like a film or game motion-capture stage: the performer gets a simple, polished experience, and the operator sees every step on their own screen. Everything runs locally on your laptop.

### 4.1 How the pieces connect

| Piece | What it is | Role |
|---|---|---|
| **SMPL** | A standard 3D template of the human body (6,890 surface points, 24 joints), shaped by pose numbers (θ) and body-shape numbers (β) | The 3D model everything is expressed in |
| **HMR2 (4D-Humans)** | An AI model: one frame in, SMPL θ and β out | The main engine, run on each video separately |
| **MediaPipe** | A fast AI model that outputs 33 body points | The instant live view, and a second opinion for trust checks |
| **SAM 3D Body** | A newer single-image model with its own MHR body model | An optional third opinion (Stage 2) |
| **Sync** | Lines videos up in time using a clap in the audio | Needed whenever there's more than one video; first fix the sign bug in the old script (M7) |
| **Fusion** | Combines each view's joint angles, weighting each view by the trust table | Multiple phones without calibration (§4.2, mode 2) |
| **Pose2Sim / aniposelib** | Calibration from a printed board, then true 3D triangulation | Calibrated multi-phone mode (§4.2, mode 3) |
| **EasyMocap** | Multi-camera SMPL fitting | Superseded here by the two rows above; stays parked (M7) |

### 4.2 Capture modes: what each extra step buys

| Mode | What the person needs | How views are combined | Expected accuracy | When |
|---|---|---|---|---|
| **1. One phone** | One phone on a tripod | — | About 4.8° MAE for a published single-phone pipeline with biomechanical constraints; raw off-the-shelf output is far worse (14–26° on knees in one study) | Stage 1 |
| **2. Two or three phones, positions labelled** | Extra phones, a clap at the start, and each video dragged to its spot on a floor plan | Each view measures the angles itself, because a joint angle doesn't depend on where the camera stands. Each angle is then a trust-weighted average: side views count most for knee bend, front views for knees caving in. No calibration needed | Unknown; this is what you measure | Stage 1 |
| **3. Two or three phones, calibrated** | Also a printed checkerboard, shown to all phones for a few seconds | True 3D triangulation from exact camera positions | About 4.5° MAE with two calibrated iPhones (OpenCap) | Stage 2 |

Two consequences:
- **Saying where each camera is isn't enough for triangulation.** Triangulation needs camera positions and directions to within about a centimetre and a degree. A label like "side, 3 m" is far too rough, which is why mode 2 fuses angles instead and mode 3 uses a board.
- **More cameras aren't automatically the biggest win.** On average, published one-phone and two-phone pipelines are close (4.8° vs 4.5°): the processing matters more than the camera count. Extra views should help most where one camera is blind: knees caving in (frontal plane), twisting (transverse plane), and the far side of the body. Measuring *how much* each extra step buys is the headline question (§3.3).

OpenCap is the professional version of mode 3; its capture app needs iPhones and a checkerboard. Your version targets Android phones, adds a no-board mode, and adds trust badges.

### 4.3 The Studio (for the person recorded)

Beautiful and simple, with five screens:
1. **Home:** "New capture", plus recent captures.
2. **Plan:** choose the exercise. A floor plan shows where to put each phone (from the trust table), with tips on light and clothing.
3. **Upload:** drop one or more videos. Each becomes a card that you drag onto its spot on the floor plan (front, side, 45°). Fill in the person, clothing and notes.
4. **Processing:** progress in plain words ("lining up videos", "building your 3D body", "measuring angles").
5. **Results:**
   - the 3D body replaying beside the video, which you can rotate and scrub
   - per-rep numbers (depth, left/right difference, tempo) with trust badges in plain language ("Knee angle 94° ± 4° — trusted")
   - **"How to get a more accurate result next time"**, e.g. "add a front phone to measure knees caving in". This advice comes straight from the trust table.

### 4.4 The Lab (for you)

Everything the Studio hides, stage by stage, for any session:
- **Ingest:** resolution, fps, rotation, duration and codec for each video, plus a thumbnail strip.
- **Sync:** the audio waveforms aligned, the offset of each video in ms, and how confident the match is.
- **Detection:** person boxes drawn on the video, with frames where the person was lost marked on the timeline.
- **2D points:** the MediaPipe overlay and each joint's confidence over time.
- **3D per view:** the HMR2 mesh drawn over each video, and each view's angle curves.
- **Fusion:** per-view vs fused angle curves, the weights used, and where the views disagree.
- **Kinematics:** detected reps and a per-rep table.
- **Trust:** a badge timeline with the reason for each badge.
- **Performance:** time per stage and GPU memory.
- **Provenance:** the run manifest (pipeline version, parameters, input hashes).
- **Export:** JSON, CSV, OpenSim `.mot`, and BVH, the standard skeleton-animation format for motion capture. Blender opens BVH directly; for Unity or Unreal, convert it to FBX (e.g. through Blender).
- **Dataset page:** every session in one table, filterable by person, clothing, view, speed and mode, next to the experiment graphs. This is where the trust map lives.

### 4.5 Under the hood

- **Data model:**
  - A *session* is one recorded take (person, exercise, clothing, notes).
  - A session has one or more *views*: a video, its position label and the phone's details.
  - A *run* processes a session with a given pipeline version and settings.
  - Each *stage* of a run saves its outputs and metrics to `runs/<id>/<stage>/`.

  The Lab simply displays those folders, so nothing is hidden and every result can be regenerated (M12).
- **Server:** FastAPI in the HMR2 Python environment, with a job queue and SQLite for the session index.
- **Web:** the existing Next.js app, with `/studio` and `/lab` pages that reuse `DualViewport`, `ThreeMeshCanvas`, `TimelineScrubber` and `KinematicWaveformChart`.
- **One command:** e.g. `./studio.sh` starts both; then open `http://localhost:3000/studio`. Localhost counts as a secure origin, so the webcam and file drop work without HTTPS.
- **Timing:** processing time adds up with every video, so 2 phones × 15 s is the demo sweet spot. Measure it.
- **Phones at different frame rates:** combine views on timestamps, never on frame numbers.
- **No NVIDIA GPU:** a MediaPipe-only fallback (skeleton, no mesh).

### 4.6 Instant view

The live page (`/test/squat`) stays as the instant tier: webcam in, skeleton and angles out in real time, once M1 is fixed. It keeps judges engaged while a session processes.

### 4.7 Recording protocol

Use the same protocol for demo clips, experiments and the exhibition:
- **Each phone:** on a tripod at hip height, 3–4 m away, whole body in frame, with space above the head and below the feet.
- **Views:** side-on for squat depth, front-on for knees caving in, and 45° as the in-between.
- **Settings:**
  - 1080p at 60 fps, the same on every phone if possible
  - focus and exposure locked (tap and hold)
  - stabilisation off
  - bright light facing the person
  - plain background, nobody else in frame
- **Multiple phones:** start every recording, then give one sharp clap that all phones can hear.
- **Mode 3 only:** hold the printed checkerboard where every phone can see it for 5 s at the start.
- **Take structure:** stand still in an A-pose for 3 s → 5 reps → stand still for 2 s.
- **File labels:** name each file by person, clothing, speed and view, e.g. `p1_shorts_normal_side.mp4` and `p1_shorts_normal_45.mp4`. These labels become the trust-map factors.

### 4.8 Exhibit setup

- **Equipment:** two phones on tripods (side and 45°) and the laptop. No venue internet needed.
- **Flow:**
  1. A judge squats, after one clap.
  2. You drop both videos into the Studio.
  3. The Lab, on a second screen or tab, shows each stage as it runs.
  4. The results appear with badges and advice.
- **Demo mode keeps nothing.** Delete visitor clips after the session.
- **Backup:** keep pre-processed fallback clips in case anything fails, and dry-run the whole setup three times.

### 4.9 Mesh licensing

The SMPL model data (template, skinning weights) is licensed and may not be redistributed. A public web app that ships a skinned SMPL rig is therefore a licence risk; a local exhibit is not. For the public web, send per-frame vertex positions (compressed morph targets) or a skeleton-only view. Check the SMPL licence before publishing anything.

---

## 5. Capture app for other people

### 5.1 Principle: one phone, zero calibration

Two-phone sync and printed ChArUco boards are where volunteers drop out. T4 uses a single phone only; multi-view stays in your own controlled rig.

### 5.2 Flow (a mobile web app, nothing to install)

1. **Consent.** Participants under 18 also need guardian permission plus their own assent. Consent text is versioned and stored separately from the data.
2. **Profile:** height (for scale), age band, and sex (optional). No name.
3. **Choose the exercise.** The app states the camera view and phone height that the trust map recommends for it. For example, squat depth needs a side view at hip height; knee valgus needs a front view.
4. **Setup check** (live MediaPipe, 3 s), each with a specific fix on failure, such as "step back 1 m":
   - the whole body is visible: every landmark has visibility > 0.5 in ≥ 95% of frames
   - the subject fills 50–90% of the frame height
   - the phone is steady and level: pitch and roll within ~5° from `DeviceOrientation` (iOS needs a permission tap)
   - brightness is above a floor
   - the actual frame rate is ≥ 25 fps (request 60)
5. **Record:** a 3 s A-pose static trial, then N reps with an audio countdown.
6. **Upload:** on-device quality checks, a resumable upload (tus), then a results link.
7. **Metadata stored with every clip:**
   - device model, OS and browser
   - resolution, requested and actual fps
   - per-frame timestamps
   - gravity vector and orientation
   - app version and consent version

Treat every threshold above as a starting point, and tune it on your own pilot.

### 5.3 Storage and privacy

- **Uploads:** signed upload URLs to Cloudflare R2 or Supabase Storage. Free tiers cover a pilot; a 20 s 1080p60 clip is roughly 30–60 MB.
- **Optional face blur before upload.** It reduces identifiability; check that it doesn't degrade head and neck angles.
- **Data handling:**
  - a written retention policy
  - deletion on request
  - raw video kept separate from derived pose data
- **Legal:** India's DPDP Act 2023 applies (consent, purpose limitation, erasure), including verifiable parental consent for anyone under 18.

---

## 6. Ethics sequencing

- **Self-testing is exempt; anyone else needs approval first.** Under the [ISEF human-participant rules](https://www.societyforscience.org/isef/international-rules/human-participants/), a student-designed app tested only by the student is exempt from IRB pre-approval. The moment **anyone else** uses it, IRB approval is required **before recruitment begins**.
- **The rules' specifics:**
  - Physical-activity studies count as human-participant research.
  - Under-18s need guardian permission plus their own assent.
  - Risk Assessment Form 3 may apply.
- **The IRB is constituted at your school.** ISEF specifies its minimum composition: an educator, a school administrator, and a medical or mental-health professional. Confirm this against the current rules.
- **Start the paperwork during Stage 2**, because approvals take weeks.
- **Relocation:** in Japan in 2027, obtain local approval again before collecting anything; JSEC rules differ.

---

## 7. Roadmap

This assumes about 12–15 focused hours a week. Stage 1 is sized for the CBSE regional round, which last year ran from late October to November.

### Stage 1 — Exhibition-ready (≈ 30 Sep – end Oct)

**Build the pipeline and the Lab first, and polish the Studio last.** The Lab is how you find bugs and how the science gets done; a beautiful Studio on top of wrong numbers is exactly the failure the July roadmap warned about.

**Week 1 — One-video pipeline + Lab v1**
- [ ] Build the pipeline as stages that save their outputs (§4.5): ingest → detect → MediaPipe → HMR2 → clean-up → angles → reps
- [ ] Build in the measurement fixes:
  - M2: native fps and timestamps
  - M3: missed frames marked
  - M4: one body shape per clip
  - M5/M6: gravity plus one angle module
  - M11: a phone-realistic focal length
  - M12: run folders with manifests
- [ ] Lab v1: a session list, plus every stage's output for one video
- [ ] M1: live-page angles from `worldLandmarks`

**Done when:** a squat video goes through, the Lab shows every stage, and a straight standing knee reads about 170–180°.

**Week 2 — Multiple videos (mode 2)**
- [ ] A position label for each video; clap sync (fix the sign bug first); each view processed separately
- [ ] Angle fusion: combine the per-view angles with trust weights. Use equal weights until Week 3's trust table exists.
- [ ] The Lab shows the sync, per-view vs fused curves, and where the views disagree
- [ ] Record Experiment B with two phones at once, side and 45° (§3.7). One session tests clothing, view and fusion together.

**Done when:** two synced videos of one squat produce one fused result, and the Lab shows how each view contributed.

**Week 3 — Measure**
- [ ] Experiment A: ground-truth squat renders (slow/fast × blur on/off), from several virtual camera positions, so fusion is also tested against exact truth
- [ ] Experiment B: compare the holds with the angle-meter readings
- [ ] Build the first trust table, and use it for the fusion weights and the badges
- [ ] Recommended: register the OSF draft (§3.4) before this first number

**Week 4 — Studio**
- [ ] The five screens (§4.3): floor-plan position picker, upload, progress, and results with badges and advice
- [ ] M10: remove the unbacked claims from the site and the write-ups

**Week 5 — Exhibit**
- [ ] Set up the exhibit as in §4.8
- [ ] Make sure the poster and write-up claim only what the platform shows
- [ ] Do three dry runs and practise a 2-minute explanation

**If the regional date is early:** keep Weeks 1–3 and a plain version of Week 4. Drop the Studio's advice screen and the 45° view.

### Stage 2 — The most accurate a normal person can get (≈ Nov – Feb)

Judge every idea by re-running Experiments A and B and the OpenCap check, and comparing the error before and after.

- [ ] **Mode 3:** checkerboard calibration plus triangulation (Pose2Sim or aniposelib)
- [ ] **Accuracy vs effort:** compare 1 phone, 2 labelled phones, 2 calibrated phones (and 3), each with its setup time. This is the headline figure (§3.6).
- [ ] **Real-footage check on OpenCap:** it has 5 synchronized views plus marker mocap, so modes 1–3 can all be tested on real people
- [ ] **Body calibration:** measure body shape once in fitted clothes, then reuse it in any clothing
- [ ] **Physics rules:** planted feet, fixed bone lengths, gravity
- [ ] **Error predictor:** a small model that learns when readings are wrong. It powers better badges and fusion weights.
- [ ] **Targeted retraining:** fine-tune part of HMR2 on blurred or clothed renders. On an 8 GB GPU, freeze most of the model or use free cloud GPUs. BEDLAM is an option; check its access and licence.
- [ ] SAM 3D Body as an alternative per-view engine
- [ ] Polish the BVH export for animators
- [ ] More exercise classes from §3.3, if time
- [ ] Start the ethics paperwork for Stage 3

**Done when:** the accuracy-vs-effort figure exists, and at least one improvement lowers the measured error.

### Stage 3 — 2027

- The recording app for other people (§5), only after ethics approval
- Fit3D exercises → the full trust map
- Treadmill running
- JSEC, if eligible (§0)

### Backlog (whenever convenient)

- [ ] Email JSEC about eligibility (§0)
- [ ] Package + CLI; move the loose scripts to `legacy/`
- [ ] Delete or relabel `running_kinematics.json` and its generator; remove the `batch_process` mock; archive the LLM and coaching files
- [ ] Tests that need SMPL skip when the file is absent; add a golden-file test; activate CI
- [ ] Point `.gitmodules` at your forks
- [ ] Update `critical_analysis.md`

---

## 8. Cut, park, don't build

- **Cut from any measurement path:**
  - shape "enhancement" (`enhance_muscular_anchored_smpl.py`), which biases joint centres
  - `.blend` generation as a required step; export GLB directly from Python
  - LLM fine-tuning and coaching text
- **Park:** the running pipeline (keep its tests) and EasyMocap.
- **Don't build yet:**
  - accounts, social features, coaching recommendations
  - 0–100 "form scores". A score over angles with ±15° of error is noise with a number on it. Revisit once the trust map says which angles support a score.

## 9. How this fails

- **Collecting other people's data before the Stage 1A fixes.** Every clip then has to be reprocessed, which is why raw video retention matters.
- **Collecting from anyone but yourself before IRB approval.** That data is unusable for ISEF-affiliated fairs.
- **Presenting crowd data as accuracy evidence.** It measures reliability.
- **Letting the demo show an angle the study never evaluated.**
- **Shipping trust badges calibrated only on synthetic data,** without the OpenCap check.
- **Chasing the newest backend instead of finishing the evaluation.** Two backends evaluated honestly beat five evaluated partly.

## 10. Decisions only you can make

1. **Laptop:** the platform plan assumes the RTX 5060 is in the laptop you'll demo on, and that it runs Linux. If not, the MediaPipe-only fallback (§4.5) still works.
2. **Phones:** how many can you use at once? The plan assumes at least two (the CE 3 and the Nord from July), plus your teammate's, all able to record at 60 fps.
3. **`run_easymocap_videos2.py`:** my recommendation is that step 3 becomes the ground-truth generator now, and real multi-view is built as fusion (Stage 1) and Pose2Sim or aniposelib triangulation (Stage 2), not EasyMocap. This settles the open question from July.
4. **Stage 3 participants:** adults only (simpler consent), or peers under 18 (guardian forms)?
5. **Canonical body model:** SMPL (existing code, restrictive licence) or MHR / SAM 3D Body (newer; check its licence)?
6. **Hours per week.** Stages 1–2 are sized at 12–15.

*Decided so far: CBSE 2026–27 under Emerging technologies (team of two plus a mentor teacher; the school is expected to pay the fee); IRIS 2026–27 skipped.*

## Sources

- IRIS National Fair: [site](https://www.irisnationalfair.org/) · [registration](https://register.irisnationalfair.org/)
- Uhlrich et al., [OpenCap](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1011462), PLOS Comp Biol 2023 · [dataset (SimTK)](https://simtk.org/projects/opencap)
- [OpenCap Monocular](https://github.com/utahmobl/opencap-monocular) · [SimTK](https://simtk.org/projects/opencap-monoc)
- Kardolus et al., [Direct clinical joint angle extraction from parametric body model rotation matrices](https://arxiv.org/abs/2607.17639), 2026
- [Assessment of monocular human pose estimation models for clinical movement analysis](https://www.nature.com/articles/s41598-025-22626-7), Sci Rep 2025
- [Hitting the Gym with Fit3D](https://doi.org/10.3390/jimaging12070311), J. Imaging 2026 · [Fit3D dataset](https://fit3d.imar.ro/)
- Turner et al., [Markerless pose estimation for resistance training technique assessment](https://arxiv.org/abs/2608.24384), 2026
- [SAM 3D Body](https://arxiv.org/abs/2602.15989), 2026 · [weights](https://huggingface.co/facebook/sam-3d-body-dinov3)
- McGinley et al., [The reliability of three-dimensional kinematic gait measurements](https://doi.org/10.1016/j.gaitpost.2008.09.003), Gait Posture 2009
- Keller et al., [Clothing condition does not affect meaningful clinical interpretation in markerless motion capture](https://www.researchgate.net/publication/361538327_Clothing_condition_does_not_affect_meaningful_clinical_interpretation_in_markerless_motion_capture), J Biomech 2022 · [Theia3D reliability in tight vs loose clothing](https://peerj.com/articles/18613/), PeerJ
- Milanese et al., [Knee angle: smartphone app vs universal goniometer](https://www.sciencedirect.com/science/article/abs/pii/S1356689X14001118), Man Ther 2014
- [ISEF Human Participants rules](https://www.societyforscience.org/isef/international-rules/human-participants/) · [ISEF Rules for All Projects](https://www.societyforscience.org/isef/international-rules/rules-for-all-projects/) (research window, continuation projects)
- [Video-based markerless mocap for clinical and rehabilitation biomechanics: scoping review](https://arxiv.org/pdf/2609.18667), 2026
