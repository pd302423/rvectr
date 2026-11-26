"""Make poster-quality charts and data tables from the squat-depth error-budget simulation.

uv run --no-sync python tools/make_poster_charts.py

SIMULATION, NOT A MEASUREMENT. By default, every number is read from the versioned compact
summary in src/lib/results/simulation-summary.json (nothing is typed in by hand) and
every number that appears on a chart is listed, with its key path in summary.json, in
outputs/poster_kit/data/all_headline_numbers.csv.

Writes (only under outputs/poster_kit/):
    charts/NN_name.png   300 dpi
    charts/NN_name.svg   vector, text converted to outlines so it looks the same on any computer
    data/NN_name.csv     the numbers plotted (mm and curve percentages rounded to 1 decimal)
    data/07_pause_at_bottom.csv, data/08_error_bar_check.csv, data/all_headline_numbers.csv
    original_simulation_output/   copies of the original run files
Does not re-run the simulation and does not touch the original run folder.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import re
import shutil
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
_parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
_parser.add_argument("--summary", help="summary.json or simulation run directory (default: versioned compact site summary)")
_parser.add_argument("--out", help="poster output directory (default: outputs/poster_kit)")
_args, _unknown = _parser.parse_known_args()
_summary_path = Path(_args.summary) if _args.summary else ROOT / "src" / "lib" / "results" / "simulation-summary.json"
if _summary_path.is_dir():
    SRC = _summary_path
    SUMMARY_PATH = SRC / "summary.json"
else:
    SUMMARY_PATH = _summary_path
    SRC = SUMMARY_PATH.parent
RUN_NAME = "unknown-run"
OUT = Path(_args.out) if _args.out else ROOT / "outputs" / "poster_kit"
CHARTS, DATA, ORIG = OUT / "charts", OUT / "data", OUT / "original_simulation_output"
ORIGINAL_FILES = ("summary.md", "summary.json", "detection_curves.png", "ranking.png", "sweeps.png")

# ----------------------------------------------------------------------------- look
TEAL, LTEAL, ORANGE = "#1f6b5c", "#8fc2b4", "#b5643a"   # controlled pace, fast pace, comparison series
TEXT, MUTED, GRID, AXIS, BG = "#2e2e2e", "#5c5c5c", "#e4e4e4", "#9a9a9a", "#ffffff"
TITLE_PT, SUB_PT, LABEL_PT, TICK_PT, VALUE_PT, NOTE_PT, FOOT_PT = 21, 14, 15, 14, 15, 13, 12
MARGIN_IN = 0.6

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Noto Sans", "Liberation Sans", "DejaVu Sans"],
    "svg.fonttype": "path",            # text becomes outlines: identical on any computer
    "axes.unicode_minus": True,
    "axes.edgecolor": AXIS, "axes.labelcolor": TEXT, "text.color": TEXT,
    "xtick.color": TEXT, "ytick.color": TEXT,
    "figure.facecolor": BG, "savefig.facecolor": BG, "axes.facecolor": BG,
})

# ----------------------------------------------------------------------------- plain-language names
MODES = [("side_1cam", "1 phone (side)"), ("oblique_1cam", "1 phone (angled)"),
         ("two_cam", "2 phones"), ("three_cam", "3 phones")]
PACES = [("controlled", "Slow (2 s down)"), ("fast", "Fast (0.8 s down)")]
MODE_NAME, PACE_NAME = dict(MODES), dict(PACES)
CLEAN, SHAKY, DRIFT = "Lower noise", "Higher noise", "Slow drift"
MDD_PLAIN = "First tested change meeting criteria"
MDD_NOTE = (f"{MDD_PLAIN} is the first tested grid value whose threshold flags at least 95% of all shallow reps "
            "and at most 5% of all matching reps. Unclear reps count in both denominators. The cutoff is fit on "
            "one half of sessions and checked on the other; no interpolation is used.")
MDD_NAME = f"{MDD_PLAIN} (mm)"
UNICODE_MINUS = "−"


# ----------------------------------------------------------------------------- reading summary.json
SUMMARY = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
RUN_NAME = str(SUMMARY.get("created_utc") or SRC.name)
FOOTER = f"Computer simulation, not a measurement · run {RUN_NAME}"
REGISTRY: list[dict] = []        # every number shown on a chart, for all_headline_numbers.csv


def walk(tokens):
    node = SUMMARY
    for t in tokens:
        node = node[t]
    return node


def path_str(tokens):
    out = ""
    for t in tokens:
        if isinstance(t, int):
            out += f"[{t}]"
        elif t.isidentifier():
            out += ("." if out else "") + t
        else:
            out += f'["{t}"]'
    return out


def find(list_tokens, **match):
    """Index of the one row of a list in summary.json whose fields equal `match`."""
    hits = [i for i, row in enumerate(walk(list_tokens)) if all(row.get(k) == v for k, v in match.items())]
    assert len(hits) == 1, f"{list_tokens} {match}: expected 1 row, found {len(hits)}"
    return hits[0]


def fmt(x, digits=1, signed=False):
    s = f"{x:.{digits}f}"
    if float(s) == 0:
        return f"{0:.{digits}f}"             # never "-0.0"
    return "+" + s if signed and x > 0 else s


def fmt_optional(x, digits=1, signed=False, missing="unknown"):
    return missing if x is None else fmt(x, digits, signed)


def pretty(s):
    return s.replace("-", UNICODE_MINUS)       # proper minus sign on charts


def num(chart, desc, tokens, unit, digits=1, scale=1.0, signed=False):
    """Read one number, record it for all_headline_numbers.csv, return the ROUNDED value that is plotted."""
    raw = walk(tokens)
    if raw is None:
        REGISTRY.append({"chart": chart, "number": "unknown", "unit": unit, "what": desc,
                         "path": path_str(tokens), "exact": None})
        return None
    raw *= scale
    shown = fmt(raw, digits, signed)
    suffix = "" if scale == 1.0 else f"  (x {scale:g})"
    REGISTRY.append({"chart": chart, "number": shown, "unit": unit, "what": desc,
                     "path": path_str(tokens) + suffix, "exact": raw})
    return float(shown)


def derived(chart, desc, shown, unit, path, exact):
    REGISTRY.append({"chart": chart, "number": shown, "unit": unit, "what": desc, "path": path, "exact": exact})


MM_PER_MODEL_PX = (SUMMARY["reference_table"][0]["white_noise_mm_at_person"]
                   / SUMMARY["reference_table"][0]["white_noise_model_px"])
MM_PX_PATH = ("reference_table[0].white_noise_mm_at_person / reference_table[0].white_noise_model_px")


def register_pace_names(chart):
    i = next(k for k, a in enumerate(SUMMARY["assumptions"]) if "Descent time" in a)
    for shown, what in (("2", "Seconds to go down in the slow pace (label 'Slow (2 s down)')"),
                        ("0.8", "Seconds to go down in the fast pace (label 'Fast (0.8 s down)')")):
        derived(chart, what, shown, "s", f"assumptions[{i}]  (text: 'Descent time 2.0 s (controlled) or 0.8 s (fast)')",
                float(shown))


def register_mdd_definition(chart):
    i = next(k for k, a in enumerate(SUMMARY["assumptions"])
             if a.startswith(("Minimum detectable difference", "Detection threshold")))
    for shown, what in (("95", "Share of truly shallower squats that must be flagged for a difference to count as 'caught'"),
                        ("5", "Largest share of matching squats that may be flagged by mistake (false alarms)")):
        derived(chart, what, shown, "%", f"assumptions[{i}]  (text: 'flags at least 95% of shallow repetitions and at most 5% "
                                         "of matching repetitions')", float(shown))


# ----------------------------------------------------------------------------- figure scaffolding
def wrap_lines(fig, text, size, weight, max_w_in):
    renderer = fig.canvas.get_renderer()
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        t = fig.text(0, 0, trial, fontsize=size, fontweight=weight)
        too_wide = t.get_window_extent(renderer).width / fig.dpi > max_w_in
        t.remove()
        if too_wide and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    return lines


class Canvas:
    """Title, subtitle, optional legend row at the top; notes and the footer at the bottom."""

    def __init__(self, w, h, title, subtitle=None, legend=None, legend_cols=2, notes=()):
        self.w, self.h = w, h
        self.fig = fig = plt.figure(figsize=(w, h), facecolor=BG)
        text_w = w - 2 * MARGIN_IN
        y = h - 0.40
        for line in wrap_lines(fig, title, TITLE_PT, "bold", text_w):
            fig.text(MARGIN_IN / w, y / h, line, fontsize=TITLE_PT, fontweight="bold", va="top", ha="left")
            y -= TITLE_PT * 1.3 / 72
        if subtitle:
            y -= 0.05
            for line in wrap_lines(fig, subtitle, SUB_PT, "normal", text_w):
                fig.text(MARGIN_IN / w, y / h, line, fontsize=SUB_PT, color=MUTED, va="top", ha="left")
                y -= SUB_PT * 1.4 / 72
        if legend:
            y -= 0.12
            fig.legend(handles=legend, loc="upper left", bbox_to_anchor=((MARGIN_IN - 0.05) / w, y / h), ncol=legend_cols,
                       frameon=False, fontsize=SUB_PT, handlelength=1.6, columnspacing=2.4, borderaxespad=0,
                       handletextpad=0.6)
            y -= 0.34
        self.top_in = y - 0.20
        fig.text(MARGIN_IN / w, 0.28 / h, FOOTER, fontsize=FOOT_PT, color=MUTED, va="bottom", ha="left")
        note_lines = []
        for n in notes:
            note_lines += wrap_lines(fig, n, NOTE_PT, "normal", text_w)
        y = 0.28 + 0.33 + len(note_lines) * NOTE_PT * 1.35 / 72
        self.notes_top_in = y
        for line in note_lines:
            fig.text(MARGIN_IN / w, y / h, line, fontsize=NOTE_PT, color=MUTED, va="top", ha="left")
            y -= NOTE_PT * 1.35 / 72

    def grid(self, ncols=1, left_in=1.2, right_in=0.6, axis_in=1.0, head_in=0.0, wspace=0.08):
        bottom = self.notes_top_in + axis_in
        gs = self.fig.add_gridspec(1, ncols, left=left_in / self.w, right=1 - right_in / self.w,
                                   top=(self.top_in - head_in) / self.h, bottom=bottom / self.h, wspace=wspace)
        return [self.fig.add_subplot(gs[0, k]) for k in range(ncols)]

    def save(self, name):
        CHARTS.mkdir(parents=True, exist_ok=True)
        self.fig.savefig(CHARTS / f"{name}.png", dpi=300)
        self.fig.savefig(CHARTS / f"{name}.svg", metadata={"Date": None})
        plt.close(self.fig)


def style_axes(ax, grid_axis="y", hide_left=True):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    if hide_left:
        ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(axis="both", labelsize=TICK_PT, length=0, pad=6)
    ax.grid(axis=grid_axis, color=GRID, linewidth=1.0)
    ax.set_axisbelow(True)


def value_label(ax, x, y, text, **kw):
    kw.setdefault("ha", "center")
    kw.setdefault("va", "bottom")
    ax.text(x, y, text, fontsize=VALUE_PT, fontweight="bold", color=TEXT, **kw)


def write_csv(name, header, rows):
    DATA.mkdir(parents=True, exist_ok=True)
    with open(DATA / name, "w", newline="", encoding="utf-8-sig") as f:   # BOM so Excel reads the symbols correctly
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def pace_legend():
    return [Patch(facecolor=TEAL, label=PACE_NAME["controlled"]), Patch(facecolor=LTEAL, label=PACE_NAME["fast"])]


# ----------------------------------------------------------------------------- shared by charts 1 and 2
def reference_mdd(chart, noise, mode, pace, cond):
    i = find(["reference_table"], mode=mode, pace=pace, white_noise_model_px=noise)
    return num(chart, f"{MDD_PLAIN} - {MODE_NAME[mode]}, {PACE_NAME[pace]}, {cond}",
               ["reference_table", i, "minimum_detectable_difference_mm"], "mm")


def measured_mdd(chart, mode, pace):
    i = find(["extended_sensitivity"], scenario="slow_drift_0_5_model_px", mode=mode, pace=pace)
    return num(chart, f"{MDD_PLAIN} - {MODE_NAME[mode]}, {PACE_NAME[pace]}, {DRIFT}",
               ["extended_sensitivity", i, "minimum_detectable_difference_mm"], "mm")


def grouped_bars(ax, values, chart_max, label_pt=VALUE_PT, width=0.38):
    """values[(mode, pace)] -> bar heights; two bars (slow, fast) per set-up. Returns nothing."""
    for g, (mode, _) in enumerate(MODES):
        for k, (pace, _) in enumerate(PACES):
            v = values[(mode, pace)]
            x = g + (k - 0.5) * (width + 0.02)
            if v is None:
                ax.text(x, chart_max, "not reached", ha="center", va="top", fontsize=label_pt - 2, color=MUTED)
            else:
                ax.bar(x, v, width=width, color=TEAL if pace == "controlled" else LTEAL, zorder=3)
                ax.text(x, v + chart_max * 0.012, f"{v:.1f}", ha="center", va="bottom", fontsize=label_pt, fontweight="bold", color=TEXT,
                        zorder=4)


MODE_TICKS = [name.replace(" (", "\n(") for _, name in MODES]


# ----------------------------------------------------------------------------- chart 1
def chart_1():
    cid = "01_cameras_and_speed"
    values = {(m, p): reference_mdd(cid, 0.5, m, p, CLEAN) for m, _ in MODES for p, _ in PACES}
    register_pace_names(cid)
    register_mdd_definition(cid)
    finite = [v for v in values.values() if v is not None]
    chart_max = max(5, int(np.ceil(max(finite, default=5) / 5) * 5 + 2))
    c = Canvas(11.5, 7.4, "First passing depth change by camera setup and pace",
               "Simulated keypoints, standard noise and baseline frame rate. A lower bar means a smaller training-grid value.", legend=pace_legend(),
               notes=[MDD_NOTE, "The training-selected cutoff and first passing grid point may fail on held-out sessions. The named summary records both counts."])
    (ax,) = c.grid(left_in=1.35, right_in=0.5, axis_in=0.85)
    style_axes(ax)
    grouped_bars(ax, values, chart_max)
    ax.set_xticks(range(4), MODE_TICKS)
    ax.set_xlim(-0.6, 3.6)
    ax.set_ylim(0, chart_max + chart_max * 0.08)
    ax.set_yticks(range(0, chart_max + 1, 5))
    ax.set_ylabel(MDD_NAME, fontsize=LABEL_PT, labelpad=10)
    c.save(cid)
    write_csv(f"{cid}.csv", ["Setup", f"{PACE_NAME['controlled']}: {MDD_NAME}", f"{PACE_NAME['fast']}: {MDD_NAME}"],
              [[name, "not reached" if values[(m, "controlled")] is None else f"{values[(m, 'controlled')]:.1f}",
                "not reached" if values[(m, "fast")] is None else f"{values[(m, 'fast')]:.1f}"] for m, name in MODES])


# ----------------------------------------------------------------------------- chart 2
def chart_2():
    cid = "02_cameras_and_speed_3_conditions"
    panels = []
    for noise, name in ((0.5, CLEAN), (1.0, SHAKY)):
        panels.append((name, {(m, p): reference_mdd(cid, noise, m, p, name) for m, _ in MODES for p, _ in PACES}))
    panels.append((DRIFT, {(m, p): measured_mdd(cid, m, p) for m, _ in MODES for p, _ in PACES}))
    # One-line captions describe the simulated detector-error scenarios.
    clean_i = find(["reference_table"], mode="two_cam", pace="controlled", white_noise_model_px=0.5)
    shaky_i = find(["reference_table"], mode="two_cam", pace="controlled", white_noise_model_px=1.0)
    j_clean = num(cid, f"Hip-point jitter at the person in '{CLEAN}' (1 standard deviation, per phone)",
                  ["reference_table", clean_i, "white_noise_mm_at_person"], "mm", digits=0)
    j_shaky = num(cid, f"Hip-point jitter at the person in '{SHAKY}' (1 standard deviation, per phone)",
                  ["reference_table", shaky_i, "white_noise_mm_at_person"], "mm", digits=0)
    slow_i = find(["extended_sensitivity"], scenario="slow_drift_0_5_model_px", mode="two_cam", pace="controlled")
    slow_px_mm = MM_PER_MODEL_PX * 0.5
    derived(cid, "Slow detector drift sigma in the third panel, per camera/hip (0.5 model px)",
            f"{slow_px_mm:.1f}", "mm", "extended_sensitivity scenario slow_drift_0_5_model_px; 0.5 model px x mm/model px", slow_px_mm)
    captions = [f"jitter {j_clean:.0f} mm", f"jitter {j_shaky:.0f} mm", f"slow drift {slow_px_mm:.1f} mm per camera/hip"]
    register_pace_names(cid)
    register_mdd_definition(cid)
    c = Canvas(16, 7.9, "First passing depth change under three detector conditions",
               "Same four setups and baseline frame rate, across three modeled detector conditions. A lower bar means a smaller training-grid value.",
               legend=pace_legend(),
               notes=["Jitter is independent frame-to-frame hip-point noise; slow drift is correlated noise (1 standard deviation per camera/hip).",
                      MDD_NOTE])
    axes = c.grid(ncols=3, left_in=1.35, right_in=0.4, axis_in=0.85, head_in=0.75, wspace=0.07)
    finite_values = [v for _, vals in panels for v in vals.values() if v is not None]
    top = max(finite_values, default=5)
    chart_top = max(5, int(np.ceil(top / 5) * 5 + 5))
    for k, (ax, (name, vals), cap) in enumerate(zip(axes, panels, captions)):
        style_axes(ax)
        grouped_bars(ax, vals, chart_top, label_pt=13)
        ax.set_xticks(range(4), MODE_TICKS)
        ax.tick_params(axis="x", labelsize=13)
        ax.set_xlim(-0.6, 3.6)
        ax.set_ylim(0, chart_top)
        ax.set_yticks(range(0, chart_top + 1, 5))
        if k:
            ax.tick_params(axis="y", labelleft=False)
        else:
            ax.set_ylabel(MDD_NAME, fontsize=LABEL_PT, labelpad=10)
        ax.text(0.5, 1.115, name, transform=ax.transAxes, ha="center", va="bottom", fontsize=16, fontweight="bold")
        ax.text(0.5, 1.035, cap, transform=ax.transAxes, ha="center", va="bottom", fontsize=NOTE_PT, color=MUTED)
    assert top < chart_top, "tallest bar no longer fits under the shared y-axis limit"
    c.save(cid)
    rows = []
    for name, vals in panels:
        for m, mname in MODES:
            rows.append([name, mname,
                         "not reached" if vals[(m, "controlled")] is None else f"{vals[(m, 'controlled')]:.1f}",
                         "not reached" if vals[(m, "fast")] is None else f"{vals[(m, 'fast')]:.1f}"])
    write_csv(f"{cid}.csv", ["Video condition", "Setup", f"{PACE_NAME['controlled']}: {MDD_NAME}",
                             f"{PACE_NAME['fast']}: {MDD_NAME}"], rows)


# ----------------------------------------------------------------------------- chart 3
RULES = [("extreme", "Old rule (extreme)", ORANGE), ("parabola", "New rule (parabola)", TEAL)]


def chart_3():
    cid = "03_old_vs_new_depth_rule"
    conditions = [(0.5, CLEAN), (1.0, SHAKY)]
    bias, mdd = {}, {}
    for noise, cname in conditions:
        for est, ename, _ in RULES:
            i = find(["estimator_comparison", "rows"], estimator=est, white_noise_model_px=noise, pace="controlled")
            base = ["estimator_comparison", "rows", i]
            what = f"{ename}, 2 phones, slow pace, {cname}"
            bias[(noise, est)] = num(cid, f"Average depth error (positive = squat looks deeper than it was) - {what}",
                                     base + ["mean_depth_error_mm"], "mm", signed=True)
            mdd[(noise, est)] = num(cid, f"{MDD_PLAIN} - {what}", base + ["minimum_detectable_difference_mm"], "mm")
    register_pace_names(cid)
    register_mdd_definition(cid)
    legend = [Patch(facecolor=ORANGE, label=RULES[0][1]), Patch(facecolor=TEAL, label=RULES[1][1])]
    c = Canvas(13.5, 7.9, "Depth estimates under two measurement rules",
               "2 phones, slow squats (2 s down). Old rule = highest standing point minus lowest point; "
               "new rule = a curve fitted around the bottom.", legend=legend,
               notes=["Average depth error above 0 means the squat looks deeper than it really was. " + MDD_NOTE])
    left, right = c.grid(ncols=2, left_in=0.95, right_in=0.4, axis_in=0.7, head_in=0.55, wspace=0.22)
    bias_values = [v for v in bias.values() if v is not None]
    bias_low = min([-2.5, *bias_values])
    bias_high = max([1.0, *bias_values])
    bias_step = max(1, int(np.ceil((bias_high - bias_low) / 5)))
    bias_ticks = range(int(np.floor(bias_low / bias_step) * bias_step), int(np.ceil(bias_high / bias_step) * bias_step) + 1, bias_step)
    mdd_values = [v for v in mdd.values() if v is not None]
    mdd_top = max(5, int(np.ceil(max(mdd_values, default=5) / 5) * 5 + 5))
    for ax, data, title, ylim, ticks, signed in (
            (left, bias, "Average depth error (mm)", (bias_low - 1, bias_high + 2), bias_ticks, True),
            (right, mdd, MDD_NAME, (0, mdd_top), range(0, mdd_top + 1, 5), False)):
        style_axes(ax)
        for g, (noise, _) in enumerate(conditions):
            for k, (est, _, colour) in enumerate(RULES):
                v = data[(noise, est)]
                x = g + (k - 0.5) * 0.42
                if v is None:
                    ax.text(x, 0, "not reached", rotation=90, ha="center", va="bottom", fontsize=NOTE_PT, color=MUTED)
                    continue
                ax.bar(x, v, width=0.40, color=colour, zorder=3)
                if v >= 0:
                    value_label(ax, x, v + 0.3, pretty(fmt(v, 1, signed)))
                else:
                    value_label(ax, x, v - 0.3, pretty(fmt(v, 1, signed)), va="top")
        ax.set_xticks(range(2), [n for _, n in conditions])
        ax.tick_params(axis="x", labelsize=LABEL_PT)
        ax.set_xlim(-0.6, 1.6)
        ax.set_ylim(*ylim)
        ax.set_yticks(list(ticks))
        ax.axhline(0, color=AXIS, linewidth=1.4, zorder=3.5)
        ax.text(0.5, 1.04, title, transform=ax.transAxes, ha="center", va="bottom", fontsize=16, fontweight="bold")
    c.save(cid)
    write_csv(f"{cid}.csv", ["Video condition", "Depth rule", "Average depth error (mm)", MDD_NAME],
              [[cname, ename, "unknown" if bias[(n, est)] is None else fmt(bias[(n, est)], 1, True),
                "not reached" if mdd[(n, est)] is None else f"{mdd[(n, est)]:.1f}"]
               for n, cname in conditions for est, ename, _ in RULES])


# ----------------------------------------------------------------------------- chart 4
def chart_4():
    cid = "04_missed_detections"
    levels = [row["dropout"] for row in SUMMARY["estimator_comparison"]["dropouts"]
              if row["estimator"] == "parabola" and row["pace"] == "controlled"]
    series = {est: [] for est, _, _ in RULES}
    labels = []
    for p in levels:
        label = "0" if p == 0 else f"1 in {round(1 / p)}"
        labels.append(label)
        i0 = find(["estimator_comparison", "dropouts"], estimator="parabola", pace="controlled", dropout=p)
        derived(cid, f"How often a hip goes undetected in a video frame (x-axis label '{label}')", label, "frames",
                f"estimator_comparison.dropouts[{i0}].dropout  (label = 1 in round(1 / {p:g}))" if p else
                f"estimator_comparison.dropouts[{i0}].dropout  (= 0)", p)
        for est, ename, _ in RULES:
            i = find(["estimator_comparison", "dropouts"], estimator=est, pace="controlled", dropout=p)
            series[est].append(num(cid, f"Squats judged 'unclear', {ename}, 2 phones, slow pace, hip undetected {label}",
                                   ["estimator_comparison", "dropouts", i, "unclear_rate"], "%", digits=0, scale=100))
    register_pace_names(cid)
    legend = [Line2D([0], [0], color=ORANGE, lw=3.5, marker="s", markersize=10, label=RULES[0][1]),
              Line2D([0], [0], color=TEAL, lw=3.5, marker="o", markersize=10, label=RULES[1][1])]
    c = Canvas(11.5, 7.4, "Missing hip detections and unclear squat results",
               "Share of simulated squats judged unclear. 2 phones, controlled pace, standard noise.",
               legend=legend, notes=["The x-axis steps are evenly spaced labels, not a true scale."])
    (ax,) = c.grid(left_in=1.3, right_in=0.6, axis_in=1.0)
    style_axes(ax)
    xs = range(len(levels))
    old, new = series["extreme"], series["parabola"]
    ax.plot(xs, old, color=ORANGE, lw=3.5, marker="s", markersize=10, zorder=3, clip_on=False)
    ax.plot(xs, new, color=TEAL, lw=3.5, marker="o", markersize=10, zorder=4, clip_on=False)
    for x, o, n in zip(xs, old, new):
        if o is None and n is None:
            continue
        if o is None or n is None:
            value, offset, align = (n, (9, -9), "left") if o is None else (o, (-9, 8), "right")
            ax.annotate(f"{value:.0f}%", (x, value), xytext=offset, textcoords="offset points", ha=align,
                        fontsize=VALUE_PT, fontweight="bold", color=TEXT)
            continue
        if o == n:                                  # same value: one label
            value_label(ax, x, o + 3.5, f"{o:.0f}%")
        else:
            ax.annotate(f"{o:.0f}%", (x, o), xytext=(-9, 8), textcoords="offset points", ha="right", va="bottom",
                        fontsize=VALUE_PT, fontweight="bold", color=TEXT)
            ax.annotate(f"{n:.0f}%", (x, n), xytext=(9, -9), textcoords="offset points", ha="left", va="top",
                        fontsize=VALUE_PT, fontweight="bold", color=TEXT)
    ax.set_xticks(list(xs), labels)
    ax.set_xlim(-0.45, len(levels) - 0.45)
    ax.set_ylim(-17, 114)
    ax.set_yticks(range(0, 101, 25), [f"{v}%" for v in range(0, 101, 25)])
    ax.set_xlabel("How often a hip goes undetected in a video frame", fontsize=LABEL_PT, labelpad=10)
    ax.set_ylabel("Squats judged 'unclear' (%)", fontsize=LABEL_PT, labelpad=10)
    c.save(cid)
    write_csv(f"{cid}.csv", ["How often a hip goes undetected in a video frame", "Old rule (extreme): squats judged unclear (%)",
                             "New rule (parabola): squats judged unclear (%)"],
              [[l, "unknown" if o is None else f"{o:.0f}", "unknown" if n is None else f"{n:.0f}"] for l, o, n in zip(labels, old, new)])


# ----------------------------------------------------------------------------- chart 5
def chart_5():
    cid = "05_what_matters_most"
    entries = [(i, row) for i, row in enumerate(SUMMARY["extended_sensitivity"])
               if row["mode"] == "two_cam" and row["pace"] == "controlled"]
    names = {"clustered_missing_8_frames": "Shared gaps · 8 frames",
             "motion_dependent_noise_100pct": "Motion noise · +100% at peak",
             "camera_specific_bias_0_5_px": "Camera bias · 0.5 image px",
             "shared_vertical_error_4mm": "Shared vertical error · 4 mm",
             "slow_drift_0_5_model_px": "Slow drift · 0.5 model px",
             "two_camera_offset_1_frame": "Clock offset · 1 frame",
             "camera_center_error_10mm": "Camera centre error · 10 mm",
             "camera_rotation_error_0_5deg": "Camera rotation error · 0.5°"}
    labels = [names.get(row["scenario"], row["scenario"]) for _, row in entries]
    values = [row["minimum_detectable_difference_mm"] for _, row in entries]
    baseline_i = find(["reference_table"], mode="two_cam", white_noise_model_px=0.5, pace="controlled")
    baseline = num(cid, "Baseline first passing training-grid value (two cameras, controlled pace)",
                   ["reference_table", baseline_i, "minimum_detectable_difference_mm"], "mm")
    register_pace_names(cid)
    c = Canvas(15, 8.6, "First passing depth change under modelled errors",
               f"Two phones at the controlled pace. Baseline first passing change (mm): {fmt_optional(baseline, missing='not reached')}. Counts use held-out sessions.",
               notes=["Bars show the first passing tested grid value from training; no interpolation. Held-out counts evaluate that frozen cutoff. "
                      "These are model settings, not measured phone effects. Conditions are not ranked by causal importance."])
    (ax,) = c.grid(left_in=3.35, right_in=5.3, axis_in=0.9, head_in=0.28)
    columns = (1.03, 1.29, 1.55)
    for column, title in zip(columns, ("False alarms", "Shallow flags", "Both limits")):
        ax.text(column, 1.015, title, transform=ax.transAxes, va="bottom", ha="left",
                fontsize=LABEL_PT, fontweight="bold")
    style_axes(ax, grid_axis="x")
    for j, ((i, row), value) in enumerate(zip(entries, values)):
        if value is None:
            ax.text(0.2, j, "not reached on tested grid", va="center", fontsize=VALUE_PT, color=MUTED)
        else:
            shown = num(cid, f"First passing training-grid value: {labels[j]}",
                        ["extended_sensitivity", i, "minimum_detectable_difference_mm"], "mm")
            ax.barh(j, shown, height=0.62, color=TEAL, zorder=3)
            value_label(ax, shown + 0.12, j, fmt(shown, 1), ha="left", va="center")
        bracket = row["tested_grid_bracket_mm"]
        fa = bracket["heldout_matching_counts"]
        det = bracket["heldout_shallow_counts"]
        counts = (f"{fa['false_alarms']} / {fa['matching_total']}", f"{det['detected_shallow']} / {det['shallow_total']}",
                  "pass" if bracket["passes_on_heldout_sessions"] else "fail")
        for column, count in zip(columns, counts):
            ax.text(column, j, count, transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=LABEL_PT)
        REGISTRY.append({"chart": cid, "number": f"{fa['false_alarms']}/{fa['matching_total']}; {det['detected_shallow']}/{det['shallow_total']}",
                         "unit": "counts", "what": f"Held-out false alarms and detections: {labels[j]}",
                         "path": f"extended_sensitivity[{i}].tested_grid_bracket_mm held-out counts", "exact": None})
    ax.set_yticks(range(len(labels)), labels)
    ax.set_ylim(-0.55, len(labels) - 0.45)
    ax.tick_params(axis="y", labelsize=TICK_PT)
    ax.invert_yaxis()
    chart_max = max(5, int(np.ceil(max((v or 0) for v in values) / 5) * 5 + 5))
    ax.set_xlim(0, chart_max)
    ax.set_xticks(range(0, chart_max + 1, 5))
    ax.spines["left"].set_visible(False)
    ax.set_xlabel(MDD_NAME, fontsize=LABEL_PT, labelpad=10)
    c.save(cid)
    write_csv(f"{cid}.csv", ["Modeled sensitivity condition", "First passing training-grid value (mm)", "Held-out false alarms", "Held-out shallow detections", "Held-out result"],
              [[labels[j], "not reached" if values[j] is None else fmt(values[j]),
                f"{row['tested_grid_bracket_mm']['heldout_matching_counts']['false_alarms']}/{row['tested_grid_bracket_mm']['heldout_matching_counts']['matching_total']}",
                f"{row['tested_grid_bracket_mm']['heldout_shallow_counts']['detected_shallow']}/{row['tested_grid_bracket_mm']['heldout_shallow_counts']['shallow_total']}",
                "pass" if row['tested_grid_bracket_mm']['passes_on_heldout_sessions'] else "fail"]
               for j, (_, row) in enumerate(entries)])


# ----------------------------------------------------------------------------- chart 6
def chart_6():
    cid = "06_detection_curve"
    series = [("two_cam", "2 phones", TEAL, "o", 3.0, 4), ("oblique_1cam", "1 phone (front-oblique)", ORANGE, "s", 5.0, 3)]
    curve_i = find(["detection_curves_default_rule"], mode="two_cam", pace="controlled", white_noise_model_px=0.5)
    keys = sorted(SUMMARY["detection_curves_default_rule"][curve_i]["by_true_difference_cm"], key=float)
    xs = [float(k) for k in keys]
    data = {}
    for mode, name, *_ in series:
        i = find(["detection_curves_default_rule"], mode=mode, pace="controlled", white_noise_model_px=0.5)
        data[mode] = [num(cid, f"Squats flagged as shallower by the default 3 cm rule - {name}, slow pace, clean video, "
                               f"true difference {k} cm",
                          ["detection_curves_default_rule", i, "by_true_difference_cm", k, "flagged_shallower"], "%",
                          digits=1, scale=100) for k in keys]
    i2 = find(["detection_curves_default_rule"], mode="two_cam", pace="controlled", white_noise_model_px=0.5)
    line_cm = num(cid, "Position of the decision line: the default tolerance of the rule",
                  ["detection_curves_default_rule", i2, "tolerance_mm"], "cm", digits=0, scale=0.1)
    register_pace_names(cid)
    bias_i = find(["reference_table"], mode="oblique_1cam", pace="controlled", white_noise_model_px=0.5)
    bias = num(cid, "Magnitude of mean depth underestimate, 1 front-oblique phone, slow pace, standard noise",
               ["reference_table", bias_i, "mean_depth_error_mm"], "mm", digits=0, scale=-1)
    c = Canvas(11.5, 7.8, f"Fixed {line_cm:.0f} cm rule: simulated flag rates by true depth change",
               "Share of truly shallower squats flagged. Controlled pace, standard noise. This fixed-rule curve is not a training-grid or held-out result.",
               legend=[Line2D([0], [0], color=col, lw=3.6, marker=mk, markersize=9, label=name)
                       for _, name, col, mk, _, _ in series],
    notes=[(f"In this camera layout, the front-oblique estimate was about {bias:.0f} mm too shallow on average. "
            "The direction and size depend on camera placement and movement; this is not a general correction.")
           if bias is not None else "Mean depth bias is unknown in this summary."])
    (ax,) = c.grid(left_in=1.3, right_in=0.6, axis_in=1.15)
    style_axes(ax)
    ax.axvline(line_cm, color=TEXT, linestyle=(0, (5, 4)), linewidth=1.8, zorder=2)
    ax.text(line_cm - 0.12, 101, f"decision line ({line_cm:.0f} cm)", ha="right", va="center", fontsize=SUB_PT,
            color=TEXT)
    for (mode, name, col, mk, lw, z) in series:
        plotted = [np.nan if value is None else value for value in data[mode]]
        ax.plot(xs, plotted, color=col, lw=lw, marker=mk, markersize=lw + 4.5, zorder=z, clip_on=False)
    # Annotate the tested values at and immediately above the fixed decision line, if present.
    decision_points = [i for i, value in enumerate(xs) if value >= line_cm]
    for index in decision_points[:2]:
        for j, (mode, _name, _col, _mk, _lw, _z) in enumerate(series):
            value = data[mode][index]
            if value is not None:
                ax.annotate(f"{value:.1f}%", (xs[index], value), xytext=((-12 if j == 0 else 12), 5 if j == 0 else -9),
                            textcoords="offset points", ha=("right" if j == 0 else "left"),
                            va=("bottom" if j == 0 else "top"), fontsize=VALUE_PT, fontweight="bold", color=TEXT)
    xmax = max(xs, default=line_cm)
    ax.set_xlim(min(-0.25, min(xs, default=0) - 0.25), xmax + max(0.25, (xmax - min(xs, default=0)) * 0.03))
    ax.set_ylim(-5, 108)
    tick_step = 1 if xmax <= 9 else max(1, int(np.ceil(xmax / 8)))
    ax.set_xticks(np.arange(0, xmax + tick_step, tick_step))
    ax.set_yticks(range(0, 101, 25), [f"{v}%" for v in range(0, 101, 25)])
    ax.set_xlabel("How much shallower the squat really was (cm)", fontsize=LABEL_PT, labelpad=10)
    ax.set_ylabel("Squats flagged as shallower (%)", fontsize=LABEL_PT, labelpad=10)
    c.save(cid)
    write_csv(f"{cid}.csv", ["How much shallower the squat really was (cm)", "2 phones: squats flagged as shallower (%)",
                             "1 phone (front-oblique): squats flagged as shallower (%)"],
              [[f"{x:g}", "unknown" if a is None else f"{a:.1f}", "unknown" if b is None else f"{b:.1f}"]
               for x, a, b in zip(xs, data["two_cam"], data["oblique_1cam"])])


# ----------------------------------------------------------------------------- tables 7 and 8
def table_7():
    rows = []
    for i, r in enumerate(SUMMARY["pause_at_bottom"]):
        base = ["pause_at_bottom", i]
        share = lambda k: f"{r['bottom_model_share'][k] * 100:.0f}"
        rows.append([PACE_NAME[r["pace"]], fmt_optional(r.get("dwell_s")), fmt_optional(r.get("mean_depth_error_mm"), 1, True),
                     fmt_optional(r.get("sd_depth_error_mm")), share("parabola"), share("plateau"), share("none"), share("missing"),
                     fmt_optional(None if r.get("unclear_rate") is None else r["unclear_rate"] * 100, 0),
                     fmt_optional(r.get("minimum_detectable_difference_mm"), missing="not reached on tested grid")])
    write_csv("07_pause_at_bottom.csv",
              ["Pace", "Pause at the bottom (seconds)", "Average depth error (mm)", "Spread of depth error, 1 st. dev. (mm)",
               "Bottom read as a curve (%)", "Bottom read as a flat plateau (%)", "Bottom not seen well enough (%)",
               "Squat not found at all (%)", "Squats judged unclear (%)", MDD_NAME], rows)


def table_8():
    rows = []
    for r in SUMMARY["estimator_comparison"]["calibration"]:
        drift = ("No slow drift" if r["slow_noise_model_px"] == 0
                 else f"With slow drift ({r['slow_noise_model_px'] * MM_PER_MODEL_PX:.0f} mm)")
        video = CLEAN if r["white_noise_model_px"] == 0.5 else SHAKY
        rows.append([video, drift, PACE_NAME[r["pace"]], f"{r['mean_reported_depth_se_mm']:.2f}",
                     f"{r['empirical_sd_depth_error_mm']:.2f}", f"{r['ratio_reported_to_empirical'] * 100:.0f}"])
    write_csv("08_error_bar_check.csv",
              ["Video condition", "Slow drift in hip position", "Pace", "Error bar the software reports (mm)",
               "Actual spread of the depth error (mm)", "Reported error bar as % of actual spread"], rows)


# ----------------------------------------------------------------------------- headline numbers
def headline_numbers():
    rows = []
    for e in REGISTRY:
        rows.append([e["chart"], e["number"], e["unit"], e["what"], e["path"],
                     "" if e["exact"] is None else f"{e['exact']:.4f}"])
    write_csv("all_headline_numbers.csv",
              ["Chart", "Number shown", "Unit", "What it is", "Key path in summary.json", "Unrounded value"], rows)
    return len(rows)


def main():
    for d in (CHARTS, DATA, ORIG):
        d.mkdir(parents=True, exist_ok=True)
    for name in ORIGINAL_FILES:
        if (SRC / name).is_file():
            shutil.copy2(SRC / name, ORIG / name)
    for f in (chart_1, chart_2, chart_3, chart_4, chart_5, chart_6):
        f()
    table_7()
    table_8()
    n = headline_numbers()
    print(f"wrote 6 charts (png + svg), 8 tables and {n} headline numbers under {OUT}")


if __name__ == "__main__":
    main()
