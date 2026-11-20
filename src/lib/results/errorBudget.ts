/**
 * Results of the Rvectr error-budget simulation.
 *
 * EVERY NUMBER IN THIS FILE COMES FROM A COMPUTER SIMULATION, NOT FROM A
 * MEASUREMENT. No real two-phone footage has been recorded yet. Do not present
 * these values as measured results anywhere on the site.
 *
 * Source: simulation run `error_budget_20261116T041515Z`.
 */

export const SOURCE_RUN = "error_budget_20261116T041515Z";

/** Used in captions and footers. */
export const SIMULATION_SETUP =
  "300 simulated sessions per setting, 3 test squats each. Phones 3 m away, 1080p portrait at 60 fps.";

export const NOISE_DEFINITIONS =
  "\"Clean video\" = hip points shaking about 4 mm per frame at the person; \"shakier\" = about 8 mm. \"Slow drift\" uses 4 mm fast shake plus 4 mm slow wobble per phone.";

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
  /** Controlled pace: 2 s down, 2 s up. Smallest catchable change, mm. */
  controlled: number;
  /** Fast pace: under 1 s down. Smallest catchable change, mm. */
  fast: number;
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

export const SCENARIOS: readonly Scenario[] = [
  {
    key: "clean",
    label: "Clean video",
    note: "Hip points shake about 4 mm per frame. The best realistic case.",
    values: [
      { controlled: 4.0, fast: 6.2 },
      { controlled: 4.4, fast: 6.6 },
      { controlled: 3.0, fast: 4.7 },
      { controlled: 2.5, fast: 3.4 },
    ],
  },
  {
    key: "noisy",
    label: "Shakier hip points",
    note: "Hip points shake about 8 mm per frame. Every setup gets roughly twice as bad.",
    values: [
      { controlled: 8.0, fast: 12.5 },
      { controlled: 8.6, fast: 13.0 },
      { controlled: 5.9, fast: 9.2 },
      { controlled: 5.0, fast: 6.8 },
    ],
  },
  {
    key: "drift",
    label: "Shaky plus slow drift",
    note: "Shake plus slow wobble. This is the likely real-world range; the extra phones still help.",
    values: [
      { controlled: 14.9, fast: 16.6 },
      { controlled: 15.9, fast: 17.9 },
      { controlled: 10.2, fast: 11.9 },
      { controlled: 8.3, fast: 9.2 },
    ],
  },
];

/** Top of the bar-chart axis, in mm. Large enough for every value above. */
export const CAMERA_CHART_MAX_MM = 20;

export interface HeadlineNumber {
  phones: 1 | 2 | 3;
  /** Smallest catchable depth change, mm (slow squat, clean video). */
  mm: number;
  label: string;
}

/**
 * The three headline numbers. They are the "clean video", controlled-pace
 * values from SCENARIOS (1 phone = side view).
 */
export const HEADLINE_NUMBERS: readonly HeadlineNumber[] = [
  {
    phones: 1,
    mm: SCENARIOS[0].values[0].controlled,
    label: "smallest change 1 phone can catch (side view, slow squat, clean video)",
  },
  {
    phones: 2,
    mm: SCENARIOS[0].values[2].controlled,
    label: "same with 2 phones",
  },
  {
    phones: 3,
    mm: SCENARIOS[0].values[3].controlled,
    label: "same with 3 phones",
  },
];

/** A single phone placed at an angle reads every squat about this much too shallow. */
export const ANGLED_PHONE_BIAS_MM = 12;

/* ------------------------------------------------------------------ */
/* 2. Old rule versus new rule                                          */
/* ------------------------------------------------------------------ */

export type ValueKind = "signedMm" | "mm" | "count";

export interface OldVsNewRow {
  measure: string;
  kind: ValueKind;
  oldRule: number;
  newRule: number;
}

/** Two phones, slow squat. */
export const OLD_VS_NEW: readonly OldVsNewRow[] = [
  { measure: "Average depth error, clean video", kind: "signedMm", oldRule: 8.0, newRule: -0.1 },
  { measure: "Average depth error, shakier hip points", kind: "signedMm", oldRule: 16.7, newRule: -0.1 },
  { measure: "Smallest change it can catch, clean video", kind: "mm", oldRule: 7.3, newRule: 3.0 },
  { measure: "Fake extra squats found per take, very shaky video", kind: "count", oldRule: 1.7, newRule: 0 },
];

const MINUS = "−";

export function formatValue(value: number, kind: ValueKind): string {
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
  oldRule: readonly number[];
  newRule: readonly number[];
}

export const DROPOUTS: DropoutSeries = {
  labels: ["0", "1 in 200", "1 in 100", "1 in 50", "1 in 33", "1 in 20", "1 in 10"],
  oldRule: [0, 6, 17, 30, 47, 99, 100],
  newRule: [0, 0, 0, 0, 14, 98, 100],
};

/* ------------------------------------------------------------------ */
/* 3. Error budget                                                      */
/* ------------------------------------------------------------------ */

export interface ErrorSource {
  label: string;
  /** The realistic level the simulation used. Empty when the label says it all. */
  level: string;
  /** Extra millimetres added to the smallest catchable change. */
  extraMm: number;
}

/** Two phones, slow squat, starting from 3.0 mm. Sorted from biggest to smallest. */
export const ERROR_BUDGET: readonly ErrorSource[] = [
  { label: "Slow drift in hip position", level: "4 mm wobble", extraMm: 7.4 },
  { label: "More shake in hip points", level: "8 mm instead of 4", extraMm: 2.8 },
  { label: "Recording at 30 fps", level: "instead of 60", extraMm: 1.2 },
  { label: "Hip point rides up when bent", level: "10% of descent", extraMm: 0.2 },
  { label: "Phones only 20° apart", level: "instead of 45°", extraMm: 0.2 },
  { label: "Missed hip detections", level: "1 in 50 frames", extraMm: 0.1 },
  { label: "Phones 1 frame out of step", level: "", extraMm: 0.0 },
  { label: "Board tilted 2°", level: "", extraMm: 0.0 },
];

export const ERROR_BUDGET_BASELINE_MM = 3.0;
export const ERROR_BUDGET_MAX_MM = 8;

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
  {
    situation: "Rest of 0.3 s at the bottom",
    outcome: [
      "Reads about ",
      { text: "1.3 mm", style: "num" },
      " too deep. Small enough to accept.",
    ],
  },
  {
    situation: "Rest of 1 s at the bottom",
    outcome: [
      "Reads about ",
      { text: "0.9 mm", style: "num" },
      " too deep. Switches to a flat-bottom reading for 4–8% of squats.",
    ],
  },
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
  "No real phone has been tested. The simulation assumes a hip detector shakes by about 2–4 mm per frame; real phones may be worse.",
  "The first real check: stools raised by measured amounts (2, 4, 6, 8 cm). If the software sorts those squats correctly, the method works.",
  "Things the simulation leaves out: lens distortion, left and right hips being swapped, and loose clothing.",
];
