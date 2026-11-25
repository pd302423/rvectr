"""Make poster-quality charts and data tables from the squat-depth error-budget simulation.

    uv run --no-sync python tools/make_poster_charts.py

SIMULATION, NOT A MEASUREMENT. Every number is read from
outputs/sim/error_budget_20261116T041515Z/summary.json (nothing is typed in by hand) and
every number that appears on a chart is listed, with its key path in summary.json, in
outputs/poster_kit/data/all_headline_numbers.csv.

Writes (only under outputs/poster_kit/):
    charts/NN_name.png   300 dpi
    charts/NN_name.svg   vector, text converted to outlines so it looks the same on any computer
    data/NN_name.csv     exactly the numbers plotted (mm rounded to 1 decimal, percentages to whole numbers)
    data/07_pause_at_bottom.csv, data/08_error_bar_check.csv, data/all_headline_numbers.csv
    original_simulation_output/   copies of the original run files
Does not re-run the simulation and does not touch the original run folder.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RUN_NAME = "error_budget_20261116T041515Z"          # which finished run to read (a folder name, not a result)
SRC = ROOT / "outputs" / "sim" / RUN_NAME
OUT = ROOT / "outputs" / "poster_kit"
CHARTS, DATA, ORIG = OUT / "charts", OUT / "data", OUT / "original_simulation_output"
ORIGINAL_FILES = ("summary.md", "summary.json", "detection_curves.png", "ranking.png", "sweeps.png")

# ----------------------------------------------------------------------------- look
TEAL, LTEAL, ORANGE = "#1f6b5c", "#8fc2b4", "#b5643a"   # new software / slow pace, fast pace, old rule / biggest risk
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
CLEAN, SHAKY, DRIFT = "Clean video", "Shakier hip points", "Shaky + slow drift"
MDD_PLAIN = "Smallest depth change it can catch"
MDD_NOTE = (f"{MDD_PLAIN} = smallest real difference between two squats spotted at least 95% of the time, "
            "with at most 5% false alarms (best-case threshold).")
MDD_NAME = f"{MDD_PLAIN} (mm)"
UNICODE_MINUS = "−"


# ----------------------------------------------------------------------------- reading summary.json
SUMMARY = json.loads((SRC / "summary.json").read_text(encoding="utf-8"))
FOOTER = f"Computer simulation, not a measurement · run {RUN_NAME}"
assert SUMMARY["created_utc"] == RUN_NAME.split("_")[-1], "summary.json is from a different run than expected"
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


def pretty(s):
    return s.replace("-", UNICODE_MINUS)       # proper minus sign on charts


def num(chart, desc, tokens, unit, digits=1, scale=1.0, signed=False):
    """Read one number, record it for all_headline_numbers.csv, return the ROUNDED value that is plotted."""
    raw = walk(tokens)
    assert raw is not None, f"{path_str(tokens)} is null (target not reached)"
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
    i = next(k for k, a in enumerate(SUMMARY["assumptions"]) if a.startswith("Minimum detectable difference"))
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
    rows = SUMMARY["measured_noise_scenario"]["rows"]
    i = next(k for k, r in enumerate(rows) if r["mode"] == mode and r["pace"] == pace)
    return num(chart, f"{MDD_PLAIN} - {MODE_NAME[mode]}, {PACE_NAME[pace]}, {DRIFT}",
               ["measured_noise_scenario", "rows", i, "minimum_detectable_difference_mm"], "mm")


def grouped_bars(ax, values, label_pt=VALUE_PT, width=0.38):
    """values[(mode, pace)] -> bar heights; two bars (slow, fast) per set-up. Returns nothing."""
    for g, (mode, _) in enumerate(MODES):
        for k, (pace, _) in enumerate(PACES):
            v = values[(mode, pace)]
            x = g + (k - 0.5) * (width + 0.02)
            ax.bar(x, v, width=width, color=TEAL if pace == "controlled" else LTEAL, zorder=3)
            ax.text(x, v + 0.25, f"{v:.1f}", ha="center", va="bottom", fontsize=label_pt, fontweight="bold", color=TEXT,
                    zorder=4)


MODE_TICKS = [name.replace(" (", "\n(") for _, name in MODES]


# ----------------------------------------------------------------------------- chart 1
def chart_1():
    cid = "01_cameras_and_speed"
    values = {(m, p): reference_mdd(cid, 0.5, m, p, CLEAN) for m, _ in MODES for p, _ in PACES}
    register_pace_names(cid)
    register_mdd_definition(cid)
    c = Canvas(11.5, 7.4, "More phones catch smaller changes; fast squats are harder",
               "Clean video. A lower bar means finer detail.", legend=pace_legend(),
               notes=[MDD_NOTE])
    (ax,) = c.grid(left_in=1.35, right_in=0.5, axis_in=0.85)
    style_axes(ax)
    grouped_bars(ax, values)
    ax.set_xticks(range(4), MODE_TICKS)
    ax.set_xlim(-0.6, 3.6)
    ax.set_ylim(0, 7.4)
    ax.set_yticks(range(0, 8))
    ax.set_ylabel(MDD_NAME, fontsize=LABEL_PT, labelpad=10)
    c.save(cid)
    write_csv(f"{cid}.csv", ["Setup", f"{PACE_NAME['controlled']}: {MDD_NAME}", f"{PACE_NAME['fast']}: {MDD_NAME}"],
              [[name, f"{values[(m, 'controlled')]:.1f}", f"{values[(m, 'fast')]:.1f}"] for m, name in MODES])


# ----------------------------------------------------------------------------- chart 2
def chart_2():
    cid = "02_cameras_and_speed_3_conditions"
    panels = []
    for noise, name in ((0.5, CLEAN), (1.0, SHAKY)):
        panels.append((name, {(m, p): reference_mdd(cid, noise, m, p, name) for m, _ in MODES for p, _ in PACES}))
    panels.append((DRIFT, {(m, p): measured_mdd(cid, m, p) for m, _ in MODES for p, _ in PACES}))
    # one-line captions under each panel title, with the jitter / drift sizes read from summary.json
    clean_i = find(["reference_table"], mode="two_cam", pace="controlled", white_noise_model_px=0.5)
    shaky_i = find(["reference_table"], mode="two_cam", pace="controlled", white_noise_model_px=1.0)
    j_clean = num(cid, f"Hip-point jitter at the person in '{CLEAN}' (1 standard deviation, per phone)",
                  ["reference_table", clean_i, "white_noise_mm_at_person"], "mm", digits=0)
    j_shaky = num(cid, f"Hip-point jitter at the person in '{SHAKY}' (1 standard deviation, per phone)",
                  ["reference_table", shaky_i, "white_noise_mm_at_person"], "mm", digits=0)
    j_fast = num(cid, f"Hip-point jitter in '{DRIFT}' (per phone, per hip)",
                 ["measured_noise_scenario", "per_camera_per_hip_white_mm"], "mm", digits=0)
    j_slow = num(cid, f"Slow drift of the hip point in '{DRIFT}' (per phone, per hip)",
                 ["measured_noise_scenario", "per_camera_per_hip_slow_mm"], "mm", digits=0)
    captions = [f"jitter {j_clean:.0f} mm", f"jitter {j_shaky:.0f} mm", f"jitter {j_fast:.0f} mm + slow drift {j_slow:.0f} mm"]
    register_pace_names(cid)
    register_mdd_definition(cid)
    c = Canvas(16, 7.9, "Shakier video makes every setup less sharp, but more phones still help",
               "Same four setups under three video conditions, all on one scale. A lower bar means finer detail.",
               legend=pace_legend(),
               notes=["Jitter = random frame-to-frame error in each hip point; slow drift = the hip point wandering slowly "
                      "(both per phone, 1 standard deviation).",
                      MDD_NOTE])
    axes = c.grid(ncols=3, left_in=1.35, right_in=0.4, axis_in=0.85, head_in=0.75, wspace=0.07)
    top = max(v for _, vals in panels for v in vals.values())
    for k, (ax, (name, vals), cap) in enumerate(zip(axes, panels, captions)):
        style_axes(ax)
        grouped_bars(ax, vals, label_pt=13)
        ax.set_xticks(range(4), MODE_TICKS)
        ax.tick_params(axis="x", labelsize=13)
        ax.set_xlim(-0.6, 3.6)
        ax.set_ylim(0, 21)
        ax.set_yticks(range(0, 21, 5))
        if k:
            ax.tick_params(axis="y", labelleft=False)
        else:
            ax.set_ylabel(MDD_NAME, fontsize=LABEL_PT, labelpad=10)
        ax.text(0.5, 1.115, name, transform=ax.transAxes, ha="center", va="bottom", fontsize=16, fontweight="bold")
        ax.text(0.5, 1.035, cap, transform=ax.transAxes, ha="center", va="bottom", fontsize=NOTE_PT, color=MUTED)
    assert top < 21 - 1.5, "tallest bar no longer fits under the shared y-axis limit"
    c.save(cid)
    rows = []
    for name, vals in panels:
        for m, mname in MODES:
            rows.append([name, mname, f"{vals[(m, 'controlled')]:.1f}", f"{vals[(m, 'fast')]:.1f}"])
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
    c = Canvas(13.5, 7.9, "The new depth rule removes the error that made squats look deeper",
               "2 phones, slow squats (2 s down). Old rule = highest standing point minus lowest point; "
               "new rule = a curve fitted around the bottom.", legend=legend,
               notes=["Average depth error above 0 means the squat looks deeper than it really was. " + MDD_NOTE])
    left, right = c.grid(ncols=2, left_in=0.95, right_in=0.4, axis_in=0.7, head_in=0.55, wspace=0.22)
    for ax, data, title, ylim, ticks, signed in (
            (left, bias, "Average depth error (mm)", (-2.5, 21), range(0, 21, 5), True),
            (right, mdd, MDD_NAME, (0, 18), range(0, 17, 5), False)):
        style_axes(ax)
        for g, (noise, _) in enumerate(conditions):
            for k, (est, _, colour) in enumerate(RULES):
                v = data[(noise, est)]
                x = g + (k - 0.5) * 0.42
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
              [[cname, ename, fmt(bias[(n, est)], 1, True), f"{mdd[(n, est)]:.1f}"]
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
    c = Canvas(11.5, 7.4, "The new rule copes with missing hip detections far better",
               "Share of squats the software refuses to judge ('unclear'). 2 phones, slow squats (2 s down), clean video.",
               legend=legend, notes=["The x-axis steps are evenly spaced labels, not a true scale."])
    (ax,) = c.grid(left_in=1.3, right_in=0.6, axis_in=1.0)
    style_axes(ax)
    xs = range(len(levels))
    old, new = series["extreme"], series["parabola"]
    ax.plot(xs, old, color=ORANGE, lw=3.5, marker="s", markersize=10, zorder=3, clip_on=False)
    ax.plot(xs, new, color=TEAL, lw=3.5, marker="o", markersize=10, zorder=4, clip_on=False)
    for x, o, n in zip(xs, old, new):
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
              [[l, f"{o:.0f}", f"{n:.0f}"] for l, o, n in zip(labels, old, new)])


# ----------------------------------------------------------------------------- chart 5
def ranking_label(cid, i, e):
    """Plain-words name of one error source, with its numbers read from summary.json."""
    s, lv, bl = e["source"], e["plausible_level"], e["baseline_level"]
    lvp, blp = ["ranking", i, "plausible_level"], ["ranking", i, "baseline_level"]
    mm_note = f"ranking[{i}].plausible_level x ({MM_PX_PATH})"

    if s == "slow_noise":
        mm = lv * MM_PER_MODEL_PX
        derived(cid, "Size of the slow drift in hip position at the person", f"{mm:.0f}", "mm", mm_note, mm)
        return f"Slow drift in hip position ({mm:.0f} mm)"
    if s == "white_noise":
        mm, mm0 = lv * MM_PER_MODEL_PX, bl * MM_PER_MODEL_PX
        derived(cid, "Jitter of the hip points when 'shakier'", f"{mm:.0f}", "mm", mm_note, mm)
        derived(cid, "Jitter of the hip points in clean video (the baseline)", f"{mm0:.0f}", "mm",
                f"ranking[{i}].baseline_level x ({MM_PX_PATH})", mm0)
        return f"Shakier hip points ({mm:.0f} mm jitter instead of {mm0:.0f} mm)"
    if s == "frame_rate":
        num(cid, "Frame rate in the 'worse' case", lvp, "fps", digits=0)
        num(cid, "Frame rate of the baseline", blp, "fps", digits=0)
        return f"Recording at {lv:.0f} fps instead of {bl:.0f}"
    if s == "dropouts":
        n = round(1 / lv)
        derived(cid, "A hip point goes undetected in 1 of this many frames", f"{n}", "frames",
                f"ranking[{i}].plausible_level  (n = 1 / {lv:g})", n)
        return f"Hip point missed in 1 of every {n} frames"
    if s == "posture_bias_beta":
        pc = num(cid, "Posture lifts the detected hip by this share of the descent", lvp, "%", digits=0, scale=100)
        return f"Posture lifts the hip point ({pc:.0f}% of the descent)"
    if s == "camera_separation":
        a = num(cid, "Angle between the two phones in the 'worse' case", lvp, "degrees", digits=0)
        b = num(cid, "Angle between the two phones in the baseline", blp, "degrees", digits=0)
        return f"Phones only {a:.0f}° apart instead of {b:.0f}°"
    if s == "sync_error":
        n = num(cid, "Phone timing error in frames", lvp, "frames", digits=0)
        return f"Phone timing off by {n:.0f} frame"
    if s == "scale_error":
        pc = num(cid, "Distance scale too small by this percentage (scale error is negative)", lvp, "%", digits=0, scale=-100)
        return f"Distance scale {pc:.0f}% too small"
    if s == "tilt":
        d = num(cid, "Calibration tilt in degrees", lvp, "degrees", digits=0)
        return f"Calibration tilted by {d:.0f}°"
    raise KeyError(s)


def wrap_bar_label(label, width=34):
    """Wrap a long bar name without splitting a bracketed phrase or 'instead of X' or 'N frames'."""
    glue = lambda m: m.group(0).replace(" ", "\u00a0")
    label = re.sub(r"\([^)]*\)", glue, label)
    label = re.sub(r"instead of \S+", glue, label)
    label = re.sub(r"1 of every \d+ frames", glue, label)
    return "\n".join(textwrap.wrap(label, width)).replace("\u00a0", " ")


def chart_5():
    cid = "05_what_matters_most"
    entries = list(enumerate(SUMMARY["ranking"]))
    entries.sort(key=lambda ie: -ie[1]["controlled"]["change_mm"])           # biggest extra mm first (slow pace)
    labels, vals = [], []
    for i, e in entries:
        labels.append(ranking_label(cid, i, e))
        vals.append(num(cid, f"Extra mm added to the smallest catchable change - {labels[-1]} (slow pace, 2 phones)",
                        ["ranking", i, "controlled", "change_mm"], "mm", signed=True))
    base_i = entries[0][0]
    baseline = num(cid, "Smallest catchable change with no extra errors (2 phones, slow pace, clean video)",
                   ["ranking", base_i, "controlled", "baseline_mdd_mm"], "mm")
    register_pace_names(cid)
    c = Canvas(13.5, 8.6, "Slow drift matters most; phone timing barely matters",
               "Extra millimetres added to the smallest depth change it can catch when one error is set to a plausible level "
               f"and everything else stays at the clean-video baseline of {baseline:.1f} mm. 2 phones, slow squats (2 s down).",
               notes=["0.0 means less than 0.05 mm. A negative bar means the error made things very slightly better."])
    (ax,) = c.grid(left_in=5.35, right_in=0.5, axis_in=0.9)
    style_axes(ax, grid_axis="x")
    ys = list(range(len(labels)))
    ax.barh(ys, vals, height=0.62, color=[ORANGE] + [TEAL] * (len(vals) - 1), zorder=3)
    for y, v in zip(ys, vals):
        value_label(ax, max(v, 0) + 0.12, y, pretty(fmt(v, 1, True)), ha="left", va="center")
    ax.set_yticks(ys, [wrap_bar_label(l) for l in labels])
    ax.tick_params(axis="y", labelsize=TICK_PT)
    ax.invert_yaxis()
    ax.set_xlim(-0.1, 9)
    ax.set_xticks(range(0, 9))
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Extra mm added to the smallest depth change it can catch", fontsize=LABEL_PT, labelpad=10)
    c.save(cid)
    write_csv(f"{cid}.csv", ["Rank", "What goes wrong (plain words)", "Extra mm added to the smallest depth change it can catch"],
              [[r + 1, l, fmt(v, 1, True)] for r, (l, v) in enumerate(zip(labels, vals))])


# ----------------------------------------------------------------------------- chart 6
def chart_6():
    cid = "06_detection_curve"
    series = [("two_cam", "2 phones", TEAL, "o", 3.0, 4), ("oblique_1cam", "1 phone (angled)", ORANGE, "s", 5.0, 3)]
    keys = [k for k in SUMMARY["detection_curves_default_rule"][
        find(["detection_curves_default_rule"], mode="two_cam", pace="controlled", white_noise_model_px=0.5)
    ]["by_true_difference_cm"] if float(k) <= 8]
    xs = [float(k) for k in keys]
    data = {}
    for mode, name, *_ in series:
        i = find(["detection_curves_default_rule"], mode=mode, pace="controlled", white_noise_model_px=0.5)
        data[mode] = [num(cid, f"Squats flagged as shallower by the default 3 cm rule - {name}, slow pace, clean video, "
                               f"true difference {k} cm",
                          ["detection_curves_default_rule", i, "by_true_difference_cm", k, "flagged_shallower"], "%",
                          digits=0, scale=100) for k in keys]
    i2 = find(["detection_curves_default_rule"], mode="two_cam", pace="controlled", white_noise_model_px=0.5)
    line_cm = num(cid, "Position of the decision line: the default tolerance of the rule",
                  ["detection_curves_default_rule", i2, "tolerance_mm"], "cm", digits=0, scale=0.1)
    register_pace_names(cid)
    bias_i = find(["reference_table"], mode="oblique_1cam", pace="controlled", white_noise_model_px=0.5)
    bias = num(cid, "Average depth error of 1 phone (angled), slow pace, clean video (negative = reads too shallow)",
               ["reference_table", bias_i, "mean_depth_error_mm"], "mm", digits=0, scale=-1)
    c = Canvas(11.5, 7.8, "Two phones flag a shallower squat right at the 3 cm line",
               "Share of truly shallower squats flagged by the default 3 cm rule. Slow squats (2 s down), clean video.",
               legend=[Line2D([0], [0], color=col, lw=3.6, marker=mk, markersize=9, label=name)
                       for _, name, col, mk, _, _ in series],
               notes=[f"Why the angled single phone lags: it reads squat depth about {bias:.0f} mm too shallow on average "
                      "(perspective error), so real differences look slightly smaller and fewer reach the 3 cm line."])
    (ax,) = c.grid(left_in=1.3, right_in=0.6, axis_in=1.15)
    style_axes(ax)
    ax.axvline(line_cm, color=TEXT, linestyle=(0, (5, 4)), linewidth=1.8, zorder=2)
    ax.text(line_cm - 0.12, 101, f"decision line ({line_cm:.0f} cm)", ha="right", va="center", fontsize=SUB_PT,
            color=TEXT)
    for (mode, name, col, mk, lw, z) in series:
        ax.plot(xs, data[mode], color=col, lw=lw, marker=mk, markersize=lw + 4.5, zorder=z, clip_on=False)
    # label only the points on the steep part of each curve
    three = keys.index("3")
    ax.annotate(f"{data['two_cam'][three]:.0f}%", (xs[three], data["two_cam"][three]), xytext=(-12, 0),
                textcoords="offset points", ha="right", va="center", fontsize=VALUE_PT, fontweight="bold", color=TEXT)
    ax.annotate(f"{data['oblique_1cam'][three]:.0f}%", (xs[three], data["oblique_1cam"][three]), xytext=(14, 2),
                textcoords="offset points", ha="left", va="center", fontsize=VALUE_PT, fontweight="bold", color=TEXT)
    t35 = keys.index("3.5")
    v35 = data["oblique_1cam"][t35]
    if 0 < v35 < 100:
        ax.annotate(f"{v35:.0f}%", (xs[t35], v35), xytext=(12, -12), textcoords="offset points", ha="left", va="top",
                    fontsize=VALUE_PT, fontweight="bold", color=TEXT)
    ax.set_xlim(-0.25, 8.25)
    ax.set_ylim(-5, 108)
    ax.set_xticks(range(0, 9))
    ax.set_yticks(range(0, 101, 25), [f"{v}%" for v in range(0, 101, 25)])
    ax.set_xlabel("How much shallower the squat really was (cm)", fontsize=LABEL_PT, labelpad=10)
    ax.set_ylabel("Squats flagged as shallower (%)", fontsize=LABEL_PT, labelpad=10)
    c.save(cid)
    write_csv(f"{cid}.csv", ["How much shallower the squat really was (cm)", "2 phones: squats flagged as shallower (%)",
                             "1 phone (angled): squats flagged as shallower (%)"],
              [[f"{x:g}", f"{a:.0f}", f"{b:.0f}"] for x, a, b in zip(xs, data["two_cam"], data["oblique_1cam"])])


# ----------------------------------------------------------------------------- tables 7 and 8
def table_7():
    rows = []
    for i, r in enumerate(SUMMARY["pause_at_bottom"]):
        base = ["pause_at_bottom", i]
        share = lambda k: f"{r['bottom_model_share'][k] * 100:.0f}"
        rows.append([PACE_NAME[r["pace"]], f"{r['dwell_s']:.1f}", fmt(r["mean_depth_error_mm"], 1, True),
                     fmt(r["sd_depth_error_mm"], 1), share("parabola"), share("plateau"), share("none"), share("missing"),
                     f"{r['unclear_rate'] * 100:.0f}", f"{r['minimum_detectable_difference_mm']:.1f}"])
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
        rows.append([e["chart"], e["number"], e["unit"], e["what"], e["path"], f"{e['exact']:.4f}"])
    write_csv("all_headline_numbers.csv",
              ["Chart", "Number shown", "Unit", "What it is", "Key path in summary.json", "Unrounded value"], rows)
    return len(rows)


def main():
    for d in (CHARTS, DATA, ORIG):
        d.mkdir(parents=True, exist_ok=True)
    for name in ORIGINAL_FILES:
        shutil.copy2(SRC / name, ORIG / name)
    for f in (chart_1, chart_2, chart_3, chart_4, chart_5, chart_6):
        f()
    table_7()
    table_8()
    n = headline_numbers()
    print(f"wrote 6 charts (png + svg), 8 tables and {n} headline numbers under {OUT}")


if __name__ == "__main__":
    main()
