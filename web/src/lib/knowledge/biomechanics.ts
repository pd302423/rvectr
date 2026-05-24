/**
 * Vector Biomechanics Knowledge Base
 *
 * Compiled from:
 *   - NSCA Essentials of Strength Training and Conditioning (4th ed.)
 *   - Journal of Strength and Conditioning Research (JSCR)
 *   - Journal of Sports Science & Medicine
 *   - Haff & Triplett, "Periodisation" chapter in NSCA CSCS
 *   - FIG Code of Points (gymnastics)
 *   - Gymnastics Strength Training community research (Sommer, Bachmann)
 *   - PubMed: upper-limb loading in gymnastics rings exercises
 *
 * Format: structured data — not prose — so it can be injected into LLM context
 * as precise, citable reference material.
 */

// ─────────────────────────────────────────────
// JOINT ANGLE STANDARDS
// ─────────────────────────────────────────────

export type AngleStatus = "nominal" | "caution" | "error";

export type JointStandard = {
  exercise: string;
  joint: string;
  position: string;
  /** degrees */
  optimal_min: number;
  optimal_max: number;
  caution_threshold: number;
  error_threshold: number;
  clinical_note: string;
  source: string;
};

export const JOINT_STANDARDS: JointStandard[] = [
  // ── PULL-UP / CHIN-UP ──────────────────────────────────────────────
  {
    exercise: "pull_up",
    joint: "elbow",
    position: "bottom (dead hang initiation)",
    optimal_min: 155,
    optimal_max: 165,
    caution_threshold: 168,
    error_threshold: 173,
    clinical_note:
      "Full elbow extension (>170°) at dead hang places excessive valgus stress on the medial collateral ligament (MCL). " +
      "Maintain 155–165° flexion at hang initiation to pre-activate triceps as a stabiliser.",
    source: "Provencher et al., AJSM 2004; NSCA CSCS 4th ed. Ch.14",
  },
  {
    exercise: "pull_up",
    joint: "scapula",
    position: "initiation phase",
    optimal_min: 0, // coded as 0 = adequate depression present
    optimal_max: 100,
    caution_threshold: -1, // insufficient = flagged
    error_threshold: -2,
    clinical_note:
      "Scapular depression must precede glenohumeral flexion. Failure to depress elevates the humeral head, " +
      "impinging the supraspinatus tendon (subacromial space < 7mm below clinical threshold). " +
      "Cue: 'pack the shoulders before pulling.'",
    source: "Ludewig & Cook, JOSPT 2000; Kibler et al., JBJS 2003",
  },
  {
    exercise: "pull_up",
    joint: "shoulder",
    position: "top position (chin over bar)",
    optimal_min: 170,
    optimal_max: 180,
    caution_threshold: 165,
    error_threshold: 155,
    clinical_note:
      "Shoulder flexion at the top should reach 170–180°. Values below 165° indicate incomplete ROM or " +
      "premature termination — reduces lat length-tension advantage and limits strength gains at end range.",
    source: "Youdas et al., JOSPT 2010",
  },

  // ── PUSH-UP ────────────────────────────────────────────────────────
  {
    exercise: "push_up",
    joint: "elbow",
    position: "bottom (chest contact)",
    optimal_min: 85,
    optimal_max: 95,
    caution_threshold: 80,
    error_threshold: 70,
    clinical_note:
      "Elbow angle at chest contact should be ~90°. Excessive elbow flare (>45° from torso) at this position " +
      "dramatically increases anterior shoulder stress. Keep elbows at 20–40° of abduction from the torso.",
    source: "Cogley et al., JSCR 2005",
  },
  {
    exercise: "push_up",
    joint: "wrist",
    position: "throughout movement",
    optimal_min: 65,
    optimal_max: 80,
    caution_threshold: 85,
    error_threshold: 90,
    clinical_note:
      "Wrist extension beyond 80° significantly increases carpal tunnel pressure. " +
      "Parallettes or closed fists reduce wrist extension by ~20° and are recommended for high-volume work.",
    source: "Werner et al., JBJS 2002",
  },

  // ── SQUAT ──────────────────────────────────────────────────────────
  {
    exercise: "bodyweight_squat",
    joint: "knee",
    position: "bottom",
    optimal_min: 85,
    optimal_max: 100,
    caution_threshold: 80,
    error_threshold: 70,
    clinical_note:
      "Hip crease must drop to or below knee crease for full-depth squat. " +
      "Values above 100° indicate insufficient depth for maximal glute activation. " +
      "Depth limitation is most commonly caused by ankle dorsiflexion deficit (<35° DF required).",
    source: "Cotter et al., JSCR 2013; Escamilla, Med Sci Sports Exerc 2001",
  },
  {
    exercise: "bodyweight_squat",
    joint: "knee_valgus",
    position: "bottom and ascent",
    optimal_min: -5,
    optimal_max: 5,
    caution_threshold: -7,
    error_threshold: -10,
    clinical_note:
      "Knee valgus (inward collapse) beyond −5° increases ACL shear force and patellofemoral compression. " +
      "Primary causes: hip abductor weakness (GMed), femoral anteversion, or ankle pronation. " +
      "Correct at the hip, not by cueing the knee.",
    source: "Hewett et al., AJSM 2005; McLean et al., Med Sci Sports Exerc 2004",
  },
  {
    exercise: "pistol_squat",
    joint: "torso",
    position: "bottom",
    optimal_min: 40,
    optimal_max: 65,
    caution_threshold: 70,
    error_threshold: 80,
    clinical_note:
      "Pistol squat requires greater forward lean (~50°) than bilateral squat due to single-leg balance demands. " +
      "Values >65° indicate insufficient ankle dorsiflexion. " +
      "Hip flexor flexibility and ankle DF (target >45°) are primary limiters.",
    source: "Sheehan & Gormley, JSCR 2012",
  },

  // ── MUSCLE-UP ──────────────────────────────────────────────────────
  {
    exercise: "muscle_up",
    joint: "wrist",
    position: "transition phase",
    optimal_min: 70,
    optimal_max: 90,
    caution_threshold: 95,
    error_threshold: 100,
    clinical_note:
      "The false grip (wrist above bar) reduces transition leverage requirement by ~35% " +
      "by eliminating the wrist extension component during pull-to-dip transition. " +
      "Beginners should practise false grip dead hangs before attempting full reps.",
    source: "Garhammer, NSCA Journal 1993; GST community research Bachmann 2018",
  },

  // ── PLANCHE ────────────────────────────────────────────────────────
  {
    exercise: "planche_lean",
    joint: "shoulder",
    position: "lean position",
    optimal_min: 20,
    optimal_max: 35,
    caution_threshold: 40,
    error_threshold: 45,
    clinical_note:
      "Planche lean angle (degrees forward of vertical) of 20–35° provides sufficient anterior deltoid and " +
      "serratus anterior challenge without exceeding recommended loading for beginner/intermediate athletes. " +
      "Progress lean angle by ~5° per 4-week mesocycle once 3×30s can be held at current angle.",
    source: "Sommer, Building the Gymnastic Body 2008; Bachmann Planche Progressions 2017",
  },
];

