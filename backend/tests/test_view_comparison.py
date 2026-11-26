"""Synthetic checks of the one-camera models and of the comparison between numbers of views.

Everything is generated. Passing shows the software recovers known answers under the
stated assumptions; it says nothing about how accurate real phones are.
"""
import json

import cv2
import numpy as np
import pytest

from rvectr import oneview
from rvectr.pipeline import (DEFAULTS, compare_views, measure_squats, reconstruct_sequence, run_session)

from .test_two_camera_pipeline import (DEPTHS, HIPS, STANDING_HIP_HEIGHT, hip_height, intrinsic, look_at,
                                       needs_ffmpeg, observe, prepare_full_run, skeleton, two_cameras)

UP = np.array([0.0, -1.0, 0.0])          # board frame: Y points down
STANDING = np.array([0.3, -STANDING_HIP_HEIGHT, 0.5])   # pelvis while standing
HIP_LINE = np.array([1.0, 0.0, 0.0])     # left hip -> right hip
BACKWARDS = np.array([0.0, 0.0, 1.0])    # the way the hips move when squatting (flat, across the hip line)
BACK_PER_DROP = 0.5                      # hips travel back by half of how far they go down


def camera_at(direction, distance=3.2, distortion=None, size=(1920, 1080)):
    """A camera `distance` m from the standing spot along a flat direction, looking at the person."""
    direction = np.asarray(direction, float)
    centre = STANDING + distance * direction / np.linalg.norm(direction)
    centre[1] = -1.0
    R, t = look_at(centre, STANDING + [0, 0.25, 0])
    return {"K": intrinsic(*size, 1500), "R": R, "t": t,
            "distortion": np.zeros(5) if distortion is None else np.asarray(distortion, float),
            "units": "m", "board_frame_id": "setupA", "image_size": list(size)}


def pixels_of(points, camera):
    """Pixels of 3D points seen through the camera, including its lens distortion."""
    return cv2.projectPoints(np.ascontiguousarray(points, dtype=float).reshape(-1, 3), cv2.Rodrigues(camera["R"])[0], camera["t"],
                             camera["K"], camera["distortion"])[0].reshape(-1, 2)


def squat_with_backwards_hips(times):
    """Hips [F,2,3] (left, right): down by the squat depth and backwards by half of it."""
    drop = STANDING_HIP_HEIGHT - hip_height(times)
    pelvis = STANDING + drop[:, None] * UP * -1 + (BACK_PER_DROP * drop)[:, None] * BACKWARDS
    return np.stack([pelvis - 0.1 * HIP_LINE, pelvis + 0.1 * HIP_LINE], axis=1)


def one_view_depths(camera, kind, hip_line=HIP_LINE):
    """Depth per rep measured from this one camera with the given plane model."""
    times = np.arange(0, 22, 1 / 60)
    hips = squat_with_backwards_hips(times)
    pixels = np.full((len(times), 17, 2), np.nan)
    pixels[:, 11], pixels[:, 12] = (pixels_of(hips[:, k], camera) for k in (0, 1))
    point, normal = oneview.movement_plane(kind, STANDING, UP, oneview.camera_centre(camera), hip_line)
    xyz, valid = oneview.reconstruct_one_view(pixels, np.full((len(times), 17), 0.9), camera, point, normal)
    result = measure_squats(times, xyz, valid, UP, {"standing_window_s": [0.5, 2.5]})
    return np.array([r["depth_m"] for r in result["reps"]["raw"]["reps"]])


