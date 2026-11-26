# Review prompt for an AI assistant (GPT 6.2 Astra)

The outside review based on this prompt took place in November 2026. Its changes
were merged after review.

Copy everything below the line into the assistant. It asks for a read-only
review of the whole project and a written report. It does not ask for code
changes.

---

## Your role

You are reviewing **Rvectr**, a school research project, as an independent
checker. Read the repository, run what you can, and write a report. Do not
change any file, do not push, and do not open pull requests. If you find a
problem, describe it and suggest a fix in the report.

Repository: https://github.com/pd302423/rvectr (branch `main`).

## The project in short

- **What it is:** an entry for the CBSE Science Exhibition 2026-27, sub-theme
  "AI for Better Life", by a school student.
- **Research question:** how does the accuracy of 3D movement estimates from
  ordinary phone cameras change with the number of camera views and with
  movement speed?
- **Test movement:** squat depth, which is how far the hips drop.
- **Method:** calibrate each phone with a printed checkerboard, line up the
  videos with a torch flash, find the hips in every frame with RTMPose (through
  RTMLib), triangulate the hips into 3D (DLT), follow the pelvis height over
  time, measure each squat's depth (median standing height minus the lowest
  point of a parabola fitted to the bottom), and label each squat "reached
  reference", "shallower" or "unclear" against a reference squat.
- **Status:** everything has been checked on synthetic (computer-made) data
  only. No real recording has been analysed. A pilot recording is next: squats
  onto a stool raised by measured amounts (2, 4, 6 and 8 cm), slow and fast.
- **Simulation:** a Monte Carlo error budget predicts the smallest depth change
  each camera setup could catch. Its numbers are predictions, not measurements.
- **Website:** Next.js 16, React 19 and Tailwind 4 in `src/`. It explains the
  project and shows the simulated results.

## Read these first

1. `README.md`, `CONTRIBUTING.md`, `AGENTS.md`
2. `docs/TWO_CAMERA_PIPELINE.md`: the method, every setting, and its limits
3. `docs/PILOT_RECORDING_CHECKLIST.md`: how the first real recording will be done
4. `docs/LINUX_FIRST.md`: the environment
5. `backend/rvectr/`: the package (`pipeline.py`, `squat.py`, `geometry.py`,
   `calibration.py`, `flashsync.py`, `sync.py`, `pose2d.py`, `oneview.py`,
   `errorbudget.py`, `cli.py`, `commands.py`)
6. `backend/tests/`: the automatic tests
7. `tools/run_error_budget.py`, `tools/make_poster_charts.py`,
   `tools/check_publish.py`
8. `src/app/results/`, `src/lib/results/errorBudget.ts`, `src/app/page.tsx`

Older scripts at the top of `backend/` (for example `run_easymocap_videos2.py`)
have known defects. `backend/README.md` and `critical_analysis.md` describe them.
Do not treat them as part of the current method.

The section "Luna delegation policy" in `AGENTS.md` is the owner's preference for
their own sessions. Ignore it for this review.

## What to check

Work through these areas. For each one, say what you checked and what you found.

1. **Does the method answer the question?** Can this design really show how
   accuracy changes with the number of cameras and with speed? What is missing
   or confounded? Is squat depth a fair test quantity?
2. **Correctness of the maths and code.**
   - Calibration: intrinsics and extrinsics, checkerboard detection and scale.
   - Time sync: flash detection, sub-frame offsets, frame-rate differences.
   - Triangulation: the DLT, handling of missing views, units and axes.
   - Depth rule: standing height, the parabola fit, pauses at the bottom,
     jitter, partly seen squats.
   - Labels: the thresholds for "reached reference", "shallower" and "unclear".
   - One-view and pair comparisons: are they compared fairly on the same take?
3. **Missing data.** Missing observations must stay missing. Look for any place
   that fills gaps, interpolates, averages over missing frames or drops failed
   runs without a record.