// ─────────────────────────────────────────────
// SKILL PROGRESSION MECHANICS
// ─────────────────────────────────────────────

export type SkillProgressionStep = {
  slug: string;
  name: string;
  prerequisite_slugs: string[];
  primary_muscles: string[];
  limiting_factors: string[];
  key_angle_refs: string[];
  progression_note: string;
  typical_weeks_to_achieve: string;
};

export const SKILL_PROGRESSIONS: SkillProgressionStep[] = [
  // ── PUSH LINE ────────────────────────────────────────────────────
  {
    slug: "push_up",
    name: "Push-up",
    prerequisite_slugs: ["incline_push_up"],
    primary_muscles: ["pectoralis major", "anterior deltoid", "triceps brachii"],
    limiting_factors: ["scapular stability", "wrist mobility", "core anti-extension"],
    key_angle_refs: ["elbow 85–95° at bottom", "elbows 20–40° from torso"],
    progression_note:
      "Achieve 3×15 with full ROM before advancing. Eccentric-only reps (3–5s descent) accelerate tendon adaptation.",
    typical_weeks_to_achieve: "2–6 (from incline)",
  },
  {
    slug: "archer_push_up",
    name: "Archer push-up",
    prerequisite_slugs: ["push_up", "diamond_push_up"],
    primary_muscles: ["pectoralis major (unilateral)", "serratus anterior", "anterior deltoid"],
    limiting_factors: ["unilateral pec strength", "scapular protraction capacity", "wrist mobility"],
    key_angle_refs: ["working arm elbow 85–95° at bottom", "non-working arm ~165° extension"],
    progression_note:
      "Bridge between standard push-up and one-arm push-up. Develop at 3×8 each side. " +
      "Parallettes reduce wrist stress and allow greater ROM.",
    typical_weeks_to_achieve: "4–10 (from standard push-up)",
  },
  {
    slug: "pseudo_planche_push_up",
    name: "Pseudo planche push-up",
    prerequisite_slugs: ["push_up", "planche_lean"],
    primary_muscles: ["anterior deltoid", "serratus anterior", "pectoralis minor", "wrist flexors"],
    limiting_factors: ["wrist extensor flexibility", "anterior deltoid strength at 90° abduction", "core position"],
    key_angle_refs: ["wrist angle ≤ 70° with hands turned out", "body lean 15–25° forward"],
    progression_note:
      "The pseudo planche push-up is the single most effective exercise for planche preparation. " +
      "Hand position: fingers pointing laterally or backward. Lean increases anterior deltoid loading exponentially.",
    typical_weeks_to_achieve: "6–14 (from standard push-up)",
  },

  // ── PULL LINE ────────────────────────────────────────────────────
  {
    slug: "pull_up",
    name: "Pull-up",
    prerequisite_slugs: ["negative_pull_up"],
    primary_muscles: ["latissimus dorsi", "biceps brachii", "lower trapezius", "rhomboids"],
    limiting_factors: ["scapular depression strength", "elbow flexor endurance", "grip strength"],
    key_angle_refs: ["elbow 155–165° at initiation", "shoulder flexion 170–180° at top"],
    progression_note:
      "Depress scapulae before initiating pull. Full dead hang between reps maximises lat ROM. " +
      "Achieve 3×8 strict before adding weight or advancing.",
    typical_weeks_to_achieve: "4–12 (from negatives)",
  },
  {
    slug: "kipping_muscle_up",
    name: "Muscle-up",
    prerequisite_slugs: ["pull_up", "pb_dips"],
    primary_muscles: ["latissimus dorsi", "biceps brachii", "pectoralis major", "triceps brachii"],
    limiting_factors: [
      "explosive pulling power (rate of force development)",
      "false grip strength",
      "transition timing",
      "straight-arm strength at bottom of dip",
    ],
    key_angle_refs: ["false grip: wrist above bar", "transition elbow 90°", "finish: arms locked at top of dip"],
    progression_note:
      "False grip is non-negotiable for strict muscle-up. " +
      "Transition drill: hang on rings at bar height, practise pulling elbows past bar without kipping. " +
      "Weighted pull-ups to 120% BW recommended before first muscle-up attempt.",
    typical_weeks_to_achieve: "12–30 (from solid pull-up)",
  },
  {
    slug: "tuck_front_lever",
    name: "Tuck front lever",
    prerequisite_slugs: ["pull_up"],
    primary_muscles: ["latissimus dorsi", "teres major", "posterior deltoid", "core anti-extension"],
    limiting_factors: ["shoulder depression strength (RFD)", "core rigidity", "lat length-tension"],
    key_angle_refs: ["body horizontal ± 5°", "arms straight, shoulder depression"],
    progression_note:
      "Begin with 3×5s holds. Add 1–2s per week. Progress: advanced tuck → one leg extended → straddle → full. " +
      "Eccentric lower from inverted hang develops this efficiently.",
    typical_weeks_to_achieve: "8–20 (from solid pull-up)",
  },

  // ── SKILL LINE ────────────────────────────────────────────────────
  {
    slug: "wall_handstand",
    name: "Wall handstand",
    prerequisite_slugs: [],
    primary_muscles: ["anterior deltoid", "serratus anterior", "wrist flexors", "core anti-extension"],
    limiting_factors: ["wrist mobility (≥70° extension)", "shoulder flexibility (overhead mobility)", "fear/vestibular adaptation"],
    key_angle_refs: ["body vertical ± 3°", "shoulders directly over wrists", "wrist extension ≤80°"],
    progression_note:
      "Begin face-to-wall for proprioception. Shoulders must be 'pushed through the ears' — " +
      "scapular elevation at top is correct in handstand (differs from pulling movements). " +
      "Target 3×60s holds before progressing to freestanding.",
    typical_weeks_to_achieve: "3–8 (no prerequisite)",
  },
  {
    slug: "tuck_planche",
    name: "Tuck planche",
    prerequisite_slugs: ["planche_lean", "pseudo_planche_push_up"],
    primary_muscles: ["anterior deltoid", "serratus anterior", "pectoralis minor", "wrist flexors"],
    limiting_factors: [
      "anterior deltoid max isometric force at ~100° abduction",
      "serratus anterior protraction capacity",
      "wrist extensor length",
      "core compression",
    ],
    key_angle_refs: ["body horizontal ± 5°", "arms straight at elbow (0° flexion)", "hips tucked, knees to chest"],
    progression_note:
      "The tuck planche requires body weight to be supported anterior to the hands. " +
      "Anterior deltoid must produce ~1.5× bodyweight isometric force. " +
      "Programme: planche lean 3×30s + PPPUs 3×8 as primary prep. Expected timeline 6–18 months from beginner.",
    typical_weeks_to_achieve: "26–78 (from beginner calisthenics)",
  },
];

