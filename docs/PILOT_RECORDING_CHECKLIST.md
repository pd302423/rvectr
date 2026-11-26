# First squat-depth recording

Use one private take ID for each continuous recording from all the phones.
Keep the notebook, original videos, annotated frames and outputs together by
take ID. The checklist records a pilot observation only after someone films
and reads it. The exercises and example CSV values in the repository are examples.

## Set up and measure

- [ ] Use two stable phones for the one-versus-two pilot. Use three only if you can capture the same attempts in all three. Write down each camera ID, measured angle, distance, lens height, lens, resolution, orientation and frame rate.
- [ ] To compare with the simulated layout, place the first camera side-on (90° from the facing direction), the second at +45°, and an optional third at −45°. The simulation uses level lenses 1 m high, 3 m from the standing spot. Record any differences. Place a visible floor cross and fix the phones after lens calibration.
- [ ] Use steady lighting, fixed zoom, focus and exposure where possible. Disable stabilization, automatic framing and lens changes. Check that both hips and the scale stay inside the image during the entire movement.
- [ ] Attach the rectangular checkerboard flat. Measure across several printed squares horizontally and vertically, divide by the number of squares and record both measurements and ruler precision. If the sizes disagree beyond reading uncertainty, reprint without stretch and remeasure. The scalar square-size option assumes the two sizes agree.
- [ ] Add an asymmetric physical mark in the border next to the intended inner corner 0 and distinguish the long +X and short +Y directions. Film varied, sharp board poses for each lens. Mount the cameras and film the same still, level board from every view. Turn the board so the marked face is visible to all cameras.
- [ ] Run the intrinsic and extrinsic commands in the [pipeline guide](TWO_CAMERA_PIPELINE.md). Open every saved `<output-stem>.corners.png`. Compare circle 0 and both arrows with the physical marks. A low pixel error cannot establish physical corner identity. Redo the still-board clip if any view disagrees or a camera moves.
- [ ] Measure the distance between the marks on a rigid stick. Record reconstructions and signed length errors at the centre, left, right, near and far. Check vertical, horizontal and toward/away orientations at each position. Investigate failures before recording a participant.

## Record the same experiment at both speeds

- [ ] With the supervising adult, choose stable, comfortable stool settings and measure the baseline seat height and each raised seat height. Enter their difference in metres as `target_height_m`. Mark the floor at the standing spot. Film only the agreed participant and stop if uncomfortable. Keep the floor clear and the support stable.
- [ ] Place a visible marker on snug clothing near the side of the pelvis. Beside it place a vertical ruler or measured tape in the same depth plane. The side camera should view the scale face-on, with the marker and at least two known scale ticks legible while standing and at the bottom. A scale on a distant wall gives a different image scale. Photograph or sketch this geometry privately.
- [ ] In one continuous take, flash a torch where every camera sees it, stand still for the configured standing window, and film the unraised baseline reference **and** test attempts. Repeat some baseline attempts to measure matching agreement. Include the same selected raised heights at both speeds. Never move a camera to change the stool. Record each ID and height and keep every miss or interruption.
- [ ] Alternate the order of the test heights between blocks (for example low/high, then high/low). Alternate the speed order across replicate blocks. Keep the reference identifiable in each take, pause upright between attempts and flash again before stopping. A two-speed comparison with one reference per take compares within-take changes.
- [ ] Record the observed descent duration for **each** attempt from the camera timestamps. Nominal speeds (the simulation uses 2.0 and 0.8 seconds down) are settings. Preserve actual timing even when the movement misses its target.

## Read the scale before opening a reconstruction

- [ ] On camera 1's original clock, independently mark the start, bottom and end of every attempt. During a hold use the middle of the lowest stable interval. Save the reference ID first. Estimate reading uncertainty from the frame spacing, blurred edges and uncertainty in selecting the bottom. Retain attempts with a hidden marker or unclear timing in the ledger.
- [ ] Read the marker centre against two known ticks for the standing and bottom frames. Interpolate between adjacent ticks, record **both** heights and the scale's resolution privately, then subtract bottom from standing. Convert to metres for `marker_depth_m`. For example, a displacement measured in centimetres is divided by 100. Read from the side scale independently of the triangulated software output. With a different scale-camera clock, map the times using the two-flash sync record.
- [ ] Record the plausible reading range or repeated blinded readings, reader code and uncertainty in the notebook. Use metres for the uncertainty in the marker displacement (`marker_uncertainty_m`, scale readout) and the spread of the reader's repeated depth readings (`reader_uncertainty_m`). Use seconds for `reader_uncertainty_s`. Record the method alongside the sheet. The borderline calculation combines independent components for the baseline and test by root-sum-square. Avoid counting the same source twice. If components are unknown or share a bias, leave unsupported fields blank and describe it in the notebook. If two readers are available, keep both sheets and their disagreement. A hidden or out-of-plane marker is unscorable. The skin/clothing marker can move relative to the internal midpoint of the two estimated hip joints. Record this as a limitation of the comparison.
- [ ] For a human classification, compare **measured marker displacements** with that same take's baseline using the fixed 0.03 m tolerance. A test exactly 3 cm or only 2 cm shallower still reaches the reference under that rule. Flag proximity to the boundary separately. The raised stool height records what was attempted, even if the marker reading differs.
- [ ] Save a private copy of the independent annotation CSV before viewing results. Set the camera paths, calibration, standing interval, baseline and annotations in a private session JSON. Keep `sync.require_end` true for the speed experiment. Run the CLI and retain its numbered folder even if it fails.

```bash
uv run --no-sync rvectr sync --config /path/to/session.json --out /path/to/sync
uv run --no-sync rvectr frames --config /path/to/session.json --sync /path/to/sync/sync.json --time 9.2 --out /path/to/marker
uv run --no-sync rvectr run --config /path/to/session.json --annotations /path/to/annotations.csv
```

Replace paths and the illustrative time with the take's actual values. Record
each camera and pair separately, and note whether a one-camera setup borrowed
the multiview standing geometry. Report all attempted IDs, marker errors with
units and denominators, fixed-rule agreement, and failed/unclear counts.
