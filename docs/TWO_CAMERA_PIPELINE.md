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

Each measurement attempt gets a numbered output folder. A stick check measures
geometry. Marker agreement needs an independently read scale and real footage.
The [student checklist](PILOT_RECORDING_CHECKLIST.md) covers the recording order.

## 0. Set up a private take

From the repository root, install the CPU detector and create a private session
file alongside your recordings. These commands assume the example data root.
Use your own paths, take ID, video filenames and calibration records.

```bash
bash tools/bootstrap-linux.sh --pose
# For an NVIDIA machine use --cuda --pose and set pose.device to cuda.
cp -n .env.example .env.local
pilot_dir="$HOME/Videos/rvectr/2026-11-16/take1"
mkdir -p "$pilot_dir"
cp -n configs/session.example.json "$pilot_dir/session.json"
cp -n configs/pilot_annotations.example.csv "$pilot_dir/pilot_annotations.csv"
```

The example fields and times illustrate the format. Replace every example row
with an actual independent reading before analysis. Video names in the session
are relative to `RVECTR_DATA_ROOT`, calibration names to `RVECTR_CALIBRATION_DIR`
(default `<data root>/calibration`), and annotation names to the session JSON.
Set the standing interval and flash search windows to suit the actual take.
Use the same shell for the commands below.

## 1. Measure the board

Your board has **8 × 11 printed squares** (7 × 10 inner corners). Measure four
squares in a row with a ruler, divide by four, and do this along both
directions. Record the readings and ruler uncertainty. If the axes disagree beyond that uncertainty, reprint without stretching and repeat. Pass the verified square size as `--square-mm`; 70.7 below is only an example. Add an asymmetric physical mark at the border nearest the intended corner 0, and distinguish the +X and +Y directions.

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
numbering depends on that. The command saves `<output-stem>.corners.png`; open
each preview and check the circled zero corner and the `+X`/`+Y` arrows. They
must follow the same physical board corner and directions in every camera.
If the preview is wrong or the board is not fully detected, stop and repeat the
board clip/calibration instead of accepting a guessed axis.

**After this, do not touch the phones.** If one moves, redo step 4.

## 5. Check the geometry with a known length (before recording people)

Put a rigid stick with two marks a known distance apart (for example 50 cm) in
the squat area. Check it at **five positions**: near the middle, left and right
edges of the movement area, and near and far from the phones. At each position,
show the stick first upright, then sideways, then pointing towards and away from
the cameras. Keep both marks visible and note the position and direction. This
checks scale and axis errors across the working volume, not just one convenient
line.

Record both flashes in the stick take. Copy the session JSON to
`$pilot_dir/stick-session.json`, change its video names to the **stick** videos and
set `experiment.annotations` to null. Use the stick take's own sync record:

```bash
uv run --no-sync rvectr sync --config "$pilot_dir/stick-session.json" --out "$pilot_dir/stick-sync"
uv run --no-sync rvectr frames --config "$pilot_dir/stick-session.json" --time 4.0 \
  --sync "$pilot_dir/stick-sync/sync.json" --out "$pilot_dir/stick-frames"
```

Open the synchronized camera/time-named PNGs. Record the pixel
position of the same two physical marks in every camera; do not pick different
stick corners in different views. Save the two measured pixel locations per view in `$pilot_dir/points.json`. The coordinates below illustrate the format.

```json
{"points": {"A": {"cam1": [812, 1404], "cam2": [655, 1390]},
            "B": {"cam1": [1290, 1410], "cam2": [1102, 1377]}},
 "distances": [{"from": "A", "to": "B", "known_m": 0.5}]}
```

```bash
uv run --no-sync rvectr check-points --config "$pilot_dir/stick-session.json" --points "$pilot_dir/points.json" --out "$pilot_dir/stick-result.json"
```

Repeat for the five positions and directions. Use the same point names for the
same physical marks within each synchronized frame set. Compare measured with
known length and save every error, including failed/unreconstructed cases. This
is an independent check of scale, camera geometry and coordinate axes.