// ─────────────────────────────────────────────
// PERIODISATION STANDARDS
// ─────────────────────────────────────────────

export const PERIODISATION = {
  weekly_volume_landmarks: {
    beginner: {
      push: { min_sets: 6, max_sets: 14, note: "MEV–MAV range for beginners. Higher volumes produce faster adaptation." },
      pull: { min_sets: 6, max_sets: 14, note: "Match push volume to maintain force couple balance at shoulder." },
      core: { min_sets: 4, max_sets: 10, note: "Anti-extension volume (plank, hollow hold) precedes flexion work." },
      legs: { min_sets: 6, max_sets: 16, note: "High frequency tolerated (large muscle group)." },
    },
    intermediate: {
      push: { min_sets: 12, max_sets: 22 },
      pull: { min_sets: 12, max_sets: 22 },
      core: { min_sets: 8, max_sets: 16 },
      legs: { min_sets: 12, max_sets: 24 },
    },
    advanced: {
      push: { min_sets: 18, max_sets: 30 },
      pull: { min_sets: 18, max_sets: 30 },
      core: { min_sets: 12, max_sets: 22 },
      legs: { min_sets: 16, max_sets: 28 },
    },
  },
  deload_indicators: [
    "Performance regression on primary movements for 2+ consecutive sessions",
    "Resting HR elevated >7 BPM above personal baseline",
    "Sleep quality score (HRV apps) <70 for 3+ consecutive nights",
    "Joint tenderness persisting >24h post-session",
    "Mood/motivation markedly reduced (subjective wellness score <5/10)",
  ],
  block_structure: {
    accumulation: { weeks: "3–4", intensity: "60–75% MVC", volume: "high", note: "Build work capacity. High rep, controlled tempo." },
    intensification: { weeks: "2–3", intensity: "75–90% MVC", volume: "moderate", note: "Higher intensity, lower volume. Strength focus." },
    realisation: { weeks: "1", intensity: "90–100% MVC", volume: "low", note: "Peak performance. Test maxes, attempt skills." },
    deload: { weeks: "1", intensity: "50–60% MVC", volume: "very low", note: "Recovery. Technique focus, no PRs." },
  },
  source: "Haff & Triplett, NSCA Periodization; Issurin, Block Periodization 2008",
};

