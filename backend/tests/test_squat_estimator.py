"""Fast checks of the squat-depth estimators on synthetic pelvis-height traces.

Each trace is a person who stands still, then does repetitions shaped like a raised
cosine (the same motion as the error-budget simulation), with a 2 s standing pause
after every repetition. The true depth of every repetition is known.
"""
import numpy as np

from rvectr import squat

STANDING_M = 0.95
DEPTHS = (0.30, 0.30, 0.27, 0.30)   # reference first, then one shallower repetition
PACES = (2.0, 0.8)                  # descent time in seconds: controlled, fast


def make_trace(fps=60.0, descent_s=2.0, depths=DEPTHS, noise_m=0.0, rng=None, phase_s=0.0, pause_s=2.0, lead_s=3.0):
    """Pelvis height [F] over time [F]; also the true bottom time of every repetition."""
    dt = 1.0 / fps
    starts = lead_s + phase_s + (2 * descent_s + pause_s) * np.arange(len(depths))
    times = np.arange(int((starts[-1] + 2 * descent_s + pause_s) / dt)) * dt
    drop = np.zeros_like(times)
    for start, depth in zip(starts, depths):
        s = times - start
        inside = (s >= 0) & (s <= 2 * descent_s)
        drop[inside] += depth * np.sin(np.pi * s[inside] / (2 * descent_s)) ** 2
    h = STANDING_M - drop
    if noise_m:
        h = h + rng.standard_normal(len(times)) * noise_m
    return times, h, starts + descent_s


def noisy_sessions(descent_s, n_sessions, noise_m, fps=60.0, estimator="parabola"):
    """Depth errors, reported standard errors and number of extra repetitions over many sessions."""
    errors, reported, extra = [], [], []
    for i in range(n_sessions):
        rng = np.random.default_rng(100 + i)
        times, h, _ = make_trace(fps, descent_s, noise_m=noise_m, rng=rng, phase_s=rng.uniform(0, 1 / fps))
        reps, _ = squat.segment_reps(times, h, estimator=estimator)
        extra.append(len(reps) - len(DEPTHS))
        if len(reps) == len(DEPTHS):
            errors += [r["depth_m"] - d for r, d in zip(reps, DEPTHS)]
            reported += [r.get("depth_se_m", np.nan) for r in reps]
    return np.array(errors), np.array(reported), np.array(extra)


def unclear_share(reps):
    """Share of the true repetitions the software would not judge (missing ones count as unclear)."""
    unclear = sum(1 for r in reps if r["coverage"] < 0.85 or not r["bottom_observed"])
    return (unclear + max(len(DEPTHS) - len(reps), 0)) / len(DEPTHS)


def test_no_noise_recovers_depth_and_bottom_time():
    for fps in (60.0, 30.0):
        for descent_s in PACES:
            times, h, bottoms = make_trace(fps, descent_s, phase_s=0.4 / fps)
            reps, _ = squat.segment_reps(times, h)
            assert len(reps) == len(DEPTHS)
            for rep, depth, bottom in zip(reps, DEPTHS, bottoms):
                assert abs(rep["depth_m"] - depth) < 0.0005
                assert abs(rep["bottom_s"] - bottom) < 0.005
                assert rep["bottom_observed"] and rep["standing_source"] == "local"


def test_white_noise_biases_the_old_estimator_but_not_the_parabola():
    for descent_s in PACES:
        parabola, _, _ = noisy_sessions(descent_s, 100, 0.004)
        extreme, _, _ = noisy_sessions(descent_s, 100, 0.004, estimator="extreme")
        assert len(parabola) >= 400 and len(extreme) >= 400
        assert abs(parabola.mean()) < 0.001
        assert extreme.mean() > 0.005   # every depth too deep


def test_reported_standard_error_matches_the_actual_spread_for_white_noise():
    for descent_s in PACES:
        errors, reported, _ = noisy_sessions(descent_s, 100, 0.004)
        assert abs(np.mean(reported) / np.std(errors) - 1) < 0.30


def test_random_missing_frames_rarely_make_a_repetition_unclear():
    for fps, descent_s in ((60.0, 2.0), (60.0, 0.8), (30.0, 2.0)):
        shares, errors = [], []
        for i in range(60):
            rng = np.random.default_rng(300 + i)
            times, h, _ = make_trace(fps, descent_s, phase_s=rng.uniform(0, 1 / fps))
            h[rng.random(len(h)) < 0.08] = np.nan
            reps, _ = squat.segment_reps(times, h)
            shares.append(unclear_share(reps))
            errors += [r["depth_m"] - d for r, d in zip(reps, DEPTHS) if r["bottom_observed"]]
        assert np.mean(shares) < 0.05
        assert np.abs(errors).max() < 0.003   # no noise: only the missing samples differ


def test_no_frames_near_the_bottom_means_unclear_not_a_guess():
    for descent_s in PACES:
        times, h, bottoms = make_trace(60.0, descent_s)
        h[np.abs(times - bottoms[1]) < 0.15] = np.nan
        reps, _ = squat.segment_reps(times, h)
        classified, _ = squat.classify(reps, 1, 0.03)
        assert classified[1]["outcome"] == "unclear" and not classified[1]["bottom_observed"]
        assert np.isnan(classified[1]["depth_se_m"])
        assert classified[2]["outcome"] != "unclear"


def test_no_frames_after_the_bottom_means_unclear():
    for descent_s in PACES:
        times, h, bottoms = make_trace(60.0, descent_s)
        h[(times > bottoms[1]) & (times < bottoms[1] + descent_s)] = np.nan   # the whole way back up
        reps, _ = squat.segment_reps(times, h)
        classified, _ = squat.classify(reps, 1, 0.03)
        assert classified[1]["outcome"] == "unclear"