# ----------------------------------------------------------------------------- geometry
def test_points_in_a_known_plane_are_recovered_through_lens_distortion():
    camera = camera_at([1, 0, -1], distortion=[-0.28, 0.09, 0.0012, -0.0008, -0.015])
    point, normal = oneview.movement_plane("movement_plane", STANDING, UP, hip_line=[1, 0, 0.2])
    sideways = np.cross(normal, UP)
    sideways /= np.linalg.norm(sideways)
    # A grid of points lying in the plane (across the person and up and down).
    grid = np.array([point + a * sideways + b * -UP for a in np.linspace(-0.8, 0.8, 9)
                     for b in np.linspace(-0.6, 0.6, 7)])
    pixels = pixels_of(grid, camera).reshape(len(grid), 1, 2)
    assert np.abs(camera["distortion"]).max() > 0.2
    xyz, valid = oneview.reconstruct_one_view(pixels, np.ones((len(grid), 1)), camera, point, normal)
    assert valid.all()
    assert np.abs(xyz[:, 0] - grid).max() < 1e-4   # 0.1 mm


def test_camera_centre_and_rays_follow_the_calibration():
    camera = camera_at([1, 0, -1])
    centre, rays = oneview.camera_centre_and_rays(np.array([[960.0, 540.0], [np.nan, 10.0]]), camera)
    np.testing.assert_allclose(centre, -camera["R"].T @ camera["t"])
    np.testing.assert_allclose(np.linalg.norm(rays[0]), 1.0)
    assert np.isnan(rays[1]).all()
    np.testing.assert_allclose(rays[0], camera["R"][2], atol=1e-9)   # the picture centre looks along the optical axis


def test_planes_face_the_camera_or_follow_the_hip_line():
    point, normal = oneview.movement_plane("fixed_distance", STANDING, UP, camera_centre=STANDING + [2, -1, -2])
    np.testing.assert_allclose(normal, np.array([1, 0, -1]) / np.sqrt(2))   # flat part only
    point, normal = oneview.movement_plane("movement_plane", STANDING, UP, hip_line=[3, 0.4, 0])
    np.testing.assert_allclose(normal, [1, 0, 0])
    with pytest.raises(ValueError):
        oneview.movement_plane("fixed_distance", STANDING, UP)


# ----------------------------------------------------------------------------- one camera, moving hips
def test_squat_with_backwards_hips_from_45_degrees_and_side_on(capsys):
    away = HIP_LINE - BACKWARDS                    # camera in front-side: backwards means away from it
    at_45, side_on = camera_at(away), camera_at(HIP_LINE)
    truth = np.array(DEPTHS)

    plane, fixed = one_view_depths(at_45, "movement_plane"), one_view_depths(at_45, "fixed_distance")
    assert len(plane) == len(fixed) == len(truth)
    assert np.abs(plane - truth).max() < 0.002
    short = 1 - fixed / truth
    assert (short > 0.02).all() and (short < 0.06).all()

    side_plane, side_fixed = one_view_depths(side_on, "movement_plane"), one_view_depths(side_on, "fixed_distance")
    assert np.abs(side_plane - truth).max() < 0.002
    assert np.abs(side_fixed - truth).max() < 0.002
    with capsys.disabled():
        print(f"\n45 deg: movement-plane worst error {np.abs(plane - truth).max() * 1000:.2f} mm, "
              f"fixed-distance short by {short.min() * 100:.1f} to {short.max() * 100:.1f} %"
              f"\nside-on: movement-plane {np.abs(side_plane - truth).max() * 1000:.2f} mm, "
              f"fixed-distance {np.abs(side_fixed - truth).max() * 1000:.2f} mm")


def test_a_hip_line_ten_degrees_wrong_changes_the_depth_by_less_than_three_percent(capsys):
    camera = camera_at(HIP_LINE - BACKWARDS)
    turn = np.radians(10)
    wrong = np.array([np.cos(turn), 0.0, np.sin(turn)])
    right_depth = one_view_depths(camera, "movement_plane")
    wrong_depth = one_view_depths(camera, "movement_plane", hip_line=wrong)
    change = np.abs(wrong_depth / right_depth - 1)
    with capsys.disabled():
        print(f"\nhip_line 10 deg wrong: depth changes by {change.min() * 100:.2f} to {change.max() * 100:.2f} %")
    assert change.max() < 0.03


