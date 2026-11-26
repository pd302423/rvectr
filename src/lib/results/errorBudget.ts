/**
 * Results of the Rvectr error-budget simulation.
 *
 * EVERY NUMBER IN THIS FILE COMES FROM A COMPUTER SIMULATION, NOT FROM A
 * MEASUREMENT. No real two-phone footage has been recorded yet. Do not present
 * these values as measured results anywhere on the site.
 *
 * Values are copied from the compact summary of one reproducible simulation run.
 */

import simulation from "./simulation-summary.json";

export const SOURCE_RUN = simulation.created_utc;
export const SIMULATION_SEED = simulation.seed;
export const SIMULATION_CODE_VERSION = simulation.code_version;
export const SIMULATION_SOURCE_DIRTY = simulation.source_dirty;
export const SIMULATION_SESSION_COUNT = simulation.sessions_per_condition;
export const SIMULATION_INFO = simulation;
export const TARGETED_3MM = simulation.targeted_3mm_heldout;

/** Used in captions and footers. */
export const SIMULATION_SETUP =
  `${SIMULATION_SESSION_COUNT} sessions per condition, ${simulation.settings.session_test_repetitions} test squats each, seed ${SIMULATION_SEED}; baseline ${simulation.settings.baseline_frame_rate_fps} fps with ${simulation.settings.frame_rate_sensitivity_fps[0]} fps sensitivity; the separate 3 mm check uses ${TARGETED_3MM.sessions_for_threshold} cutoff-training and ${TARGETED_3MM.sessions_held_out} held-out sessions.`;

export const DEFAULT_TOLERANCE_CM = simulation.settings.pipeline_defaults_squat.tolerance_m * 100;

export interface FixedRulePoint {
  differenceCm: number;
  twoCameraFlaggedPercent: number | null;
  twoCameraUnclearPercent: number | null;
  twoCameraMissedPercent: number | null;
  angledFlaggedPercent: number | null;
  angledUnclearPercent: number | null;
  angledMissedPercent: number | null;
}

function defaultRuleRow(mode: string) {
  const row = simulation.detection_curves_default_rule.find(
    (item) => item.mode === mode && item.white_noise_model_px === 0.5 && item.pace === "controlled",
  );
  if (!row) throw new Error(`Missing fixed-rule curve: ${mode}`);
  return row.by_true_difference_cm as Record<string, {
    flagged_shallower?: number | null;
    unclear?: number | null;
    total?: number | null;
    flagged_count?: number | null;
    unclear_count?: number | null;
    missed_count?: number | null;
  }>;
}

const twoCameraFixedRule = defaultRuleRow("two_cam");
const angledFixedRule = defaultRuleRow("oblique_1cam");
export const FIXED_RULE_CURVE: readonly FixedRulePoint[] = Object.keys(twoCameraFixedRule)
  .map(Number)
  .sort((a, b) => a - b)
  .map((differenceCm) => {
    const key = String(differenceCm);
    const two = twoCameraFixedRule[key];
    const angled = angledFixedRule[key];
    const percent = (value: number | null | undefined, count?: number | null, total?: number | null) =>
      total && count != null ? count / total * 100 : value == null ? null : value * 100;
    return {
      differenceCm,
      twoCameraFlaggedPercent: percent(two?.flagged_shallower, two?.flagged_count, two?.total),
      twoCameraUnclearPercent: percent(two?.unclear, two?.unclear_count, two?.total),
      twoCameraMissedPercent: percent(undefined, two?.missed_count, two?.total),
      angledFlaggedPercent: percent(angled?.flagged_shallower, angled?.flagged_count, angled?.total),
      angledUnclearPercent: percent(angled?.unclear, angled?.unclear_count, angled?.total),
      angledMissedPercent: percent(undefined, angled?.missed_count, angled?.total),
    };
  });

export const NOISE_DEFINITIONS =
  "Noise levels are simulated settings, not estimates from phone recordings. Hip-point noise is set in \"model pixels\" (one pixel of the small, shrunk picture the pose model works on) and converted to millimetres at the simulated person.";

/* ------------------------------------------------------------------ */
/* 1. Camera count                                                      */
/* ------------------------------------------------------------------ */

export type ScenarioKey = "clean" | "noisy" | "drift";

export type SetupId = "one-side" | "one-angled" | "two" | "three";

export interface CameraSetup {
  id: SetupId;
  label: string;
}

/** Order matters: it is the order the bars are drawn in. */
export const CAMERA_SETUPS: readonly CameraSetup[] = [
  { id: "one-side", label: "1 phone, side" },
  { id: "one-angled", label: "1 phone, angled" },
  { id: "two", label: "2 phones" },
  { id: "three", label: "3 phones" },
];