def test_strong_noise_does_not_invent_repetitions():
    for descent_s in PACES:
        _, _, extra = noisy_sessions(descent_s, 40, 0.0083)
        assert (extra == 0).all()


def rep_with(rep, depth, se=None):
    out = {"rep": rep, "depth_m": depth, "coverage": 1.0, "bottom_observed": True}
    if se is not None:
        out["depth_se_m"] = se
    return out


def test_classify_borderline_uses_the_larger_of_the_fixed_margin_and_twice_the_error():
    # Pass line = 0.30 - 0.03 = 0.27 m. The test repetition (0.262 m) is 8 mm from it.
    # difference_se = sqrt(0.004^2 + 0.003^2) = 5 mm, so twice that is 10 mm.
    reps = [rep_with(1, 0.30, 0.003), rep_with(2, 0.262, 0.004)]
    out, _ = squat.classify(reps, 1, 0.03, borderline_m=0.005)
    assert abs(out[1]["difference_se_m"] - 0.005) < 1e-12 and out[0]["difference_se_m"] == 0
    assert out[1]["borderline"]                       # 8 mm <= max(5 mm, 10 mm)
    out, _ = squat.classify(reps, 1, 0.03, borderline_m=0.012)
    assert out[1]["borderline"]                       # 8 mm <= max(12 mm, 10 mm)
    reps = [rep_with(1, 0.30, 0.003), rep_with(2, 0.255, 0.004)]
    out, _ = squat.classify(reps, 1, 0.03, borderline_m=0.005)
    assert not out[1]["borderline"]                   # 15 mm > max(5 mm, 10 mm)
    assert out[1]["outcome"] == "shallower"           # the outcome itself ignores the error bar
    reps = [rep_with(1, 0.30, 0.003), rep_with(2, 0.262)]   # error unknown: old fixed rule
    out, _ = squat.classify(reps, 1, 0.03, borderline_m=0.005)
    assert np.isnan(out[1]["difference_se_m"]) and not out[1]["borderline"]


# Captured from the code BEFORE the parabola estimator was added (same traces as below).
# Each row: rep, start_index, bottom_index, end_index, standing_m, bottom_m, depth_m, bottom_observed, coverage.
GOLDEN_EXTREME = {
    "clean 60 fps controlled": [
        (1, 204, 300, 396, 0.95, 0.650002, 0.299998, True, 1.0), (2, 564, 660, 756, 0.95, 0.650002, 0.299998, True, 1.0),
        (3, 924, 1020, 1116, 0.95, 0.680001, 0.269999, True, 1.0), (4, 1284, 1380, 1476, 0.95, 0.650002, 0.299998, True, 1.0)],
    "clean 30 fps fast": [
        (1, 95, 114, 134, 0.95, 0.65001, 0.29999, True, 1.0), (2, 203, 222, 242, 0.95, 0.65001, 0.29999, True, 1.0),
        (3, 311, 330, 350, 0.95, 0.680009, 0.269991, True, 1.0), (4, 419, 438, 458, 0.95, 0.65001, 0.29999, True, 1.0)],
    "noisy 60 fps controlled": [
        (1, 200, 298, 400, 0.959578, 0.644203, 0.315374, True, 1.0), (2, 561, 665, 758, 0.958047, 0.642945, 0.315102, True, 1.0),
        (3, 923, 1017, 1119, 0.961865, 0.676348, 0.285517, True, 1.0), (4, 1282, 1384, 1476, 0.957459, 0.643211, 0.314248, True, 1.0)],
    "noisy 60 fps fast": [
        (1, 188, 226, 269, 0.962204, 0.642594, 0.31961, True, 1.0), (2, 404, 441, 485, 0.962536, 0.645676, 0.316859, True, 1.0),
        (3, 619, 660, 699, 0.959004, 0.6774, 0.281603, True, 1.0), (4, 835, 874, 916, 0.959594, 0.642532, 0.317062, True, 1.0)],
    "noisy with gaps, given standing level": [
        (1, 204, 290, 397, 0.956616, 0.648029, 0.308588, True, 0.927835), (2, 562, 657, 758, 0.957633, 0.646828, 0.310805, True, 0.908629),
        (3, 921, 1015, 1121, 0.959945, 0.672367, 0.287578, True, 0.910448), (4, 1284, 1381, 1480, 0.958112, 0.641271, 0.316841, True, 0.913706)],
}


def golden_traces():
    yield "clean 60 fps controlled", make_trace(60, 2.0, phase_s=0.003), None
    yield "clean 30 fps fast", make_trace(30, 0.8, phase_s=0.003), None
    yield "noisy 60 fps controlled", make_trace(60, 2.0, noise_m=0.004, rng=np.random.default_rng(5), phase_s=0.003), None
    yield "noisy 60 fps fast", make_trace(60, 0.8, noise_m=0.004, rng=np.random.default_rng(6), phase_s=0.003), None
    rng = np.random.default_rng(7)
    times, h, bottoms = make_trace(60, 2.0, noise_m=0.004, rng=rng, phase_s=0.003)
    h[rng.random(len(h)) < 0.08] = np.nan
    yield "noisy with gaps, given standing level", (times, h, bottoms), 0.95


def test_old_estimator_reproduces_the_values_captured_before_the_change():
    for name, (times, h, _), standing in golden_traces():
        reps, _ = squat.segment_reps(times, h, standing=standing, estimator="extreme")
        got = [(r["rep"], r["start_index"], r["bottom_index"], r["end_index"], round(r["standing_m"], 6),
                round(r["bottom_m"], 6), round(r["depth_m"], 6), r["bottom_observed"], round(r["coverage"], 6)) for r in reps]
        assert got == GOLDEN_EXTREME[name], name