def test_a_missing_hip_is_nan_never_filled():
    camera = camera_at(HIP_LINE - BACKWARDS)
    point, normal = oneview.movement_plane("movement_plane", STANDING, UP, hip_line=HIP_LINE)
    pixels = np.tile(pixels_of(STANDING, camera), (6, 17, 1))
    confidence = np.full((6, 17), 0.9)
    confidence[1, 11] = 0.1          # too uncertain
    pixels[2, 11] = np.nan           # not detected
    pixels[3, 11] = [-5000, 5000]    # absurd pixel: the ray points away from the plane or never meets it validly
    xyz, valid = oneview.reconstruct_one_view(pixels, confidence, camera, point, normal, min_confidence=0.3)
    assert valid[[0, 4, 5], 11].all() and valid[:, 12].all()
    assert not valid[[1, 2], 11].any() and np.isnan(xyz[[1, 2], 11]).all()
    assert np.isfinite(xyz[0, 11]).all()
    from rvectr import squat
    assert np.isnan(squat.pelvis_track(xyz, valid)[[1, 2]]).all()   # no pelvis without both hips


def test_a_ray_along_the_plane_or_behind_the_camera_is_invalid():
    camera = camera_at([1, 0, -1])
    # A plane that contains the optical axis: the picture-centre ray runs along it.
    centre = oneview.camera_centre(camera)
    along = camera["R"][2]
    normal = np.cross(along, UP)
    xyz, valid = oneview.reconstruct_one_view(np.array([[[960.0, 540.0]]]), np.ones((1, 1)), camera, centre + 0 * along, normal)
    assert not valid.any() and np.isnan(xyz).all()
    # The same plane square-on, but placed behind the camera.
    behind = centre - 2 * camera["R"][2]
    xyz, valid = oneview.reconstruct_one_view(np.array([[[960.0, 540.0]]]), np.ones((1, 1)), camera, behind,
                                              camera["R"][2] * np.array([1, 0, 1]))
    assert not valid.any()


# ----------------------------------------------------------------------------- comparing views
def make_session(angles, offsets, noise_px=0.5, seed=3):
    """Hips-only synthetic observations for cameras at the given angles (degrees around the person)."""
    rng = np.random.default_rng(seed)
    K = intrinsic(1920, 1080, 1500)
    cameras, observations, syncs = [], [], []
    for index, (angle, offset) in enumerate(zip(angles, offsets)):
        a = np.radians(angle)
        centre = [0.3 + 3.2 * np.sin(a), -1.0, 0.5 - 3.2 * np.cos(a)]
        R, t = look_at(centre, [0.3, -0.7, 0.5])
        cameras.append({"K": K, "R": R, "t": t, "distortion": np.zeros(5), "units": "m",
                        "board_frame_id": "setupA", "image_size": [1920, 1080]})
        rate = 60 if index == 0 else 30
        times = np.arange(0, 22, 1 / rate) + (0.0037 if index else 0.0)
        observations.append(observe(times, skeleton(times + offset), cameras[-1], noise_px, rng))
        syncs.append({"offset_s": offset, "drift_rate": 0.0, "anchor_s": 0.0})
    return cameras, observations, syncs


def run_comparison(angles, offsets, views=None):
    cameras, observations, syncs = make_session(angles, offsets)
    periods = [1 / 60] + [1 / 30] * (len(angles) - 1)
    sequence = reconstruct_sequence(observations, cameras, syncs, frame_periods=periods, joints=HIPS)
    result = measure_squats(sequence["times_s"], sequence["xyz"], sequence["valid"], UP,
                            {"standing_window_s": [0.5, 2.5]})
    config = {"cameras": [{"id": f"cam{i + 1}"} for i in range(len(angles))], "squat": result["settings"],
              "triangulation": DEFAULTS["triangulation"], "views": {**DEFAULTS["views"], **(views or {})}}
    return compare_views(observations, cameras, syncs, list(UP), config, sequence, result, periods)