## 6. Record a take for the pilot comparison

Before the first take, mark the standing spot with a tape cross on the floor.
Stand on it at the start of every take and face the same way in every take.
The one-camera comparison (see "Comparing numbers of views") needs to know where
the person stands and which way the hips point.

Keep a **baseline reference rep and raised-target reps in the same take**. The
reference is the ordinary, comfortable squat to the unraised stool; the raised
stool reps are intentionally shallower. This gives every camera condition the
same reference without borrowing a reference from another take. Record the
actual added stool height for every attempt. Do not combine repeated takes into
one scoring list.

1. Start all phones.
2. Flash a light visible to both cameras: a phone torch switched on for about half a second.
3. Stand still for 3 seconds. This is the jitter measurement.
4. Do the baseline reference rep first, then the raised-target reps in the same
take. Mark which target height each attempt used in the notebook.
   Stand still for two seconds between reps: the software reads the standing
   height from that pause. When squatting to a target (a stool, a bar), touch
   it lightly and come straight back up.
5. Stand still, then flash the light again.
6. Stop both phones.

Check the sync on its own first:

```bash
uv run --no-sync rvectr sync --config "$pilot_dir/session.json" --out "$pilot_dir/sync"
```

Look at `$pilot_dir/sync/brightness.png`: the dashed lines must sit on the two
flashes in both cameras. If other light changes confuse it, set a `roi`
`[x, y, w, h]` around the torch for each camera in the config.

One usable flash gives an offset-only diagnostic. The annotated pilot requires
one distinct usable start and end flash in every view. Multiple rising pulses
in a window are ambiguous. Inspect the plot, crop the ROI or adjust the windows
and rerun. Two landmarks fit linear offset and drift; two fitted points provide
no independent residual measurement. The report gives per-endpoint sampling
uncertainty in seconds. A third independent landmark can check the mapping.

Ordinary presentation timestamps do not specify where exposure starts.
By default the tool uses brightness landmarks with timing uncertainty. For a
camera with independently known exposure duration and timestamp convention,
set e.g. `sync.exposures.cam1 = {"duration_s": 0.01, "pts_at": "start"}`.
Allowed conventions are `start`, `centre` and `end`. Use a measured duration,
which can differ from the frame period. The exposure model assumes a step
flash and linear integrated brightness. Auto-exposure, rolling shutter and
nonlinear drift can add errors beyond the reported sampling term.

## 7. Label the footage BEFORE looking at the software results

Before opening any software result, make an independent annotation list from
the videos. Give each rep a unique ID and record its start, lowest point and end
time on camera 1's video clock. Record one reference rep in this same take;
label each test rep `match`, `shallow`, `rejected` (a documented protocol
failure), or `unscorable` (the video cannot support a judgement). Keep rejected
and unscorable attempts in the list. For these rows only, leave an unknown
time blank. A row without a bottom time stays in the ledger and cannot be
paired to a detection. Record the measured added stool height in
`target_height_m`; the annotated descent time is the start-to-bottom interval.
Use `configs/pilot_annotations.example.csv` as the column template. Have two
readers annotate independently when possible; keep both readers' sheets and
record the reader ID and uncertainty estimate.

For a continuous comparison, read the **visible marker against a measured
vertical scale in its own plane**, as in the student checklist. Take independent
standing and bottom readings before opening software depth outputs. For a
moving marker in another view, export the corresponding frame for each time:

```bash
uv run --no-sync rvectr frames --config "$pilot_dir/session.json" --time 9.2 --sync "$pilot_dir/sync/sync.json" --out "$pilot_dir/marker-frames"
```

Record its depth and measurement uncertainty in metres. Save a blank value when
no defensible uncertainty is available; do not enter zero. Keep the video-based
class judgement independent from the software output. The fixed match rule is
depth no more than 3 cm shallower than the reference; the 1 cm band around that
boundary is reported as borderline. Set and freeze these thresholds before
looking at results. If marker and reader depth uncertainties are known, the
borderline band is widened to twice their combined uncertainty. The
per-condition predicted reference comes from that condition's detection of the
same annotated reference rep. The report retains each reader's label. If the
marker-based class disagrees with the label, their disagreement and whether it
falls outside the borderline band are recorded. A usable marker-based class is
the independent comparison target when it exists.

