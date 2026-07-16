/**
 * Overcoming Gravity 2nd Edition — Steven Low (2016)
 * Encoded programming framework used by rvector's AI coach.
 *
 * Difficulty scale: 1–15 (Low's original)
 * rvector maps this to 5 display dots in onboarding (1–3→1, 4–6→2, 7–9→3, 10–12→4, 13–15→5)
 */

// ─── DIFFICULTY RATINGS (Low 1–15 scale) ──────────────────────────────────

export const OG_DIFFICULTY: Record<string, number> = {
  // Push line
  incline_push_up: 1,
  push_up: 2,
  diamond_push_up: 3,
  ring_push_up: 4,
  pseudo_planche_push_up: 5,
  archer_push_up: 6,
  wall_pike_push_up: 4,
  box_pike_push_up: 5,
  wall_handstand_push_up: 7,
  pb_dips: 4,
  ring_dips: 6,
  weighted_dips: 7,
  one_arm_push_up: 8,
  tuck_planche: 9,
  adv_tuck_planche: 10,
  straddle_planche: 12,
  full_planche: 14,
  tuck_planche_push_up: 10,
  adv_tuck_planche_push_up: 11,
  full_planche_push_up: 15,
  // Pull line
  ring_rows: 1,
  negative_pull_up: 2,
  jump_pull_up: 2,
  pull_up: 4,
  chin_up: 3,
  wide_pull_up: 5,
  weighted_pull_up: 6,
  archer_pull_up: 7,
  l_sit_pull_up: 7,
  explosive_pull_up: 8,
  clapping_pull_up: 9,
  tuck_back_lever: 7,
  adv_tuck_back_lever: 8,
  straddle_back_lever: 10,
  full_back_lever: 12,
  tuck_front_lever: 8,
  adv_tuck_front_lever: 9,
  straddle_front_lever: 11,
  full_front_lever: 13,
  kipping_muscle_up: 8,
  strict_bar_muscle_up: 9,
  ring_muscle_up: 10,
  one_arm_chin_up: 13,
  iron_cross: 15,
  // Core
  plank: 1,
  hollow_hold: 2,
  hanging_knee_raises: 3,
  tuck_l_sit: 4,
  l_sit: 6,
  kneeling_ab_wheel: 4,
  ab_wheel_rollout: 6,
  hanging_leg_raises: 6,
  toes_to_bar: 7,
  dragon_flag: 9,
  full_ab_wheel_rollout: 9,
  straddle_l_sit: 9,
  v_sit_45: 10,
  rto_l_sit: 10,
  v_sit_75: 12,
  one_arm_ab_wheel: 13,
  manna: 15,
  // Legs
  parallel_squat: 1,
  full_squat: 2,
  glute_bridge: 1,
  split_squat: 3,
  side_to_side_squat: 4,
  beginner_shrimp_squat: 5,
  natural_ham_curl: 5,
  intermediate_shrimp_squat: 7,
  nordic_curl: 7,
  pistol_squat: 8,
  advanced_shrimp_squat: 9,
  elevated_shrimp_squat: 10,
  weighted_pistol_squat: 11,
  // Skill
  wall_handstand: 4,
  pike_push_up: 4,
  two_arm_elbow_lever: 6,
  box_handstand_push_up: 7,
  free_handstand: 9,
  free_handstand_push_up: 11,
  tuck_flag: 10,
  straddle_flag: 12,
  full_flag: 14,
  press_handstand: 13,
  one_arm_elbow_lever: 12,
  one_arm_handstand: 15,
};

// ─── PUSH / PULL / CORE SPLIT STRUCTURE ────────────────────────────────────

/**
 * Low recommends training push and pull movements on the SAME day,
 * paired to balance anterior/posterior shoulder loading.
 * Core is trained every session (low volume, high frequency).
 *
 * 3-day structure (most common):
 *   Day A: Push + Pull (strength focus) + Core
 *   Day B: Push + Pull (skill focus) + Core
 *   Day C: Legs + Core
 *
 * 2-day structure:
 *   Day A: Push + Pull + Core + Legs
 *   Day B: Repeat with different intensity
 *
 * 4-day structure:
 *   Day A/C: Push + Pull (heavy)
 *   Day B/D: Push + Pull (skill/volume)
 */