@pytest.fixture(scope="module")
def two_view_comparison():
    return run_comparison([-50, 40], [0.0, 0.6173])


@pytest.fixture(scope="module")
def three_view_comparison():
    return run_comparison([-50, 40, 80], [0.0, 0.6173, -0.31])


def test_two_cameras_give_five_conditions_with_matched_reps(two_view_comparison):
    info = two_view_comparison
    assert list(info["conditions"]) == ["one view, fixed distance (cam1)", "one view, movement plane (cam1)",
                                        "one view, fixed distance (cam2)", "one view, movement plane (cam2)",
                                        "all views (cam1+cam2)"]
    assert info["plane_source"] == "multiview_standing"
    for name, entry in info["conditions"].items():
        assert entry["reps_found"] == 6, name
        assert entry["assumes"]
    everything = info["conditions"]["all views (cam1+cam2)"]
    assert everything["depth_minus_all_views_m"]["mean"] == 0.0
    # Rows keep the all-cameras numbering: six reps for each of the five conditions.
    rows = info["rows"]
    assert len(rows) == 30 and {r["rep"] for r in rows} == {1, 2, 3, 4, 5, 6}
    # The people here squat in place, so the movement-plane model should agree with all views to a few mm.
    movement = info["conditions"]["one view, movement plane (cam1)"]["depth_minus_all_views_m"]
    assert abs(movement["mean"]) < 0.01


def test_measured_plane_inputs_are_labelled_as_measured():
    info = run_comparison([-50, 40], [0.0, 0.6173],
                          views={"standing_point_m": [0.3, -0.95, 0.5], "hip_line": [1, 0, 0]})
    assert info["plane_source"] == "measured"
    assert all(c["plane_source"] == "measured" for c in info["conditions"].values() if c["plane_source"])


def test_three_cameras_give_ten_conditions(three_view_comparison):
    names = list(three_view_comparison["conditions"])
    assert len(names) == 10
    assert sum(n.startswith("one view") for n in names) == 6
    assert sum(n.startswith("two views") for n in names) == 3
    assert sum(n.startswith("all views") for n in names) == 1
    for name in names:
        if name.startswith("two views"):
            entry = three_view_comparison["conditions"][name]
            assert entry["reps_found"] == 6, name
            # Pairs use a different timeline and sync chain; their depths must still match the all-views result.
            assert abs(entry["depth_minus_all_views_m"]["mean"]) < 0.01, name


# ----------------------------------------------------------------------------- whole run
@needs_ffmpeg
def test_full_run_writes_the_view_files_and_can_be_switched_off(tmp_path, monkeypatch):
    paths, outputs, previous, _ = prepare_full_run(tmp_path, monkeypatch)
    run, report = run_session(tmp_path / "session.json", paths, outputs, keypoints_from=previous,
                              progress=lambda *_: None)
    assert report["status"] == "measured"
    for name in ("views_comparison.csv", "views_summary.json", "views_depth.png"):
        assert (run / name).exists(), name
    assert report["views"]["status"] == "done"
    summary = json.loads((run / "views_summary.json").read_text())
    assert len(summary["conditions"]) == 5 and summary["plane_source"] == "multiview_standing"
    header = (run / "views_comparison.csv").read_text().splitlines()[0]
    assert header.startswith("condition,cameras,model,rep,depth_m,depth_se_m")
    assert json.loads((run / "report.json").read_text())["views"]["status"] == "done"

    config = json.loads((tmp_path / "session.json").read_text())
    config["views"] = {"compare": False}
    config["experiment"] = {"annotations": "roster.csv"}
    (tmp_path / "roster.csv").write_text(
        "annotation_id,start_s,bottom_s,end_s,role,label,target_height_m,marker_depth_m,marker_uncertainty_m,reader,reader_uncertainty_s,reader_uncertainty_m\n"
        "S1,3,4,5,test,match,0,,,,,\n"
        "S2,5.8,6.8,7.8,reference,match,0,,,,,\n"
    )
    (tmp_path / "session_off.json").write_text(json.dumps(config))
    run_off, report_off = run_session(tmp_path / "session_off.json", paths, outputs, keypoints_from=previous,
                                      progress=lambda *_: None)
    assert report_off["status"] == "measured" and "views" not in report_off
    assert not (run_off / "views_comparison.csv").exists()
    saved = json.loads((run_off / "report.json").read_text())
    assert saved["reference_source"]["annotation_id"] == "S2"
    assert saved["scoring"]["decision_settings"]["tolerance_m"] == 0.03
    score = saved["experiment"][saved["scoring"]["primary_condition"]]
    assert score["counts"]["reference_excluded"] == 1 and score["counts"]["extra"] == 4
    assert score["classification"]["denominator"] == 1


