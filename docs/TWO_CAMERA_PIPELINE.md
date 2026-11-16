# Two-camera squat pipeline

This pipeline measures **squat depth** as the drop of the pelvis (the midpoint of
the two hip keypoints) along the true vertical, using two calibrated,
synchronized phones. It implements the procedure in the CBSE report
("R Vector 3D Motion Capture for Comparing Squat Repetitions").

```
board videos ──► calibrate-intrinsics (per phone) ──► calibrate-extrinsics (per phone, same board)
                                                                 │
exercise videos ──► sync (light pulse) ──► 2D keypoints (RTMPose) ──► triangulate ──► pelvis height
                                                                                         │
                                       reps, depth, reference comparison, jitter ◄───────┘
```

Everything is written to a numbered run folder, `outputs/V1.1.N`.
**The software never declares itself accurate.** You get accuracy only from
the checks in steps 5 and 7 below.

## 0. One-time setup

```bash
uv sync --frozen --extra pose          # RTMPose via RTMLib (CPU works)
uv sync --frozen --extra cuda --extra pose   # optional: ~3 GB, lets pose detection use the GPU
cp .env.example .env.local             # then set RVECTR_DATA_ROOT to your recordings folder
```

Put recordings under `RVECTR_DATA_ROOT` and calibration files under
`RVECTR_DATA_ROOT/calibration` (or set `RVECTR_CALIBRATION_DIR`).

## 1. Measure the board

Your board has **8 × 11 printed squares** (7 × 10 inner corners). Measure four
squares in a row with a ruler, divide by four, and do this along both
directions. That number in millimetres is `--square-mm`. It sets the scale of
every result, so do not guess it from the paper size.

## 2. Phone settings (same for calibration and exercise)

- Rear main camera, 1×, 1080p at 60 fps if possible, the same orientation for every video.
- Turn off stabilisation, auto lens switching and auto framing. Lock focus and exposure if the phone allows it.
- Whole body, from standing to the bottom of the squat, stays inside the frame
  with space around it. Keypoints on the frame edge are thrown away.

## 3. Lens calibration: once per phone and setting

Record about 60 seconds per phone: hold the board in the centre, edges and
corners of the picture, tilted left/right/up/down, near and far. Pause briefly
at each place so the corners are sharp.

```bash
uv run --no-sync rvectr calibrate-intrinsics --camera-id cam1 \
  --video ~/Videos/rvectr/2026-11-16/cam1_lens.mp4 --square-mm 70.7 \
  --out ~/Videos/rvectr/calibration/2026-11-16/cam1_intrinsics.json
```

It picks up to 30 varied sharp views, keeps 20 % aside to test the result, and
prints `PASSED` or `FAILED` with the reason. The held-out error should be well
under 1 px. Repeat for `cam2`.

## 4. Camera position: every time the phones are placed

Mount both phones in their final positions. Start recording on both. Stand the
board **upright and level** (use a spirit level) in the middle of the squat
area, facing both cameras, and hold it still for 3–5 seconds. Both phones must
see the whole board at the same time.

```bash
uv run --no-sync rvectr calibrate-extrinsics \
  --intrinsics ~/Videos/rvectr/calibration/2026-11-16/cam1_intrinsics.json \
  --video ~/Videos/rvectr/2026-11-16/board_cam1.mp4 --start 2 --end 5 \
  --board-frame-id 2026-11-16_setupA --square-mm 70.7 --same-recording-mode \
  --out ~/Videos/rvectr/calibration/2026-11-16/cam1_camera.json
```

`--start/--end` are seconds into **that phone's** video where the board is
still. Use the same `--board-frame-id` for both phones. Pass
`--same-recording-mode` only after checking that the exercise videos use
exactly the same settings; runs refuse calibrations without it. The board must
stay level and must not be rotated about 45° in the picture, because the corner
numbering depends on that.

**After this, do not touch the phones.** If one moves, redo step 4.

## 5. Check the geometry with a known length (before recording people)

Put a rigid stick with two marks a known distance apart (for example 50 cm) in
the squat area. Record it in both phones. Save a frame from each:

```bash
uv run --no-sync rvectr frames --config configs/session.json --time 4.0 --out frames/
```

Open the PNGs in any image viewer that shows pixel coordinates. Note the pixel
position of each mark in both images and write `points.json`:

```json
{"points": {"A": {"cam1": [812, 1404], "cam2": [655, 1390]},
            "B": {"cam1": [1290, 1410], "cam2": [1102, 1377]}},
 "distances": [{"from": "A", "to": "B", "known_m": 0.5}]}
```

```bash
uv run --no-sync rvectr check-points --config configs/session.json --points points.json
```

Repeat with the stick in several places and orientations. Record the errors.
This is the independent check of scale and camera geometry.

## 6. Record a take