export type SessionFocus = "strength" | "skill" | "volume" | "legs" | "assessment";

export const SESSION_STRUCTURE: Record<number, SessionFocus[]> = {
  2: ["strength", "volume"],
  3: ["strength", "skill", "legs"],
  4: ["strength", "volume", "skill", "legs"],
  5: ["strength", "skill", "volume", "strength", "legs"],
  6: ["strength", "skill", "volume", "strength", "skill", "legs"],
};

// ─── VOLUME LANDMARKS ───────────────────────────────────────────────────────

/**
 * Weekly set ranges per movement category by experience.
 * Source: Low (2016), Ch. 8 — Volume and Frequency Guidelines.
 */
export const VOLUME_LANDMARKS = {
  beginner: {
    push_sets_per_week: [6, 10],
    pull_sets_per_week: [6, 10],
    core_sets_per_week: [4, 8],
    legs_sets_per_week: [4, 8],
    max_reps_before_adding_difficulty: 15,
    min_reps_for_progression: 3,
  },
  intermediate: {
    push_sets_per_week: [10, 18],
    pull_sets_per_week: [10, 18],
    core_sets_per_week: [6, 12],
    legs_sets_per_week: [6, 12],
    max_reps_before_adding_difficulty: 12,
    min_reps_for_progression: 4,
  },
  advanced: {
    push_sets_per_week: [16, 24],
    pull_sets_per_week: [16, 24],
    core_sets_per_week: [10, 16],
    legs_sets_per_week: [10, 16],
    max_reps_before_adding_difficulty: 8,
    min_reps_for_progression: 3,
  },
} as const;

// ─── INTENSITY OSCILLATION (intra-week) ────────────────────────────────────

/**
 * Low's hard/easy oscillation: alternate heavy and light sessions
 * to manage CNS fatigue and allow supercompensation.
 */
export const INTENSITY_BY_FOCUS: Record<SessionFocus, {
  sets: number;
  rep_range: [number, number];
  rpe_target: number;
  rest_seconds: [number, number];
}> = {
  strength: {
    sets: 3,
    rep_range: [3, 6],
    rpe_target: 8,
    rest_seconds: [180, 300],
  },
  skill: {
    sets: 4,
    rep_range: [1, 3],
    rpe_target: 7,
    rest_seconds: [120, 180],
  },
  volume: {
    sets: 3,
    rep_range: [8, 15],
    rpe_target: 7,
    rest_seconds: [90, 120],
  },
  legs: {
    sets: 3,
    rep_range: [6, 12],
    rpe_target: 7,
    rest_seconds: [120, 180],
  },
  // Assessment: max-effort single test set with full recovery between tests
  assessment: {
    sets: 1,
    rep_range: [1, 20],
    rpe_target: 10,
    rest_seconds: [300, 300],
  },
};

// ─── CONNECTIVE TISSUE ADAPTATION WINDOWS ──────────────────────────────────

/**
 * Low repeatedly emphasises that connective tissue (tendons, ligaments)
 * adapts 3–10× SLOWER than muscle. Rushing progressions causes injury.
 * These are MINIMUM weeks before attempting to advance a skill level.
 *
 * Source: Low (2016), Ch. 6 — Injury Prevention and Tissue Adaptation.
 */
export const CONNECTIVE_TISSUE_WINDOWS = {
  beginner_to_intermediate: 8,   // weeks minimum
  intermediate_to_advanced: 12,
  advanced_to_elite: 16,
  isometric_hold_progression: 4, // minimum weeks per hold duration increment
};

/**
 * Tendon load tolerance by joint — informs injury risk flags.
 */