@needs_ffmpeg
def test_a_failing_comparison_keeps_the_main_result(tmp_path, monkeypatch):
    paths, outputs, previous, _ = prepare_full_run(tmp_path, monkeypatch)
    from rvectr import pipeline

    def broken(*args, **kwargs):
        raise RuntimeError("planes could not be placed")
    monkeypatch.setattr(pipeline, "compare_views", broken)
    run, report = run_session(tmp_path / "session.json", paths, outputs, keypoints_from=previous,
                              progress=lambda *_: None)
    assert report["status"] == "measured"
    assert report["views"] == {"status": "failed", "error": "planes could not be placed"}
    assert (run / "reps_raw.csv").exists() and not (run / "views_comparison.csv").exists()


def annotated_session():
    """Two synthetic cameras and an annotation list built from the squats the all-views result found."""
    cameras, observations, syncs = make_session([-50, 40], [0.0, 0.6173])
    periods = [1 / 60, 1 / 30]
    sequence = reconstruct_sequence(observations, cameras, syncs, frame_periods=periods, joints=HIPS)
    measured = measure_squats(sequence["times_s"], sequence["xyz"], sequence["valid"], UP,
                              {"standing_window_s": [0.5, 2.5]})
    found = measured["reps"]["raw"]["reps"]
    annotations = []
    for rep in found:
        is_reference = rep["rep"] == 1
        annotations.append({"annotation_id": f"rep{rep['rep']}", "start_s": rep["start_s"],
                            "bottom_s": rep["bottom_s"], "end_s": rep["end_s"],
                            "role": "reference" if is_reference else "test",
                            "label": "match" if is_reference or rep["rep"] % 2 else "shallow",
                            "target_height_m": None, "marker_depth_m": None,
                            "marker_uncertainty_m": None, "reader": "reader-a",
                            "reader_uncertainty_s": 0.03, "reader_uncertainty_m": None})
    config = {"cameras": [{"id": "cam1"}, {"id": "cam2"}], "squat": measured["settings"],
              "triangulation": DEFAULTS["triangulation"], "views": {"compare": True,
                  "standing_point_m": STANDING.tolist(), "hip_line": HIP_LINE.tolist()},
              "experiment": {"annotations": "pilot.csv", "match_window_s": 0.5,
                             "tolerance_m": 0.03, "borderline_m": 0.01}}
    result = {"reps": {"raw": {"reps": [], "classification": None}}, "jitter": {},
              "settings": measured["settings"], "primary": "raw"}
    return cameras, observations, syncs, periods, sequence, result, config, annotations, found


