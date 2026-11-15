"""Audio alignment is a candidate timing estimate, never exposure verification."""
from __future__ import annotations
import numpy as np
from scipy import signal


def estimate_audio_offset(reference, other, sample_rate, ref_audio_start=0., other_audio_start=0.):
    """Return ref_time = other_time + offset_s. Input arrays are decoded audio."""
    a, b = np.asarray(reference, float), np.asarray(other, float)
    if min(len(a), len(b)) < sample_rate or min(np.std(a), np.std(b)) < 1e-8:
        return {"status": "unresolved", "reason": "Insufficient non-silent audio"}
    # Compare 1-ms energy envelopes: phones have different microphones and AGC.
    block = max(1, sample_rate // 1000)
    def envelope(x):
        n = len(x) // block
        v = np.sqrt(np.mean(x[:n*block].reshape(n, block)**2, axis=1))
        v = np.log1p(v / (np.median(v) + 1e-8))
        return (v - v.mean()) / (v.std() + 1e-8)
    ea, eb = envelope(a), envelope(b)
    corr = signal.correlate(ea, eb, mode="full", method="fft")
    lags = signal.correlation_lags(len(ea), len(eb), mode="full")
    overlap = signal.correlate(np.ones(len(ea)), np.ones(len(eb)), mode="full", method="fft")
    corr = np.where(overlap >= 0.6 * min(len(ea), len(eb)), corr / np.maximum(overlap, 1), -np.inf)
    k = int(np.argmax(corr))
    lag = int(lags[k])
    step = block / sample_rate
    candidates = []
    # Independent windows expose possible drift, echoes and wrong peaks.
    for center in np.linspace(0.2, 0.8, 4):
        mid_b = int(center * len(eb))
        half = min(4000, len(eb)//10)
        lo_b, hi_b = mid_b-half, mid_b+half
        lo_a, hi_a = lo_b+lag, hi_b+lag
        if lo_a < 0 or hi_a > len(ea):
            continue
        local = signal.correlate(ea[lo_a:hi_a], eb[lo_b:hi_b], method="fft")
        local_lags = signal.correlation_lags(hi_a-lo_a, hi_b-lo_b)
        mask = np.abs(local_lags) <= int(.15 / step)
        best = int(np.argmax(np.where(mask, local, -np.inf)))
        candidates.append({"other_time_s": mid_b*step+other_audio_start,
                           "offset_s": (lag+int(local_lags[best]))*step+ref_audio_start-other_audio_start})
    offset = lag * step + ref_audio_start - other_audio_start
    spread = float(np.ptp([p["offset_s"] for p in candidates])) if len(candidates)>1 else None
    return {"status": "candidate_only", "offset_s": offset,
            "mapping": "reference_pts = other_pts + offset_s", "method": "FFT audio energy correlation",
            "peak_score": float(corr[k]), "window_estimates": candidates,
            "window_offset_range_s": spread, "exposure_alignment_verified": False,
            "reason": "Audio/video device latency, sound travel, drift and rolling shutter are not certified by audio correlation"}


def interpolate_observations(timestamps, xy, confidence, query, max_gap_s=0.08):
    """Bounded interpolation of observations; never extrapolate or fill missing joints."""
    t = np.asarray(timestamps)
    xy, confidence = np.asarray(xy), np.asarray(confidence)
    out = np.full((len(query), xy.shape[1], 2), np.nan)
    scores = np.zeros((len(query), xy.shape[1]))
    for i, q in enumerate(query):
        j = int(np.searchsorted(t, q))
        if j < len(t) and np.isclose(q, t[j], atol=1e-8, rtol=0):
            out[i], scores[i] = xy[j], confidence[j]
        elif 0 < j < len(t) and t[j]-t[j-1] <= max_gap_s:
            valid = np.isfinite(xy[j]).all(-1) & np.isfinite(xy[j-1]).all(-1)
            alpha = (q-t[j-1])/(t[j]-t[j-1])
            out[i, valid] = (1-alpha)*xy[j-1,valid]+alpha*xy[j,valid]
            scores[i, valid] = np.minimum(confidence[j-1, valid], confidence[j, valid])
    return out, scores