export interface PaceValues {
  /** First passing training-grid value; null when no value passed in training. */
  controlled: number | null;
  /** First passing training-grid value; null when no value passed in training. */
  fast: number | null;
}

export interface Scenario {
  key: ScenarioKey;
  /** Text on the toggle button. */
  label: string;
  /** One-line reading shown under the toggle. */
  note: string;
  /** One entry per CAMERA_SETUPS item, same order. */
  values: readonly PaceValues[];
}

const modes = ["side_1cam", "oblique_1cam", "two_cam", "three_cam"] as const;
const modeLabels = ["1 phone, side", "1 phone, angled", "2 phones", "3 phones"] as const;
export const GRID_LIMIT_MM = Math.max(...simulation.settings.reference_grid_cm) * 10;
const gridLimitMm = GRID_LIMIT_MM;
const referenceValue = (noise: number, mode: string, pace: "controlled" | "fast") => {
  const row = simulation.reference_table.find(
    (item) => item.mode === mode && item.white_noise_model_px === noise && item.pace === pace,
  );
  if (!row) throw new Error(`Missing reference simulation row: ${mode}, ${noise}, ${pace}`);
  return row.minimum_detectable_difference_mm;
};
const driftValue = (mode: string, pace: "controlled" | "fast") => {
  const row = simulation.extended_sensitivity.find(
    (item) => item.scenario === "slow_drift_0_5_model_px" && item.mode === mode && item.pace === pace,
  );
  if (!row) throw new Error(`Missing slow-drift simulation row: ${mode}, ${pace}`);
  return row.minimum_detectable_difference_mm;
};

export const SCENARIOS: readonly Scenario[] = [
  {
    key: "clean",
    label: "Lower random noise",
    note: "Random error in each hip point, drawn separately for every camera, hip and image direction: 0.5 model pixel.",
    values: modes.map((mode) => ({ controlled: referenceValue(0.5, mode, "controlled"), fast: referenceValue(0.5, mode, "fast") })),
  },
  {
    key: "noisy",
    label: "Higher random noise",
    note: "The same random error, doubled to 1.0 model pixel. This is a test setting, not an estimate for real phones.",
    values: modes.map((mode) => ({ controlled: referenceValue(1.0, mode, "controlled"), fast: referenceValue(1.0, mode, "fast") })),
  },
  {
    key: "drift",
    label: "Slow drift",
    note: "Error that wanders slowly instead of jumping about, drawn separately for every camera, hip and image direction: 0.5 model pixel. Not measured from phones.",
    values: modes.map((mode) => ({ controlled: driftValue(mode, "controlled"), fast: driftValue(mode, "fast") })),
  },
];

export function detectionDetails(scenario: ScenarioKey) {
  const rows = modes.flatMap((mode, i) => (["controlled", "fast"] as const).map((pace) => {
    const item = scenario === "drift"
      ? simulation.extended_sensitivity.find((row) => row.scenario === "slow_drift_0_5_model_px" && row.mode === mode && row.pace === pace)
      : simulation.reference_table.find((row) => row.mode === mode && row.white_noise_model_px === (scenario === "clean" ? 0.5 : 1.0) && row.pace === pace);
    if (!item) throw new Error(`Missing simulation detail: ${scenario}, ${mode}, ${pace}`);
    const bracket = item.tested_grid_bracket_mm;
    return {
      mode: modeLabels[i], pace,
      lowerTestedMm: bracket.lower_tested_mm,
      trainingGridMm: bracket.first_passing_tested_mm,
      heldoutFalseAlarms: bracket.heldout_matching_counts,
      heldoutDetection: bracket.heldout_shallow_counts,
      heldoutPass: bracket.passes_on_heldout_sessions,
    };
  }));
  return rows;
}

/** Top of the bar-chart axis, in mm. */
export const CAMERA_CHART_MAX_MM = Math.max(20, Math.ceil(gridLimitMm / 10) * 10);

export interface HeadlineNumber {
  phones: 1 | 2 | 3;
  /** First training-grid value meeting the criteria, mm; null means no pass on the grid. */
  mm: number | null;
  label: string;
  heldout: { falseAlarms: number; falseAlarmTotal: number; shallowDetected: number; shallowTotal: number; pass: boolean };
}

const headlineHeldout = (mode: string) => {
  const row = detectionDetails("clean").find((item) => item.mode === mode && item.pace === "controlled");
  if (!row) throw new Error(`Missing held-out headline result: ${mode}`);
  return {
    falseAlarms: row.heldoutFalseAlarms.false_alarms,
    falseAlarmTotal: row.heldoutFalseAlarms.matching_total,
    shallowDetected: row.heldoutDetection.detected_shallow,
    shallowTotal: row.heldoutDetection.shallow_total,
    pass: row.heldoutPass,
  };
};