def test_independent_annotation_list_scores_each_condition_even_without_all_view_reference(monkeypatch):
    from rvectr.pipeline import compare_views

    cameras, observations, syncs, periods, sequence, result, config, annotations, found = annotated_session()
    from rvectr import pipeline
    original = pipeline._measure_condition
    middle_time = found[2]["bottom_s"]

    def less_accurate_all_views(times, xyz, valid, up, settings, reference_reps):
        scored = original(times, xyz, valid, up, settings, reference_reps)
        if xyz is sequence["xyz"]:
            scored["reps"] = [rep for rep in scored["reps"] if abs(rep["bottom_s"] - middle_time) > 0.5]
        return scored

    monkeypatch.setattr(pipeline, "_measure_condition", less_accurate_all_views)
    info = pipeline.compare_views(observations, cameras, syncs, UP, config, sequence, result,
                                  periods, annotations=annotations)
    conditions = info["experiment"]["conditions"]
    assert len(conditions) == 5
    assert all(item["status"] == "scored" for item in conditions.values())
    expected_ids = {item["annotation_id"] for item in annotations}
    for condition in conditions:
        rows = [row for row in info["experiment"]["rows"] if row["condition"] == condition]
        assert {row["annotation_id"] for row in rows if row["annotation_id"]} == expected_ids
        assert sum(row["status"] == "reference_excluded" for row in rows) == 1
    all_view_name = next(name for name in conditions if name.startswith("all views"))
    all_rows = [row for row in info["experiment"]["rows"] if row["condition"] == all_view_name]
    assert next(row for row in all_rows if row["annotation_id"] == "rep3")["status"] == "missed"
    better_camera = next(name for name in conditions if name.startswith("one view"))
    better_rows = [row for row in info["experiment"]["rows"] if row["condition"] == better_camera]
    assert next(row for row in better_rows if row["annotation_id"] == "rep3")["status"] != "missed"


def test_annotated_run_says_which_tolerances_it_used_and_which_squat_values_it_ignored():
    from rvectr.pipeline import _annotated_decision_settings

    config = {"experiment": {"tolerance_m": 0.03, "borderline_m": 0.01},
              "squat": {"tolerance_m": 0.05, "borderline_m": 0.01}}
    settings = _annotated_decision_settings(config)
    assert settings["tolerance_m"] == 0.03 and settings["borderline_m"] == 0.01
    assert settings["squat_values_not_used"] == {"squat.tolerance_m": 0.05}
    assert settings["warning"] == ("Annotated scoring used experiment.tolerance_m=0.03 and "
                                   "experiment.borderline_m=0.01; ignored squat.tolerance_m=0.05.")
    # Matching values need no warning, but the values used are still recorded.
    same = _annotated_decision_settings({"experiment": config["experiment"], "squat": config["experiment"]})
    assert same["warning"] is None and same["squat_values_not_used"] == {} and same["tolerance_m"] == 0.03


def test_a_failed_one_view_condition_is_not_scored_as_every_squat_missed(monkeypatch):
    cameras, observations, syncs, periods, sequence, result, config, annotations, _ = annotated_session()

    def broken(*args, **kwargs):
        raise ValueError("this camera could not be triangulated")

    monkeypatch.setattr(oneview, "reconstruct_one_view", broken)
    info = compare_views(observations, cameras, syncs, UP, config, sequence, result, periods,
                         annotations=annotations)
    conditions = info["experiment"]["conditions"]
    failed = {name: item for name, item in conditions.items() if item["status"] == "failed"}
    assert len(failed) == 4 and conditions["all views (cam1+cam2)"]["status"] == "scored"
    eligible = sum(a["role"] == "test" and a["label"] in ("match", "shallow") for a in annotations)
    for name, item in failed.items():
        rows = [row for row in info["experiment"]["rows"] if row["condition"] == name]
        assert {row["annotation_id"] for row in rows} == {a["annotation_id"] for a in annotations}
        assert {row["status"] for row in rows} == {"condition_failed"}
        assert all(row["condition_failure"] == "this camera could not be triangulated" for row in rows)
        assert item["error"] == item["failure_reason"] == "this camera could not be triangulated"
        assert item["counts"]["missed"] is None and item["counts"]["correct"] is None
        assert item["classification"]["accuracy"] is None
        assert item["classification"]["end_to_end_accuracy"] is None
        assert item["classification"]["all_eligible_tests_denominator"] == eligible
    # The condition that did run still gets real numbers.
    assert conditions["all views (cam1+cam2)"]["classification"]["end_to_end_accuracy"] is not None
    assert {row["outcome"] for row in info["rows"] if row["condition"] in failed} == {"condition_failed"}