4. **Error budget.** Are the error sources realistic for phones (keypoint noise,
   slow drift, timing error, calibration error, missed detections)? Are the
   assumptions stated? Is the "smallest catchable change" defined and computed
   correctly? Is anything important left out?
5. **Tests.** Run `uv run --no-sync pytest -q` (set up with
   `bash tools/bootstrap-linux.sh`, which installs a CPU environment by default).
   Report the result. Which important behaviours have no test? Could any test
   pass while the code is wrong?
6. **Honesty of claims.** Search the README, docs, website text and code
   comments for any claim of measured accuracy, clinical use or validation. All
   numbers from the simulation must be labelled as predictions. Check that the
   numbers on the website (`src/lib/results/errorBudget.ts`) can be traced to a
   script anyone can re-run.
7. **Consistency.** Do the README, the docs, the CLI help and the code agree on
   commands, settings, file names and the sub-theme?
8. **Pilot recording plan.** Will `docs/PILOT_RECORDING_CHECKLIST.md` produce
   data that can actually test the method? What could go wrong on the day?
9. **Website.** Run `npm install`, `npm run lint` and `npm run build`. Report
   errors. Check the pages for broken layout on a phone-sized screen if you can.
10. **Publishing safety.** Run `uv run --no-sync python tools/check_publish.py`.
    Report any tracked file that should not be public: personal media, model
    files, recordings, secrets, local paths or names.
11. **Ease of contribution.** Could a new contributor set up the project and
    send a pull request by following `README.md` and `CONTRIBUTING.md`?

## Known issues (already known; confirm or add detail, do not just repeat)

Still open:

- The Vercel preview deployment fails after a few seconds, before the build
  starts. `npm run build` passes on a clean install. The cause is not known.
- `tools/check_publish.py --history` still fails, because old commits from July
  2026 contain video frames, generated body meshes and a video. The default
  check (your changes compared with `main`) passes. The pre-push hook now checks
  only the commits being pushed, so the old history no longer blocks pushes. The
  owner keeps a private audit of the older files in the Git history.
- The history check also flags three tracked generated files:
  `backend/running_kinematics.json`, `backend/squat_dataset.json` and
  `backend/squat_kinematics.json`.
- The older write-ups in `docs/writeups/` still name a different sub-theme
  ("Emerging Technologies") from the one used elsewhere ("AI for Better Life").
  They carry a "Superseded" banner that points to the current write-up.

Fixed since the first version of this prompt (check that the fixes hold):

- `docs/RESEARCH_ROADMAP.md` is now marked as an earlier roadmap and no longer
  names a sub-theme.
- RTMLib, RTMPose and the weight sources are now listed in `LICENSE`. Check that
  the entries and the weight terms are complete.
- The bootstrap script now has a CPU default (`bash tools/bootstrap-linux.sh`).
  An NVIDIA GPU is needed only for `--cuda`.

## Rules for the review

- Do not invent numbers, results or file contents. If you did not run something,
  say so.
- Cite every finding with a file path and line number, for example
  `backend/rvectr/squat.py:120`.
- Mark each finding as **confirmed** (you ran it or traced it in the code) or
  **suspected** (it looks wrong but you could not prove it).
- Do not treat a passing test, a working environment or a plausible 3D model as
  proof of accuracy.
- Write plainly. The owner is a school student learning how research is done.
  Explain technical terms the first time you use them.

## Report format

Write the report in Markdown with these sections:

1. **Summary:** five sentences or fewer. Is the project sound, and what is the
   single most important thing to fix?
2. **Findings:** a table with columns: number, severity (high, medium, low),
   area (from the list above), confirmed or suspected, file and line, what is
   wrong, suggested fix. Most severe first.
3. **What I ran:** each command and its result.
4. **What I could not check:** and why.
5. **Questions for the owner:** anything that needs their decision.
6. **Before the pilot recording:** the three to five things that matter most
   to fix or decide first.