/**
 * The three headline numbers. They are the "clean video", controlled-pace
 * values from SCENARIOS (1 phone = side view).
 */
export const HEADLINE_NUMBERS: readonly HeadlineNumber[] = [
  {
    phones: 1,
    mm: SCENARIOS[0].values[0].controlled,
    label: "1 phone from the side",
    heldout: headlineHeldout(modeLabels[0]),
  },
  {
    phones: 2,
    mm: SCENARIOS[0].values[2].controlled,
    label: "2 phones at the simulated placement",
    heldout: headlineHeldout(modeLabels[2]),
  },
  {
    phones: 3,
    mm: SCENARIOS[0].values[3].controlled,
    label: "3 phones at the simulated placement",
    heldout: headlineHeldout(modeLabels[3]),
  },
];

/** Absolute average bias in the angled one-camera scenario for the simulated layout. */
const angledReference = simulation.reference_table.find(
  (item) => item.mode === "oblique_1cam" && item.white_noise_model_px === 0.5 && item.pace === "controlled",
);
export const ANGLED_PHONE_BIAS_MM = Math.round(Math.abs(angledReference?.mean_depth_error_mm ?? 0));

/* ------------------------------------------------------------------ */
/* 2. Old rule versus new rule                                          */
/* ------------------------------------------------------------------ */

export type ValueKind = "signedMm" | "mm" | "count";

export interface OldVsNewRow {
  measure: string;
  kind: ValueKind;
  oldRule: number | null;
  newRule: number | null;
}

const estimatorRow = (estimator: string, noise: number) => {
  const row = simulation.estimator_comparison.rows.find(
    (item) => item.estimator === estimator && item.white_noise_model_px === noise && item.pace === "controlled",
  );
  if (!row) throw new Error(`Missing estimator simulation row: ${estimator}, ${noise}`);
  return row;
};
const extraRepRow = (estimator: string) => {
  const row = simulation.estimator_comparison.extra_reps_2px.find(
    (item) => item.estimator === estimator && item.pace === "controlled",
  );
  if (!row) throw new Error(`Missing extra-repetition simulation row: ${estimator}`);
  return row.extra_detected_reps_per_session;
};
export const OLD_VS_NEW: readonly OldVsNewRow[] = [
  { measure: "Average depth error, lower random noise", kind: "signedMm", oldRule: estimatorRow("extreme", 0.5).mean_depth_error_mm, newRule: estimatorRow("parabola", 0.5).mean_depth_error_mm },
  { measure: "Average depth error, higher random noise", kind: "signedMm", oldRule: estimatorRow("extreme", 1.0).mean_depth_error_mm, newRule: estimatorRow("parabola", 1.0).mean_depth_error_mm },
  { measure: "Smallest passing depth change (first half of sessions), lower random noise", kind: "mm", oldRule: estimatorRow("extreme", 0.5).minimum_detectable_difference_mm, newRule: estimatorRow("parabola", 0.5).minimum_detectable_difference_mm },
  { measure: "Extra repetitions found per take, random noise of 2 model pixels", kind: "count", oldRule: extraRepRow("extreme"), newRule: extraRepRow("parabola") },
];

const MINUS = "−";

export function formatValue(value: number | null, kind: ValueKind): string {
  if (value === null) return kind === "mm" ? `not reached (tested up to ${gridLimitMm.toFixed(0)} mm)` : "not reached";
  const abs = Math.abs(value).toFixed(1);
  switch (kind) {
    case "signedMm":
      return `${value < 0 ? MINUS : "+"}${abs} mm`;
    case "mm":
      return `${abs} mm`;
    case "count":
      // "0" reads better than "0.0" for a count that is exactly zero.
      return value === 0 ? "0" : abs;
  }
}

export interface DropoutSeries {
  /** How often a hip goes undetected, per phone, per frame. One label per point. */
  labels: readonly string[];
  /** Share of squats judged "unclear", percent. Same length as labels. */
  oldRule: readonly (number | null)[];
  newRule: readonly (number | null)[];
}

const dropoutRows = simulation.estimator_comparison.dropouts
  .filter((row) => row.pace === "controlled")
  .filter((row, index, rows) => rows.findIndex((other) => other.dropout === row.dropout) === index)
  .sort((a, b) => a.dropout - b.dropout);
export const DROPOUTS: DropoutSeries = {
  labels: dropoutRows.map((row) => row.dropout === 0 ? "0" : `1 in ${Math.round(1 / row.dropout)}`),
  oldRule: dropoutRows.map((row) => {
    const value = simulation.estimator_comparison.dropouts.find((item) => item.estimator === "extreme" && item.pace === "controlled" && item.dropout === row.dropout)!.unclear_rate;
    return value == null ? null : Math.round(100 * value);
  }),
  newRule: dropoutRows.map((row) => {
    const value = simulation.estimator_comparison.dropouts.find((item) => item.estimator === "parabola" && item.pace === "controlled" && item.dropout === row.dropout)!.unclear_rate;
    return value == null ? null : Math.round(100 * value);
  }),
};

