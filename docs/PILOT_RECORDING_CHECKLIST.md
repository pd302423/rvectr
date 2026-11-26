# Pilot recording checklist

Read this on your phone while you film. Tick each box as you go.

**Time.** Plan about 2 hours in all: about 1 hour to set up, calibrate and
check the stick, about 30 minutes of filming, and about 30 minutes to copy the
files and write your readings. This is a first guess. Write down how long it
really took.

## What the pilot is for

This is a short first test with real phones. So far the software has only been
tried on computer-made data. We want to see whether it can follow your hips and
measure squat depth, and where it goes wrong.

Two rules for the whole day:

- Give each continuous recording (all phones together) one take ID, such as
  `take1`. Keep the notebook, the original videos, any pictures taken from the
  videos and the software outputs together, sorted by take ID.
- The numbers in the example files in this repository are only examples. They
  are not results. Replace them with what you really see.

## Safety (read first)

- [ ] Film only yourself. Do not film classmates or anyone else until your
  school and guide teacher have approved it.
- [ ] Warm up first.
- [ ] Stop at once if anything hurts.
- [ ] Keep the floor clear. Keep the stool steady and the boards from sliding.

## 1. Before the day

**Pack these.**

- [ ] Two phones on tripods or something very stable (a third phone only if it
  can film the same attempts as the other two).
- [ ] A laptop with the Rvectr software installed (see the README).
- [ ] The printed checkerboard, stuck flat on a stiff board.
- [ ] A ruler.
- [ ] A torch. A phone torch is fine, but use a phone that is not one of the
  filming phones.
- [ ] A stick with two marks a known distance apart (a rigid stick).
- [ ] A stool.
- [ ] A few flat boards or books to raise the stool.
- [ ] A vertical ruler or measured tape (the scale), and a small visible marker
  such as a coloured sticker.
- [ ] A spirit level, if you have one.
- [ ] Tape, for a cross on the floor.
- [ ] A notebook and pen.

**Measure and prepare.**

- [ ] Measure four squares of the board in a row along its long side. Divide by
  four. Write the result in millimetres.
- [ ] Do the same along the short side. Write it in millimetres too.
- [ ] Write down the smallest step on your ruler.
- [ ] If the two square sizes differ by more than the ruler can explain,
  reprint the board at full size with no stretching, and measure again. The
  software takes one square size, so the two directions must agree.
- [ ] Stick a small mark that is not symmetric (for example tape in an L shape)
  on the board's border, next to the corner you want the software to call
  corner 0.
- [ ] Show on the board which direction is along the long side and which is
  along the short side. Use arrows drawn on the border, or two more pieces of
  tape.
- [ ] Measure the distance between the two marks on the stick. Write it in
  centimetres.
- [ ] With your supervising adult, choose stool settings that are stable and
  comfortable. For example, raise the stool by about 2, 4, 6 and 8 cm.
- [ ] Measure the seat height with no boards. Measure it again with each board
  setting. Write every height down.
- [ ] Work out each difference from the no-board height, in metres (4 cm is
  0.04). This is what goes in the `target_height_m` column.
- [ ] Copy `configs/pilot_annotations.example.csv` to a private folder and name
  the copy `pilot_annotations.csv`. This is your attempt sheet. You will add one
  row for every attempt, and replace the example rows.
- [ ] Charge the phones and free up storage (1080p at 60 frames per second makes
  big files).

## 2. Setup on the day

**Phone settings. Use the same on every phone.**

- [ ] Use the rear main camera at 1x, with no zoom.
- [ ] Choose 1080p at 60 frames per second (fps) if the phone allows it.
- [ ] Hold every phone upright (portrait). Use the same way up for every video.
- [ ] Turn off stabilisation, automatic lens switching and automatic framing.
- [ ] Lock focus and exposure if the phone lets you.
- [ ] After you film the board, do not change the lens or the mode.

**The room.**