Put the CSV path in `experiment.annotations` in the session config, or pass
`--annotations path/to/annotations.csv` to `rvectr run`. The run matches each
condition to the same timed annotation list one-to-one, by bottom time (default
window 0.5 s). Reference reps are retained in the ledger but excluded from
classification denominators. A condition's denominator is the number of
matched, classifiable test reps; missed, extra, rejected, unscorable and model
unclear cases are reported separately. Marker depth errors use only rows with a
measured marker depth; unknown uncertainty remains unknown.

## 8. Run

```bash
uv run --no-sync rvectr run --config "$pilot_dir/session.json"
# score each camera subset against the independent timed pilot annotations:
uv run --no-sync rvectr run --config "$pilot_dir/session.json" --annotations "$pilot_dir/pilot_annotations.csv"
# change only squat/triangulation settings? reuse the slow 2D step:
uv run --no-sync rvectr run --config "$pilot_dir/session.json" --keypoints-from outputs/V1.1.12
```

Only reuse a cache from the original videos with matching camera IDs, orientation,
frame indices, presentation timestamps, stride, edge margin and detector settings.
Each new .npz carries its source digest, the detector identity and generation code
fingerprint. The balanced detector checks the recorded weight hashes against the measured ONNX files. For reuse with another preset, hash the two ONNX files from that preset's original model archives and set `pose.weight_sha256` (keys `det` and `pose`) to those digests. A pin may be supplied after inference. The locked ONNX Runtime version and actual inference device are also checked. If GPU inference fell back to CPU, set the intended device explicitly and regenerate. Older caches lack this evidence. To regenerate, run the same command
without `--keypoints-from`. A synthetic projection cache must identify its source.

The numbered run folder contains the following files.

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
  A long resting interval can use the median level of its observed frames.
  Both fits require observed movement into and back out of the dip. `bottom_model` in `reps_*.csv` says which
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
- **Unclear** = fewer than `min_coverage` (85 %) of the rep's expected elapsed frame intervals had both
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
- **Filter effect** = filtered depth − raw depth per rep. Report differences by actual descent duration; filter changes can reflect movement or noise.
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
  from the other cameras. Errors in that borrowed standing estimate also affect this result.
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
| `views_experiment.csv`, `views_experiment.json` | same independent annotation IDs for every condition, one-to-one time matches, marker depth errors, fixed-tolerance decisions, uncertainty and explicit missed/extra/rejected/unscorable/failed counts |

For pilot scores every view uses the configured primary trace and the same
annotation list. The report retains a row for every attempt, unmatched detections
and diagnostic depths for rejected attempts. The marker error summary excludes
rejected, unscorable and missing depths. Classification agreement excludes the
reference. Read its numerator and denominator alongside the full attempted tally.
The point for an accepted depth with unknown uncertainty has no error bar.

The pilot's CSV files identify the attempt and camera combination. When the
intended reference is missed or rejected, its row records the failure and the
condition cannot make any reference-relative decisions. A different attempt
cannot take its place. The raw and filtered tables record their own matched
reference from the same annotation sheet. Independent readings of a marker and
the stool setting have separate columns.

Without timed annotations, older configs can produce a diagnostic comparison
against the numbered all-view detections. This comparison has no independent
attempt denominator. Use the annotation workflow for accuracy or agreement.

## Limits

The tracker estimates the left and right internal hip joints. A skin or clothing
marker can shift relative to their midpoint. Report differences against that
marker, reader uncertainty and any out-of-plane movement. A second triangulated
marker can diagnose geometry but shares the cameras and calibration with the
software estimate. Low reprojection error alone cannot establish anatomical
accuracy. All published verification so far is synthetic.