/* ------------------------------------------------------------------ */
/* 3. Error budget                                                      */
/* ------------------------------------------------------------------ */

export interface ErrorSource {
  label: string;
  /** Training-selected first passing tested grid point; null if no point passed. */
  trainingMddMm: number | null;
  falseAlarms: number;
  falseAlarmTotal: number;
  detectedShallow: number;
  shallowTotal: number;
  heldoutPass: boolean;
}

const SENSITIVITY_LABELS: Record<string, string> = {
  clustered_missing_8_frames: "Bursts of missing detections (8 frames)",
  motion_dependent_noise_100pct: "Noise that grows with movement (100%)",
  camera_specific_bias_0_5_px: "Constant error for each camera (0.5 image pixel)",
  shared_vertical_error_4mm: "Vertical error shared by all cameras (4 mm)",
  slow_drift_0_5_model_px: "Slow drift in hip points (0.5 model pixel)",
  two_camera_offset_1_frame: "Timing offset between two cameras (1 frame)",
  camera_center_error_10mm: "Camera position error (10 mm)",
  camera_rotation_error_0_5deg: "Camera angle error (0.5°)",
};
const baselineRow = simulation.reference_table.find((row) => row.mode === "two_cam" && row.white_noise_model_px === 0.5 && row.pace === "controlled");
if (!baselineRow) throw new Error("Missing two-camera baseline simulation row");
export const ERROR_BUDGET_BASELINE_MM = baselineRow.minimum_detectable_difference_mm;
export const ERROR_BUDGET: readonly ErrorSource[] = simulation.extended_sensitivity
  .filter((row) => row.mode === "two_cam" && row.pace === "controlled")
  .map((row) => {
    const bracket = row.tested_grid_bracket_mm;
    return {
      label: SENSITIVITY_LABELS[row.scenario] ?? row.scenario,
      trainingMddMm: row.minimum_detectable_difference_mm,
      falseAlarms: bracket.heldout_matching_counts.false_alarms,
      falseAlarmTotal: bracket.heldout_matching_counts.matching_total,
      detectedShallow: bracket.heldout_shallow_counts.detected_shallow,
      shallowTotal: bracket.heldout_shallow_counts.shallow_total,
      heldoutPass: bracket.passes_on_heldout_sessions,
    };
  });
export const ERROR_BUDGET_MAX_MM = Math.ceil(Math.max(1, ...ERROR_BUDGET.map((entry) => entry.trainingMddMm ?? 0)));

/* ------------------------------------------------------------------ */
/* 4. Pauses and edge cases                                             */
/* ------------------------------------------------------------------ */

/** A piece of rich text: plain string, a number (mono) or emphasised word. */
export type TextPart = string | { text: string; style: "num" | "strong" };

export interface PauseCase {
  situation: string;
  outcome: readonly TextPart[];
}

export const PAUSE_CASES: readonly PauseCase[] = [
  ...simulation.pause_at_bottom.filter((row) => row.pace === "controlled" && row.dwell_s > 0).map((row) => ({
    situation: `Rest for ${row.dwell_s.toFixed(1)} s at the bottom`,
    outcome: [
      "Mean depth error: ",
      { text: `${row.mean_depth_error_mm >= 0 ? "+" : ""}${row.mean_depth_error_mm.toFixed(1)} mm`, style: "num" as const },
      `; parabola ${Math.round(100 * row.bottom_model_share.parabola)}%, plateau ${Math.round(100 * row.bottom_model_share.plateau)}%, unclear ${Math.round(100 * row.unclear_rate)}%.`,
    ],
  })),
  {
    situation: "Recording stops while you are still down",
    outcome: ["Marks the squat ", { text: "unclear", style: "strong" }, " instead of guessing."],
  },
  {
    situation: "A hole in the data right at the bottom",
    outcome: ["Marks the squat ", { text: "unclear", style: "strong" }, "."],
  },
];

/* ------------------------------------------------------------------ */
/* 5. What this does not show yet                                       */
/* ------------------------------------------------------------------ */

export const NOT_SHOWN_YET: readonly string[] = [
  "No real phone has been tested. Noise, motion, timing and calibration values are model settings, not measured phone distributions.",
  "The pilot will compare marker displacement, stick lengths and measured stool heights, while retaining misses and unclear attempts.",
  "The simulation leaves out several production effects, including pose-model failures, lens distortion, hip swaps, loose clothing and real camera-to-camera error correlation.",
];