- [ ] Use steady, bright light.
- [ ] Wear fitted clothes so your hips can be seen.
- [ ] Put a tape cross on the floor where you will stand.
- [ ] Decide which way you face, and face that way in every take.
- [ ] Stick the visible marker on snug clothing, at the side of your pelvis.
- [ ] Stand a vertical ruler or measured tape next to the marker, at the same
  distance from the side camera as the marker.
- [ ] Check that the side camera will see the scale face-on, with the marker and
  at least two scale marks easy to read, both standing and at the bottom of the
  squat. (A scale on a faraway wall gives a different picture size, so it does
  not work.)
- [ ] Take a photo or draw a sketch of this arrangement. Keep it private.

**Camera places.** Measure angles from the direction you face. 0 degrees is
straight in front of you. 90 degrees is exactly beside you.

- [ ] Camera 1 (the side camera): at 90 degrees, so it sees you from the side.
- [ ] Camera 2: at 45 degrees, in front of you and on the same side as camera 1.
- [ ] Camera 3 (optional): at 45 degrees on your other side, the mirror of
  camera 2.
- [ ] Put every camera about 3 m from the floor cross, with the lens about 1 m
  above the floor and the phone level.
- [ ] Write down, for each camera: its ID (cam1, cam2, cam3), the angle,
  distance and lens height you really measured, the phone model, the lens,
  the resolution, the way up, and the frame rate.
- [ ] Write down any difference from the layout above. (The computer simulation
  used exactly this layout.)
- [ ] Do one slow practice squat. Check that you and the scale stay inside
  every phone's picture the whole time, with space around you, and that both
  hips are always visible.

## 3. Calibration

Calibration means filming the board so the software learns each phone's lens
and where each phone stands.

**Lens clips. Do these before you fix the phones in place.**

- [ ] Phone 1, about 60 seconds: hold the board in the centre, at the edges and
  in the corners of the picture. Tilt it left, right, up and down. Hold it near
  and far. Pause a moment at each place so the picture is sharp. Name it for the
  phone (`cam1_lens.mp4`).
- [ ] Phone 2, about 60 seconds: do the same (`cam2_lens.mp4`).
- [ ] Phone 3, if used: do the same (`cam3_lens.mp4`).
- [ ] Run the lens calibration command from the [pipeline guide](TWO_CAMERA_PIPELINE.md)
  (section 3) for each phone.
- [ ] Check that each result says `PASSED`. If it says `FAILED`, film that
  phone's lens clip again.

**Camera positions.**

- [ ] Fix the phones at the places you measured. After this, do not touch them
  again.
- [ ] Stand the board upright and level in the middle of the squat area, facing
  the phones. Use the spirit level if you have one. Do not turn it diagonally.
- [ ] Turn the board so the side with your marks is visible to every phone.
- [ ] Start all phones recording.
- [ ] Write down the time you started each phone.
- [ ] Hold the board still for 3 to 5 seconds. Every phone must see the whole
  board.
- [ ] Write down the seconds in each video where the board is still.
- [ ] Stop all phones. Name the clips for the phones (`board_cam1.mp4`,
  `board_cam2.mp4`).
- [ ] Run the camera-position command from the pipeline guide (section 4) for
  each phone. Use the same board ID for every phone.
- [ ] Open the saved picture for each phone (it ends in `.corners.png`).
- [ ] Check that the circle (corner 0) and the two arrows (long side and short
  side) sit on the same real corner and edges as your physical marks, in every
  phone. A small error number does not prove the corner is the right one.
- [ ] If any phone disagrees, or a phone has moved, film the still-board clip
  again.

**Stick check, before you record a person.**

- [ ] Start all phones. Flash the torch for about half a second where every phone
  sees it.
- [ ] Put the stick in the middle of the squat area. Keep both marks visible.
- [ ] Hold it still for about 10 seconds: upright, then sideways, then pointing
  towards the phones, then pointing away.
- [ ] Repeat at the left edge, the right edge, a place near the phones and a place
  far from the phones.