Before the first take, mark the standing spot with a tape cross on the floor.
Stand on it at the start of every take and face the same way in every take.
The one-camera comparison (see "Comparing numbers of views") needs to know where
the person stands and which way the hips point.

1. Start both phones.
2. Flash a light visible to both cameras: a phone torch switched on for about half a second.
3. Stand still for 3 seconds. This is the jitter measurement.
4. Do the reps. Rep 1 is the participant's chosen reference depth.
   Stand still for two seconds between reps: the software reads the standing
   height from that pause. When squatting to a target (a stool, a bar), touch
   it lightly and come straight back up.
5. Stand still, then flash the light again.
6. Stop both phones.

Check the sync on its own first:

```bash
uv run --no-sync rvectr sync --config configs/session.json --out sync_check/
```

Look at `sync_check/brightness.png`: the dashed lines must sit on the two
flashes in both cameras. If other light changes confuse it, set a `roi`
`[x, y, w, h]` around the torch for each camera in the config.

## 7. Label the footage BEFORE looking at the software results

For each rep, decide from the video (marked footage, or the pelvis marker)
whether it **matches** the reference depth, is **shallow**, or is **unclear**.
Save it as a CSV like `configs/labels.example.csv` and point `"labels"` in the
session config at it. Making labels after seeing the software output would bias
the comparison.

## 8. Run

```bash
uv run --no-sync rvectr run --config configs/session.json
# change only squat/triangulation settings? reuse the slow 2D step:
uv run --no-sync rvectr run --config configs/session.json --keypoints-from outputs/V1.1.12
```

The run folder contains:

| File | What it is |
|---|---|
| `report.json` | everything: sync, coverage, jitter, reps, outcomes, comparison with labels |
| `depth_trace.png` | pelvis height over time, reps shaded green (reached), red (shallower), grey (unclear) |
| `reps_raw.csv`, `reps_filtered.csv` | one row per rep: depth, descent time, coverage, outcome |
| `pelvis_trace.csv` | height per frame, raw and filtered, with hip reprojection error |
| `points3d.npz` | all 17 triangulated joints per frame |
| `sync/` | pulse detection plot and offsets |
| `keypoints2d/` | 2D detections per camera (reusable) |

### How the numbers are defined

- **Standing height** = the median pelvis height over the second of standing
  still that ends half a second before the rep begins (never reaching back into
  the previous rep). The median ignores the odd wild value. If that stretch has
  too few observed frames, the whole pause before the rep is used; if even that
  is too short, the standing level of the whole recording is used and the rep
  is marked `standing_source` = `session` (it then has no plus-or-minus).
- **Bottom** = the lowest point of a smooth curve (a parabola) fitted to the
  real frames around the lowest part of the rep. Near the lowest point the
  pelvis moves like a ball at the top of its flight, so its height against time
  is a parabola, and using many frames averages out the noise. The single
  lowest frame is not used: it is the frame with the luckiest noise, so it
  reads too deep. If the person rests at the bottom, the height is flat there.
  In simulation most such reps are still read with the parabola and come out
  about 1 mm too deep; when the parabola does not fit at all, the bottom is the
  median level of the resting frames. `bottom_model` in `reps_*.csv` says which
  was used: `parabola`, `plateau` (rested), or `none` (the bottom was not seen
  well enough, so the rep is unclear). A recording that stops while the person
  is still at the lowest point gives `none`, because the bottom may not have
  been reached yet.
- **Depth** = standing height − bottom height.
- **Plus-or-minus** (`depth_se_m` in `reps_*.csv`) = the typical error of the
  depth, worked out from the scatter of the frames used. `difference_se_m` is
  the same for the difference from the reference rep. It assumes the error of
  each frame is independent of the next. If errors drift slowly (a slowly
  wandering pose detection), the real error is bigger, so the plus-or-minus is
  a lower bound.
- **Reached reference** = depth ≥ reference depth − `tolerance_m` (default 3 cm).
  Set the tolerance from a pilot clip, then keep it fixed.
- **Borderline** = within `borderline_m` of that line, or within twice the
  plus-or-minus of the difference from the reference rep, whichever is larger.
- **Unclear** = fewer than `min_coverage` (85 %) of the rep's frames had both
  hips reconstructed, or the bottom was not seen well enough: fewer than 5
  real frames around the lowest point, a gap of more than 0.1 s between them,
  or frames missing on one side so that the lowest point is not inside them.
  Missing data is never filled in.
- **Jitter** = spread of the pelvis around its median while standing still
  (`standing_window_s`), for raw and filtered traces. The vertical spread is
  split in two:
  `vertical_fast_sd_m` is the noise that changes from one frame to the next
  (worked out from the differences between neighbouring frames), and
  `vertical_slow_sd_m` is what is left, slow drift of the detected pose that
  stays almost the same for a second or so. They matter because fast noise
  averages out when many frames are used for the standing height and the
  bottom, but slow drift does not: it shifts the whole standing level or bottom
  together, so it sets how small a depth difference can be detected.