export const TENDON_RISK_MOVEMENTS = [
  {
    movement_family: "planche",
    at_risk: ["wrist extensors", "biceps tendon (long head)", "anterior deltoid"],
    minimum_prep_weeks: 12,
    note: "Wrist circles, reverse wrist curls, and loaded stretching mandatory before loading planche progressions.",
  },
  {
    movement_family: "front_lever",
    at_risk: ["biceps tendon (long head)", "shoulder posterior capsule"],
    minimum_prep_weeks: 10,
    note: "Scapular depression strength must be established before isometric lever holds.",
  },
  {
    movement_family: "back_lever",
    at_risk: ["shoulder anterior capsule", "biceps tendon"],
    minimum_prep_weeks: 8,
    note: "German hang flexibility required. Progress shoulder dislocates first.",
  },
  {
    movement_family: "iron_cross",
    at_risk: ["biceps tendon", "pectoralis minor", "shoulder joint capsule"],
    minimum_prep_weeks: 24,
    note: "Elite movement. Requires multiple years of ring training base.",
  },
  {
    movement_family: "one_arm_movements",
    at_risk: ["elbow medial collateral ligament", "wrist"],
    minimum_prep_weeks: 20,
    note: "Archer pull-ups and assisted OAC should precede any one-arm work by 6+ months.",
  },
] as const;

// ─── PREREQUISITE GATING ────────────────────────────────────────────────────

/**
 * Hard prerequisites — rvector will NOT program a skill until prerequisites
 * are confirmed. Prevents common injury patterns described by Low.
 */
export const HARD_PREREQUISITES: Record<string, string[]> = {
  // Push
  tuck_planche:            ["pseudo_planche_push_up", "planche_lean"],
  adv_tuck_planche:        ["tuck_planche"],
  straddle_planche:        ["adv_tuck_planche"],
  full_planche:            ["straddle_planche"],
  full_planche_push_up:    ["full_planche"],
  one_arm_push_up:         ["archer_push_up"],
  ring_dips:               ["pb_dips", "ring_support_hold"],
  // Pull
  pull_up:                 ["negative_pull_up"],
  weighted_pull_up:        ["pull_up"],
  archer_pull_up:          ["pull_up", "wide_pull_up"],
  kipping_muscle_up:       ["pull_up", "pb_dips"],
  strict_bar_muscle_up:    ["weighted_pull_up", "pb_dips"],
  ring_muscle_up:          ["strict_bar_muscle_up", "ring_dips"],
  tuck_front_lever:        ["pull_up"],
  adv_tuck_front_lever:    ["tuck_front_lever"],
  straddle_front_lever:    ["adv_tuck_front_lever"],
  full_front_lever:        ["straddle_front_lever"],
  tuck_back_lever:         ["skin_the_cat"],
  adv_tuck_back_lever:     ["tuck_back_lever"],
  straddle_back_lever:     ["adv_tuck_back_lever"],
  full_back_lever:         ["straddle_back_lever"],
  one_arm_chin_up:         ["archer_pull_up", "l_sit_pull_up"],
  iron_cross:              ["ring_muscle_up", "full_front_lever"],
  // Core
  tuck_l_sit:              ["hollow_hold"],
  l_sit:                   ["tuck_l_sit"],
  straddle_l_sit:          ["l_sit"],
  v_sit_45:                ["straddle_l_sit"],
  dragon_flag:             ["hollow_hold", "hanging_leg_raises"],
  // Skill
  free_handstand:          ["wall_handstand"],
  wall_handstand_push_up:  ["wall_handstand", "pike_push_up"],
  free_handstand_push_up:  ["free_handstand", "wall_handstand_push_up"],
  press_handstand:         ["free_handstand", "straddle_l_sit"],
  tuck_flag:               ["two_arm_elbow_lever"],
  straddle_flag:           ["tuck_flag"],
  full_flag:               ["straddle_flag"],
};

// ─── PERIODISATION BLOCKS ───────────────────────────────────────────────────

/**
 * Low uses a 4-phase block system within each 8–12 week mesocycle.
 * rvector adapts this for individual skill progression tracking.
 */