- [ ] Write down the place and direction of each one.
- [ ] Flash the torch again, then stop all phones.
- [ ] Run the stick check from the pipeline guide (section 5) for each place and
  direction.
- [ ] Write down the software's length and the real length for each one. Write the
  difference with a sign (+ means too long, - means too short). Keep every
  failure too.
- [ ] If a result is far off, find out why before you record a person.

## 4. Recording

Do the same experiment at both speeds. Use the same raised stool heights at
both speeds.

- [ ] Plan the blocks. In each block, change the order of the stool heights (for
  example low then high, and in the next block high then low).
- [ ] Change which speed goes first in each repeat block, so one speed is not
  always done when you are fresh or tired.
- [ ] Controlled pace: about 2 seconds down and 2 seconds up. Fast pace: under
  1 second down. These are targets. The simulation used 2.0 and 0.8 seconds
  down.
- [ ] Stand on the floor cross and face the same way as in every take.

**Start of each take.**

- [ ] Start all phones.
- [ ] Say or write the take ID.
- [ ] Flash the torch for about half a second where every phone sees it.
- [ ] Stand still on the cross for about 10 seconds. The software needs the part
  of the video named in your session file (the example file uses seconds 3 to
  6).

**During each take. Keep it one continuous recording.**

- [ ] Do the baseline attempt first. This is a normal, comfortable squat down to
  the stool with no boards. Mark it as the baseline (the reference) on your
  attempt sheet.
- [ ] Then do the test attempts at the raised heights you chose, about 3 at
  each height. Do some more baseline attempts as well. They show how much two
  attempts at the same depth differ.
- [ ] Stand still and upright for about 2 seconds between attempts.
- [ ] Touch the stool lightly and come straight back up.
- [ ] Say or write each attempt's ID and stool height as you go.
- [ ] Never move a camera to change the stool.
- [ ] Add a row to the attempt sheet for every attempt, including slips,
  interrupted attempts and misses. Never delete a row.

**End of each take.**

- [ ] Stand still, then flash the torch again.
- [ ] Stop all phones.
- [ ] Write notes on any problem in this take.
- [ ] Rest before the next take.

## 5. Afterwards

**Copy and keep the videos.**

- [ ] Copy every video to the computer by USB cable. On the phone, choose "File
  transfer" when you plug it in.
- [ ] Keep one folder for the day, named with the date (for example
  `2026-11-16`). Put each take in its own folder (for example `take1`) with the
  files named `cam1.mp4`, `cam2.mp4`. Keep the other clips as `cam1_lens.mp4`,
  `board_cam1.mp4` and so on.
- [ ] Do not edit or trim any video.
- [ ] Do not delete anything from the phones until every file is copied, plays
  all the way through and has a backup.
- [ ] Keep the videos, pictures, notebook and attempt sheet private. Do not put
  them in the public repository.

**Read the scale first. Do not open any software result yet.**

Take every reading from the videos and the scale only, never from the
software's 3D result.

- [ ] Run the sync command. It lines up the clocks and shows no depth results.
- [ ] Open `brightness.png`. Check that the dashed lines sit on the two flashes in
  every camera.
- [ ] Run the `frames` command to save a picture from every camera at a time you
  choose. Use it to read the scale. Replace the paths and the example time (9.2)
  with your own.

```bash
uv run --no-sync rvectr sync --config /path/to/session.json --out /path/to/sync
uv run --no-sync rvectr frames --config /path/to/session.json --sync /path/to/sync/sync.json --time 9.2 --out /path/to/marker
```

- [ ] On camera 1's video time, write the start, bottom and end time of every
  attempt on the attempt sheet. If you pause at the bottom, use the middle of
  the lowest steady stretch.
- [ ] Fill in the baseline row first.
- [ ] Write how unsure each time is (`reader_uncertainty_s`, in seconds). Think
  about the gap between video frames, blurred edges and how hard the bottom was
  to pick.
