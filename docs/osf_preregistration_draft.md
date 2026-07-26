# OSF Pre-Registration — DRAFT

**Status:** Not submitted. Prepared 2026-07-26.
**Action required:** create an OSF account, open a new Preregistration using the
"OSF Preregistration" template, paste these sections, and register **before any
error number is computed**. A pre-registration filed after seeing results is
worth nothing and looks worse than none.

Target: register by **2026-08-09** (end of roadmap week 2), which is before the
harness gate on Aug 30.

---

## Title

Velocity-dependent error in markerless 3D human pose estimation on consumer hardware

## Authors

Parth Dalal (independent researcher)

## Description

Markerless 3D human pose estimation is increasingly used for movement analysis
outside laboratory settings, but the conditions under which its measurements stop
being trustworthy are not well characterised for consumer hardware. Error is
usually reported as a single aggregate figure over a benchmark dataset, which
obscures how it varies with the speed of the movement being captured.

This study measures how per-joint 3D pose error scales with joint angular
velocity across three markerless capture backends, and identifies the velocity
beyond which the measurement is no longer meaningful for the intended
application.

## Hypotheses

**H1 (monotonic degradation).** Per-joint angular error increases monotonically
with joint angular velocity across all three backends.

**H2 (threshold existence).** There exists an identifiable joint angular velocity
above which per-joint error exceeds a pre-declared usefulness threshold. That
threshold is declared in advance as **5°**, chosen because it approaches the
inter-rater reliability of manual goniometry reported in the clinical literature —
beyond it the measurement carries no more information than a hand measurement.

**H3 (backend ordering).** Multi-view triangulation (EasyMocap) degrades more
slowly with velocity than monocular recovery (4D-Humans/HMR2), which degrades
more slowly than the realtime backend (MediaPipe Tasks).

**Directional note.** H1 and H3 are directional. H2 is existence-only; the
threshold value is estimated, not hypothesised.

## Design

Computational experiment on synthetic data with known ground truth, plus a
real-footage cross-check.

**Independent variable (primary):** joint angular velocity, manipulated by
time-warping one authored motion sequence at 0.5×, 1×, 2×, and 4× playback. The
same kinematic trajectory is traversed at four speeds, so velocity varies while
the movement itself is held identical. This avoids the confound of comparing
different movements (e.g. squat vs. running) which differ in more than speed.

**Additional manipulated variables:** off-axis camera angle, camera distance,
occlusion condition, capture frame rate.

**Dependent variable:** per-joint, per-frame absolute angular error against the
authored θ, summarised as per-joint MAE and reported with bootstrap confidence
intervals.

**Backends:** EasyMocap (multi-view), 4D-Humans/HMR2 (monocular), MediaPipe Tasks
(realtime). All three emit a common versioned `JointAngleSeries` schema through
an adapter interface so error is computed identically across backends.

## Sampling plan

No human participants are recruited. Synthetic sequences are authored SMPL poses
rendered offscreen, so sample size is a design choice rather than a recruitment
constraint: **all four velocity conditions × all backends × full frame count of
each sequence.**

Real-footage cross-check uses self-capture only (the researcher), filming squat
and treadmill running on two consumer phones at 120/240 fps, with ChArUco
calibration and audio-clap synchronisation. Treadmill belt speed provides an
independent ground-truth velocity reference. Filming oneself to test one's own
instrument involves no external participants.

## Analysis plan

1. Per-joint MAE against authored θ for each (backend × velocity) cell.
2. Primary figure: error vs. joint angular velocity, three backends overlaid,
   with bootstrap (10,000 resamples) confidence bands and the 5° threshold
   crossing marked.
3. Monotonicity of H1 tested by Spearman rank correlation between velocity and
   per-joint MAE, per backend.
4. H3 tested by comparing fitted slopes of error against velocity between
   backends, with confidence intervals on the slope differences.
5. Real-footage cross-check: does the synthetic velocity–error relationship hold
   in the same direction and rough magnitude on real captured movement?
6. Phase-normalised gait curve comparison via `spm1d` if the running data
   supports it.

**Multiple comparisons:** the per-joint tests are exploratory and reported with
Holm–Bonferroni correction. The primary hypotheses H1–H3 are tested at the
whole-body aggregate level.

**Exclusions:** frames where a backend fails to return a pose are recorded as
detection failures and reported separately as a failure rate. They are not
imputed and not silently dropped, because detection failure at high velocity is
itself a finding.

## Other

**Existing data:** No error data exists at the time of registration. Prior work in
this repository produced mesh reconstructions and joint-angle extractions but
**no validated accuracy measurement of any kind**. Earlier accuracy figures that
appeared in project documents were unsubstantiated and have been retracted (see
`critical_analysis.md` and `docs/log/2026-07-26.md`).

**Known limitations, declared in advance.**
- Synthetic ground truth tests the *estimator*, not the full real-world capture
  chain — rendering does not reproduce every property of real sensor data.
- Motion blur is simulated by 8× temporal supersampling, an approximation of
  real rolling-shutter phone capture.
- Real-footage validation uses a single subject, so it demonstrates that the
  synthetic finding transfers, not that it generalises across body types.
- No comparison against marker-based laboratory motion capture is available.

**Code and data availability:** All analysis code, authored pose sequences, and
result CSVs will be committed to the public repository. Every figure must be
regenerable from committed data by a committed script.