- **Filter effect** = filtered depth − raw depth per rep. A large change on the
  faster reps means the filter is hiding real depth.
- **False pass** = software said reached, footage said shallow.
  **False flag** = software said shallower, footage said match.

## Comparing numbers of views

The research question is how the accuracy of the depth changes with the number
of camera views. So after the normal measurement the software measures the
**same recording again** with fewer cameras. It does not detect the body again:
it reuses the 2D keypoints already found, and it uses the same squat settings
and the same reference rep. Each way of measuring is called a **condition**:

- **all views**: every camera together. This is the main result above.
- **two views** (only when there are three or more cameras): every pair of cameras, triangulated on their own.
- **one view, fixed distance** and **one view, movement plane**: each camera alone, in two versions (below).

With two cameras that makes five conditions (two per camera, plus all views);
with three cameras it makes ten (six one-view, three pairs, all views).

### What one camera can and cannot do

One camera sees a direction, not a distance: each pixel is a straight line
(a ray) running out from the camera. Two cameras give two rays that cross at
the point. One camera needs an extra assumption: *the pelvis moves in a flat,
vertical plane*. The point is then where the ray meets that plane. If the
person does not really stay in that plane, the depth is wrong. Both versions
use a vertical plane through the standing spot:

- **Fixed distance** uses the plane that faces the camera. It assumes the person
  never moves towards or away from the camera, which is what a simple
  one-camera measurement assumes. If the hips move backwards while the camera
  looks at them from the side-front, the depth is read too short; if they move
  towards the camera, too long. A camera exactly side-on to the movement is not affected.
- **Movement plane** uses the plane the person moves in: forwards, backwards, up
  and down. Its direction comes from the hip line (from the left hip to the
  right hip). It assumes no sideways movement. It copes with moving backwards,
  but a wrongly measured hip line causes an error, and it cannot be used by a
  camera that looks straight along the movement (the ray then runs along the
  plane and the point is marked missing).

### Where the plane comes from, and fairness

The plane needs the standing spot and the hip line, in the calibration frame.

- **`plane_source = "multiview_standing"`** (default): both are taken from the
  all-cameras result while the person stands still (median pelvis position, and
  median left-hip-to-right-hip direction). **This is not a fair test of one
  camera alone**, because the one-camera conditions borrow set-up information
  from the other cameras. It tells you the best a single camera could do with
  perfect knowledge of where the person stands.
- **`plane_source = "measured"`**: give both in the session config, measured
  independently of the cameras (for example the tape cross on the floor and the
  direction the person faces, converted to the calibration frame):

```json
"views": {"compare": true, "standing_point_m": [0.30, -0.95, 0.50], "hip_line": [1, 0, 0]}
```

  Then the one-camera conditions use no information from the other cameras. Give
  both values or neither. `"compare": false` switches the comparison off.

The standing spot is the pelvis position (so it is at hip height, not on the floor).

### The files

| File | What it is |
|---|---|
| `views_comparison.csv` | one row per rep per condition |
| `views_summary.json` | one entry per condition: reps found, unclear, standing jitter (total, fast, slow), the averages below, `plane_source` and one sentence saying what the condition assumes |
| `views_depth.png` | depth of every rep for every condition, with plus-or-minus bars |

Reading `views_comparison.csv`: `condition` and `cameras` say what was used and
`model` how (`triangulation`, `fixed_distance` or `movement_plane`). `rep` is
numbered as in the all-views result: a rep of another condition is the same rep
if its bottom is within 0.5 s of that rep's bottom. A rep that a condition did
not find has `outcome` = `not_found` and empty numbers; reps found that match no
all-views rep are only counted in the summary. The other columns are as in
`reps_raw.csv`, with one addition: **`depth_minus_all_views_m`** is this
condition's depth minus the all-views depth for the same rep. A value near zero
means that fewer views did as well. The summary gives its mean (a steady bias)
and standard deviation (scatter), and the same for the difference from the
reference rep (rep 1, which is zero by definition, is left out of that one).
A condition that agrees with all views is not necessarily right: all views is
the comparison, not the truth.

## What this does not tell you

- The hip keypoint is the detector's estimate of the hip joint, inside the body.
  A marker on clothing moves differently. Compare the two by marking the
  pelvis marker at the standing and bottom frames with `frames` +
  `check-points`, and report the difference. Do not treat either one as the truth.
- Low reprojection error means the two cameras agree. It does not prove the
  point is anatomically right.
- The light-pulse sync is good to roughly a quarter to a half frame. Fast
  movement makes a residual timing error matter more. The tests show that a
  two-frame error clearly inflates reprojection error, so watch that number.
- Every check in `backend/tests/test_two_camera_pipeline.py` uses synthetic data.
  It proves the software recovers known answers, not that phones are accurate.