def test_invalid_config_still_records_a_failed_attempt_and_annotation_roster(tmp_path):
    from rvectr.paths import RuntimePaths

    annotations = tmp_path / "pilot.csv"
    annotations.write_text(
        "annotation_id,start_s,bottom_s,end_s,role,label,target_height_m,marker_depth_m,marker_uncertainty_m,reader,reader_uncertainty_s,reader_uncertainty_m\n"
        "ref,0,1,2,reference,match,0,,,,,\n"
        "rep2,3,4,5,test,shallow,0.04,,,,,\n", encoding="utf-8")
    config = tmp_path / "bad-session.json"
    config.write_text(json.dumps({"cameras": [{"id": "cam1", "video": "one.mp4"}],
                                  "experiment": {"annotations": "pilot.csv"}}), encoding="utf-8")
    outputs = tmp_path / "outputs"
    paths = RuntimePaths(tmp_path, tmp_path, tmp_path, tmp_path, outputs)
    with pytest.raises(ValueError, match="at least two cameras"):
        run_session(config, paths, progress=lambda *_: None)
    run = outputs / "V1.1.1"
    manifest = json.loads((run / "manifest.json").read_text())
    report = json.loads((run / "report.json").read_text())
    assert manifest["status"] == report["status"] == "failed"
    assert report["stage"] == "configuration"
    records = report["experiment_attempt"]["records"]
    assert [item["status"] for item in records] == ["unscorable_run_failed_before_result"] * 2



def test_match_window_too_wide_for_the_annotations_is_a_recorded_configuration_failure(tmp_path):
    from rvectr.paths import RuntimePaths

    (tmp_path / "pilot.csv").write_text(
        "annotation_id,start_s,bottom_s,end_s,role,label,target_height_m,marker_depth_m,marker_uncertainty_m,reader,reader_uncertainty_s,reader_uncertainty_m\n"
        "ref,0,1,2,reference,match,0,,,,,\n"
        "rep2,1.2,1.8,2.5,test,shallow,0.04,,,,,\n", encoding="utf-8")
    config = tmp_path / "session.json"
    config.write_text(json.dumps({"cameras": [{"id": "cam1", "video": "a.mp4"}, {"id": "cam2", "video": "b.mp4"}],
                                  "experiment": {"annotations": "pilot.csv", "match_window_s": 0.5}}),
                      encoding="utf-8")
    outputs = tmp_path / "outputs"
    paths = RuntimePaths(tmp_path, tmp_path, tmp_path, tmp_path, outputs)
    with pytest.raises(ValueError, match="less than half the smallest gap"):
        run_session(config, paths, progress=lambda *_: None)
    run = outputs / "V1.1.1"
    manifest = json.loads((run / "manifest.json").read_text())
    report = json.loads((run / "report.json").read_text())
    assert manifest["status"] == report["status"] == "failed"
    assert report["stage"] == "configuration" and "match_window_s" in report["error"]
    assert [item["annotation_id"] for item in report["experiment_attempt"]["records"]] == ["ref", "rep2"]


def test_invalid_json_structure_has_a_failed_report(tmp_path):
    from rvectr.paths import RuntimePaths

    cfg = tmp_path / "session.json"
    cfg.write_text("[]", encoding="utf-8")
    paths = RuntimePaths(tmp_path, tmp_path, tmp_path, tmp_path, tmp_path / "outputs")
    with pytest.raises(ValueError, match="JSON object"):
        run_session(cfg, paths, progress=lambda *_: None)
    run = paths.outputs / "V1.1.1"
    assert json.loads((run / "report.json").read_text())["reference_source"]["kind"] == "unavailable"
    assert json.loads((run / "manifest.json").read_text())["status"] == "failed"