export const PERIODISATION_BLOCKS = [
  {
    block: "accumulation",
    weeks: [1, 3],
    focus: "Build volume. High reps, moderate load. Establish movement pattern.",
    rep_scheme: "3×8–12",
    intensity: "RPE 6–7",
  },
  {
    block: "intensification",
    weeks: [4, 6],
    focus: "Increase load/difficulty. Lower reps, higher intensity.",
    rep_scheme: "4×4–6",
    intensity: "RPE 7–8",
  },
  {
    block: "realisation",
    weeks: [7, 8],
    focus: "Peak performance. Test strength standards. Attempt next progression.",
    rep_scheme: "5×1–3",
    intensity: "RPE 8–9",
  },
  {
    block: "deload",
    weeks: [9, 9],
    focus: "Active recovery. 40–60% volume reduction. Maintain movement quality.",
    rep_scheme: "2×5–8",
    intensity: "RPE 5–6",
  },
] as const;

// ─── PROGRESSION STANDARDS (when to advance) ────────────────────────────────

/**
 * Strength standards before advancing to the next progression level.
 * These are conservative — better to over-prepare than under-prepare.
 */
export const PROGRESSION_STANDARDS: Record<string, {
  sets: number;
  reps: number;
  form_requirement: string;
}> = {
  // Push
  push_up:              { sets: 3, reps: 15, form_requirement: "Full ROM, 3s descent, chest to floor" },
  diamond_push_up:      { sets: 3, reps: 12, form_requirement: "Elbows tracking back, not flaring" },
  pb_dips:              { sets: 3, reps: 10, form_requirement: "Full depth (upper arm parallel), no forward lean" },
  ring_dips:            { sets: 3, reps: 8,  form_requirement: "RTO at top, controlled descent" },
  pseudo_planche_push_up: { sets: 3, reps: 8, form_requirement: "15–25° forward lean maintained throughout" },
  tuck_planche:         { sets: 3, reps: 10, form_requirement: "10s hold, hips level with shoulders" },
  adv_tuck_planche:     { sets: 3, reps: 8,  form_requirement: "10s hold, knees only slightly tucked" },
  // Pull
  negative_pull_up:     { sets: 3, reps: 6,  form_requirement: "5s eccentric, full dead hang" },
  pull_up:              { sets: 3, reps: 8,  form_requirement: "Dead hang start, chin clearly over bar" },
  weighted_pull_up:     { sets: 3, reps: 5,  form_requirement: "Bodyweight +20%, strict form" },
  archer_pull_up:       { sets: 3, reps: 6,  form_requirement: "Full extension of non-working arm" },
  tuck_front_lever:     { sets: 3, reps: 10, form_requirement: "10s hold, body horizontal" },
  tuck_back_lever:      { sets: 3, reps: 10, form_requirement: "10s hold, shoulders below hips" },
  // Skill
  wall_handstand:       { sets: 3, reps: 1,  form_requirement: "60s hold, straight body, active shoulders" },
  free_handstand:       { sets: 3, reps: 1,  form_requirement: "10s hold, minimal corrections" },
  // Core
  hollow_hold:          { sets: 3, reps: 1,  form_requirement: "30s hold, lower back flat" },
  tuck_l_sit:           { sets: 3, reps: 1,  form_requirement: "15s hold, hips elevated" },
  l_sit:                { sets: 3, reps: 1,  form_requirement: "10s hold, legs parallel to floor" },
};

// ─── EXERCISE INTENT LABELS ─────────────────────────────────────────────────

export type ExerciseIntent =
  | "strength"
  | "hypertrophy"
  | "skill_acquisition"
  | "tendon_prep"
  | "active_recovery";

export const INTENT_DESCRIPTIONS: Record<ExerciseIntent, string> = {
  strength:         "Low reps, high load — developing maximal force output",
  hypertrophy:      "Moderate reps, controlled tempo — building contractile tissue",
  skill_acquisition:"Sub-maximal effort — ingraining movement pattern via repetition",
  tendon_prep:      "Isometric or light loaded — conditioning passive connective tissue",
  active_recovery:  "Sub-threshold movement — promoting circulation without adding fatigue",
};