// ─────────────────────────────────────────────
// MUSCLE ACTIVATION REFERENCE
// ─────────────────────────────────────────────

export const MUSCLE_ACTIVATION: Record<string, { primary: string[]; secondary: string[]; antagonists: string[] }> = {
  pull_up: {
    primary: ["latissimus dorsi", "biceps brachii long head", "lower trapezius"],
    secondary: ["teres major", "posterior deltoid", "rhomboids", "core anti-extension"],
    antagonists: ["anterior deltoid", "pectoralis major", "serratus anterior"],
  },
  push_up: {
    primary: ["pectoralis major", "anterior deltoid", "triceps brachii"],
    secondary: ["serratus anterior", "coracobrachialis", "core anti-extension"],
    antagonists: ["posterior deltoid", "rhomboids", "lower trapezius"],
  },
  planche_lean: {
    primary: ["anterior deltoid", "serratus anterior", "pectoralis minor"],
    secondary: ["wrist flexors", "core anti-extension", "triceps brachii"],
    antagonists: ["posterior deltoid", "latissimus dorsi"],
  },
  front_lever_tuck: {
    primary: ["latissimus dorsi", "teres major", "posterior deltoid"],
    secondary: ["core anti-extension", "biceps brachii", "infraspinatus"],
    antagonists: ["anterior deltoid", "serratus anterior", "pectoralis minor"],
  },
  bodyweight_squat: {
    primary: ["quadriceps", "gluteus maximus"],
    secondary: ["hamstrings", "soleus", "gluteus medius"],
    antagonists: ["hip flexors", "tibialis anterior"],
  },
  pistol_squat: {
    primary: ["quadriceps (unilateral)", "gluteus maximus"],
    secondary: ["gluteus medius", "soleus", "tibialis posterior", "peroneals"],
    antagonists: ["hip flexors", "biceps femoris"],
  },
};

// ─────────────────────────────────────────────
// HELPER — get standard for an exercise + joint
// ─────────────────────────────────────────────

export function getJointStandard(exercise: string, joint: string): JointStandard | undefined {
  return JOINT_STANDARDS.find(
    (s) => s.exercise === exercise && s.joint.toLowerCase() === joint.toLowerCase()
  );
}

export function getAngleStatus(standard: JointStandard, measuredAngle: number): AngleStatus {
  if (
    measuredAngle >= standard.optimal_min &&
    measuredAngle <= standard.optimal_max
  ) return "nominal";
  if (
    measuredAngle >= standard.caution_threshold ||
    measuredAngle <= standard.caution_threshold
  ) return "caution";
  return "error";
}

export function getProgressionPath(targetSlug: string): SkillProgressionStep[] {
  const path: SkillProgressionStep[] = [];
  const visited = new Set<string>();

  function traverse(slug: string) {
    if (visited.has(slug)) return;
    visited.add(slug);
    const step = SKILL_PROGRESSIONS.find((s) => s.slug === slug);
    if (!step) return;
    step.prerequisite_slugs.forEach(traverse);
    path.push(step);
  }

  traverse(targetSlug);
  return path;
}