- [ ] Find the standing frame of the attempt. Read the marker's centre against
  the two nearest scale marks. Estimate between the marks if you need to. Write
  down this height and the smallest step on the scale.
- [ ] Do the same in the bottom frame.
- [ ] Work out the depth: standing height minus bottom height. Change it to
  metres (centimetres divided by 100). Write it in `marker_depth_m`.
- [ ] If the scale is filmed by a different phone from camera 1, change its
  times to camera 1's clock using the flash results from the sync step.
- [ ] Write how unsure the depth reading is in metres: `marker_uncertainty_m`
  for the scale reading, and `reader_uncertainty_m` for how much your repeated
  readings of the same depth differ.
- [ ] Write your reader code in the `reader` column.
- [ ] If you do not know an uncertainty, leave the cell blank and say why in the
  notebook. Never write zero. (The software later combines the independent
  uncertainties itself. Do not count the same source of doubt twice.)
- [ ] If another person can read independently, keep both sheets and note where
  they disagree.
- [ ] For an attempt where the marker was hidden, out of the scale's plane or the
  timing is unclear, keep the row and write `unscorable` in the `label` column.
  That means the video cannot show the depth.
- [ ] For an attempt that did not follow the plan (for example you slipped),
  keep the row and write `rejected` in the `label` column.
- [ ] Label the rest by comparing each attempt's marker depth with the baseline
  of the same take. The rule is fixed in advance: an attempt that is no more than
  3 cm (0.03 m) shallower than the baseline is `match`. Otherwise it is
  `shallow`. So an attempt exactly 3 cm or only 2 cm shallower is still `match`.
- [ ] Note any attempt within about 1 cm of the 3 cm line. It is borderline.
- [ ] Keep the stool height you wrote down. It records what you tried, even if
  the marker reading says something different.
- [ ] Write in the notebook that the marker sits on clothing or skin, so it can
  move compared with the middle of your two hip joints. This is a limit of the
  comparison.
- [ ] Save a private copy of the finished attempt sheet before you look at any
  software result.

**Then run the software.**

- [ ] Copy `configs/session.example.json` to a private folder. Fill in the video
  names, the calibration files, the standing seconds, the baseline and the
  attempt sheet. Keep `sync.require_end` set to true.
- [ ] Run the command below. Replace the paths with your own.
- [ ] Keep the numbered output folder of every run, even a run that failed.

```bash
uv run --no-sync rvectr run --config /path/to/session.json --annotations /path/to/annotations.csv
```

**Write up.**

- [ ] List every attempt you made, with its ID.
- [ ] Give the marker errors with their units.
- [ ] For every count, say "x out of y attempts".
- [ ] Give how many attempts agreed with the fixed 3 cm rule.
- [ ] Give how many attempts failed or were unclear.
- [ ] Report each camera and each pair of cameras separately.
- [ ] For a one-camera result, say whether the standing position was borrowed
  from the other cameras (see "Comparing numbers of views" in the pipeline
  guide).

## The attempt sheet, in plain words

`configs/pilot_annotations.example.csv` has one row per attempt.

| Column | What to write |
|---|---|
| `annotation_id` | A unique name for the attempt, for example `test_01`. |
| `start_s`, `bottom_s`, `end_s` | Times in seconds on camera 1's video: when the squat starts, when it is lowest and when it ends. |
| `role` | `reference` for the baseline (exactly one row) and `test` for every other attempt. |
| `label` | `match`, `shallow`, `rejected` (did not follow the plan) or `unscorable` (the video cannot show the depth). |
| `target_height_m` | How much the stool was raised for this attempt, in metres. |
| `marker_depth_m` | Standing height minus bottom height of the marker, in metres. |
| `marker_uncertainty_m` | How unsure the scale reading is, in metres. |
| `reader` | A short code for who read the video. |
| `reader_uncertainty_s` | How unsure the times are, in seconds. |
| `reader_uncertainty_m` | How much repeated readings of the depth differ, in metres. |

A blank cell means "not known". Never write zero for an uncertainty you did not
measure.
