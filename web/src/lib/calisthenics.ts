// Calisthenics skills catalog — sourced from Overcoming Gravity 2nd Ed. (Low, 2016)
// Difficulty 1–5 maps to OG levels: 1=L1–3 (beginner), 2=L4–6, 3=L7–9, 4=L10–12, 5=L13–15+ (elite)
// requiredEquipment: user needs at least ONE of these slugs. Empty = pure bodyweight.

export type SkillCategory = "push" | "pull" | "core" | "legs" | "skill";

export type Skill = {
  slug: string;
  label: string;
  category: SkillCategory;
  difficulty: 1 | 2 | 3 | 4 | 5;
  requiredEquipment: string[];
};

// ─── Equipment group shorthands ───────────────────────────────────────────────
const BAR   = ["pull_up_bar_doorframe", "pull_up_bar_mounted", "rings"];
const BARX  = [...BAR, "low_bar"];            // bar + low bar
const RNG   = ["rings"];
const DIP   = ["dip_bars", "high_parallettes", "rings"];
const SUP   = ["dip_bars", "low_parallettes", "high_parallettes", "rings"];
const PAR   = ["low_parallettes", "high_parallettes"];
const ABW   = ["ab_roller"];
const FLAG  = ["vertical_pole", "pull_up_bar_doorframe", "pull_up_bar_mounted"];
const LOAD  = ["weight_vest", "backpack_load", "dumbbell", "kettlebell", "barbell"];

export const SKILLS: Skill[] = [

  // ─── PUSH ──────────────────────────────────────────────────────────────────
  { slug: "incline_push_up",          label: "Incline push-up",               category: "push", difficulty: 1, requiredEquipment: [] },
  { slug: "push_up",                  label: "Push-up",                        category: "push", difficulty: 1, requiredEquipment: [] },
  { slug: "diamond_push_up",          label: "Diamond push-up",               category: "push", difficulty: 2, requiredEquipment: [] },
  { slug: "wall_pike_push_up",        label: "Wall pike push-up",             category: "push", difficulty: 2, requiredEquipment: [] },
  { slug: "box_pike_push_up",         label: "Box pike push-up",              category: "push", difficulty: 2, requiredEquipment: [] },
  { slug: "pseudo_planche_push_up",   label: "Pseudo planche push-up",        category: "push", difficulty: 3, requiredEquipment: [] },
  { slug: "planche_lean",             label: "Planche lean",                  category: "push", difficulty: 3, requiredEquipment: [] },
  { slug: "archer_push_up",           label: "Archer push-up",                category: "push", difficulty: 3, requiredEquipment: [] },
  { slug: "frog_stand",               label: "Frog stand",                    category: "push", difficulty: 3, requiredEquipment: [] },
  { slug: "one_arm_push_up",          label: "One-arm push-up",               category: "push", difficulty: 4, requiredEquipment: [] },
  { slug: "sa_frog_stand",            label: "Single-arm frog stand",         category: "push", difficulty: 4, requiredEquipment: [] },
  { slug: "tuck_planche",             label: "Tuck planche",                  category: "push", difficulty: 4, requiredEquipment: [] },
  { slug: "adv_tuck_planche",         label: "Advanced tuck planche",         category: "push", difficulty: 4, requiredEquipment: [] },
  { slug: "straddle_planche",         label: "Straddle planche",              category: "push", difficulty: 5, requiredEquipment: [] },
  { slug: "full_planche",             label: "Full planche",                  category: "push", difficulty: 5, requiredEquipment: [] },
  { slug: "tuck_planche_push_up",     label: "Tuck planche push-up",          category: "push", difficulty: 5, requiredEquipment: [] },
  { slug: "adv_tuck_planche_push_up", label: "Adv. tuck planche push-up",    category: "push", difficulty: 5, requiredEquipment: [] },
  { slug: "full_planche_push_up",     label: "Full planche push-up",          category: "push", difficulty: 5, requiredEquipment: [] },
  // rings
  { slug: "ring_wide_push_up",        label: "Ring wide push-up",             category: "push", difficulty: 2, requiredEquipment: RNG },
  { slug: "ring_push_up",             label: "Ring push-up",                  category: "push", difficulty: 2, requiredEquipment: RNG },
  { slug: "ring_support_hold",        label: "Ring support hold",             category: "push", difficulty: 2, requiredEquipment: RNG },
  { slug: "ring_dips_eccentric",      label: "Ring dips (eccentric)",         category: "push", difficulty: 2, requiredEquipment: RNG },
  { slug: "rto_push_up",              label: "RTO push-up",                   category: "push", difficulty: 3, requiredEquipment: RNG },
  { slug: "rto_support",              label: "RTO support hold",              category: "push", difficulty: 3, requiredEquipment: RNG },
  { slug: "ring_dips",                label: "Ring dips",                     category: "push", difficulty: 3, requiredEquipment: RNG },
  // dip bars / parallettes
  { slug: "support_hold",             label: "Support hold (dip bars)",       category: "push", difficulty: 1, requiredEquipment: SUP },
  { slug: "pb_dips",                  label: "Parallel bar dips",             category: "push", difficulty: 2, requiredEquipment: DIP },
  { slug: "weighted_dips",            label: "Weighted dips",                 category: "push", difficulty: 3, requiredEquipment: [...DIP, ...LOAD] },
  { slug: "l_sit_dips",               label: "L-sit dips",                    category: "push", difficulty: 4, requiredEquipment: DIP },

  // ─── PULL ──────────────────────────────────────────────────────────────────
  // bar
  { slug: "negative_pull_up",         label: "Negative pull-up",              category: "pull", difficulty: 1, requiredEquipment: BAR },
  { slug: "jump_pull_up",             label: "Jump pull-up",                  category: "pull", difficulty: 1, requiredEquipment: BARX },
  { slug: "german_hang",              label: "German hang",                   category: "pull", difficulty: 2, requiredEquipment: BAR },
  { slug: "pull_up",                  label: "Pull-up",                       category: "pull", difficulty: 2, requiredEquipment: BAR },
  { slug: "chin_up",                  label: "Chin-up",                       category: "pull", difficulty: 2, requiredEquipment: BAR },
  { slug: "skin_the_cat",             label: "Skin the cat",                  category: "pull", difficulty: 3, requiredEquipment: BAR },
  { slug: "wide_pull_up",             label: "Wide-grip pull-up",             category: "pull", difficulty: 3, requiredEquipment: BAR },
  { slug: "weighted_pull_up",         label: "Weighted pull-up",              category: "pull", difficulty: 3, requiredEquipment: BAR },
  { slug: "pullover",                 label: "Pullover",                      category: "pull", difficulty: 3, requiredEquipment: BAR },
  { slug: "tuck_back_lever",          label: "Tuck back lever",               category: "pull", difficulty: 3, requiredEquipment: BAR },
  { slug: "tuck_front_lever",         label: "Tuck front lever",              category: "pull", difficulty: 3, requiredEquipment: BAR },
  { slug: "archer_pull_up",           label: "Archer pull-up",                category: "pull", difficulty: 4, requiredEquipment: BAR },
  { slug: "l_sit_pull_up",            label: "L-sit pull-up",                 category: "pull", difficulty: 4, requiredEquipment: BAR },
  { slug: "explosive_pull_up",        label: "Explosive pull-up",             category: "pull", difficulty: 4, requiredEquipment: BAR },
  { slug: "clapping_pull_up",         label: "Clapping pull-up",              category: "pull", difficulty: 4, requiredEquipment: BAR },
  { slug: "adv_tuck_back_lever",      label: "Adv. tuck back lever",          category: "pull", difficulty: 4, requiredEquipment: BAR },
  { slug: "straddle_back_lever",      label: "Straddle back lever",           category: "pull", difficulty: 4, requiredEquipment: BAR },
  { slug: "adv_tuck_front_lever",     label: "Adv. tuck front lever",         category: "pull", difficulty: 4, requiredEquipment: BAR },
  { slug: "straddle_front_lever",     label: "Straddle front lever",          category: "pull", difficulty: 4, requiredEquipment: BAR },
  { slug: "kipping_muscle_up",        label: "Kipping muscle-up",             category: "pull", difficulty: 4, requiredEquipment: BAR },
  { slug: "full_back_lever",          label: "Full back lever",               category: "pull", difficulty: 5, requiredEquipment: BAR },
  { slug: "full_front_lever",         label: "Full front lever",              category: "pull", difficulty: 5, requiredEquipment: BAR },
  { slug: "strict_bar_muscle_up",     label: "Strict bar muscle-up",          category: "pull", difficulty: 5, requiredEquipment: ["pull_up_bar_doorframe", "pull_up_bar_mounted"] },
  { slug: "one_arm_chin_up",          label: "One-arm chin-up",               category: "pull", difficulty: 5, requiredEquipment: BAR },
  // rings
  { slug: "ring_rows",                label: "Ring rows",                     category: "pull", difficulty: 1, requiredEquipment: [...RNG, "low_bar"] },
  { slug: "ring_muscle_up",           label: "Ring muscle-up",                category: "pull", difficulty: 5, requiredEquipment: RNG },
  { slug: "iron_cross",               label: "Iron cross",                    category: "pull", difficulty: 5, requiredEquipment: RNG },

  // ─── CORE ──────────────────────────────────────────────────────────────────
  // bodyweight
  { slug: "plank",                    label: "Plank",                         category: "core", difficulty: 1, requiredEquipment: [] },
  { slug: "floor_tuck_raises",        label: "Floor tuck raises",             category: "core", difficulty: 1, requiredEquipment: [] },
  { slug: "hollow_hold",              label: "Hollow hold",                   category: "core", difficulty: 1, requiredEquipment: [] },
  { slug: "one_arm_one_leg_plank",    label: "1-arm 1-leg plank",             category: "core", difficulty: 2, requiredEquipment: [] },
  { slug: "tuck_l_sit",               label: "Tuck L-sit",                    category: "core", difficulty: 2, requiredEquipment: [] },
  { slug: "l_sit",                    label: "L-sit",                         category: "core", difficulty: 3, requiredEquipment: [] },
  { slug: "v_sit_45",                 label: "V-sit (45°)",                   category: "core", difficulty: 3, requiredEquipment: [] },
  { slug: "straddle_l_sit",           label: "Straddle L-sit",                category: "core", difficulty: 4, requiredEquipment: [] },
  { slug: "v_sit_75",                 label: "V-sit (75°)",                   category: "core", difficulty: 4, requiredEquipment: [] },
  { slug: "dragon_flag",              label: "Dragon flag",                   category: "core", difficulty: 4, requiredEquipment: [...BAR, "dip_bars"] },
  // ab roller
  { slug: "kneeling_ab_wheel",        label: "Kneeling ab wheel",             category: "core", difficulty: 2, requiredEquipment: ABW },
  { slug: "ab_wheel_rollout",         label: "Ab wheel rollout",              category: "core", difficulty: 3, requiredEquipment: ABW },
  { slug: "full_ab_wheel_rollout",    label: "Full ab wheel rollout",         category: "core", difficulty: 4, requiredEquipment: ABW },
  { slug: "one_arm_ab_wheel",         label: "One-arm ab wheel",              category: "core", difficulty: 5, requiredEquipment: ABW },
  // bar
  { slug: "hanging_knee_raises",      label: "Hanging knee raises",           category: "core", difficulty: 2, requiredEquipment: BARX },
  { slug: "hanging_bent_leg_toes_to_bar", label: "Hanging bent-leg toes to bar", category: "core", difficulty: 2, requiredEquipment: BAR },
  { slug: "hanging_leg_raises",       label: "Hanging leg raises",            category: "core", difficulty: 3, requiredEquipment: BAR },
  { slug: "toes_to_bar",              label: "Toes to bar",                   category: "core", difficulty: 3, requiredEquipment: BAR },
  // rings
  { slug: "rto_l_sit",                label: "RTO L-sit",                     category: "core", difficulty: 4, requiredEquipment: RNG },
  { slug: "manna",                    label: "Manna",                         category: "core", difficulty: 5, requiredEquipment: [...PAR, "dip_bars"] },

  // ─── LEGS ──────────────────────────────────────────────────────────────────
  { slug: "glute_bridge",             label: "Glute bridge",                  category: "legs", difficulty: 1, requiredEquipment: [] },
  { slug: "single_leg_bridge",        label: "Single-leg bridge",             category: "legs", difficulty: 1, requiredEquipment: [] },
  { slug: "parallel_squat",           label: "Parallel squat",                category: "legs", difficulty: 1, requiredEquipment: [] },
  { slug: "full_squat",               label: "Full squat",                    category: "legs", difficulty: 1, requiredEquipment: [] },
  { slug: "reverse_hyperextension",   label: "Reverse hyperextension",        category: "legs", difficulty: 2, requiredEquipment: [] },
  { slug: "split_squat",              label: "Split squat",                   category: "legs", difficulty: 2, requiredEquipment: [] },
  { slug: "side_to_side_squat",       label: "Side-to-side squat",            category: "legs", difficulty: 2, requiredEquipment: [] },
  { slug: "beginner_shrimp_squat",    label: "Shrimp squat (beginner)",       category: "legs", difficulty: 2, requiredEquipment: [] },
  { slug: "natural_ham_curl",         label: "Natural hamstring curl",        category: "legs", difficulty: 2, requiredEquipment: [] },
  { slug: "intermediate_shrimp_squat",label: "Shrimp squat (intermediate)",   category: "legs", difficulty: 3, requiredEquipment: [] },
  { slug: "full_natural_ham_curl",    label: "Full natural hamstring curl",   category: "legs", difficulty: 3, requiredEquipment: [] },
  { slug: "nordic_curl",              label: "Nordic hamstring curl",         category: "legs", difficulty: 3, requiredEquipment: [] },
  { slug: "advanced_shrimp_squat",    label: "Shrimp squat (advanced)",       category: "legs", difficulty: 4, requiredEquipment: [] },
  { slug: "pistol_squat",             label: "Pistol squat",                  category: "legs", difficulty: 4, requiredEquipment: [] },
  { slug: "elevated_shrimp_squat",    label: "Shrimp squat (elevated)",       category: "legs", difficulty: 4, requiredEquipment: [] },
  { slug: "weighted_pistol_squat",    label: "Weighted pistol squat",         category: "legs", difficulty: 5, requiredEquipment: LOAD },

  // ─── SKILL ─────────────────────────────────────────────────────────────────
  { slug: "wall_handstand",           label: "Wall handstand",                category: "skill", difficulty: 2, requiredEquipment: [] },
  { slug: "pike_push_up",             label: "Pike push-up",                  category: "skill", difficulty: 2, requiredEquipment: [] },
  { slug: "two_arm_elbow_lever",      label: "Two-arm elbow lever",           category: "skill", difficulty: 3, requiredEquipment: [] },
  { slug: "box_handstand_push_up",    label: "Box handstand push-up",         category: "skill", difficulty: 3, requiredEquipment: [] },
  { slug: "free_handstand",           label: "Freestanding handstand",        category: "skill", difficulty: 4, requiredEquipment: [] },
  { slug: "wall_handstand_push_up",   label: "Wall handstand push-up",        category: "skill", difficulty: 4, requiredEquipment: [] },
  { slug: "free_handstand_push_up",   label: "Freestanding HSPU",             category: "skill", difficulty: 5, requiredEquipment: [] },
  { slug: "press_handstand",          label: "Press to handstand",            category: "skill", difficulty: 5, requiredEquipment: [] },
  { slug: "one_arm_elbow_lever",      label: "One-arm elbow lever",           category: "skill", difficulty: 5, requiredEquipment: [] },
  { slug: "one_arm_handstand",        label: "One-arm handstand",             category: "skill", difficulty: 5, requiredEquipment: [] },
  // flag — needs pole or high bar
  { slug: "tuck_flag",                label: "Tuck human flag",               category: "skill", difficulty: 4, requiredEquipment: FLAG },
  { slug: "straddle_flag",            label: "Straddle human flag",           category: "skill", difficulty: 4, requiredEquipment: FLAG },
  { slug: "full_flag",                label: "Full human flag",               category: "skill", difficulty: 5, requiredEquipment: FLAG },
];

export const CATEGORIES: { value: SkillCategory; label: string }[] = [
  { value: "push", label: "Push" },
  { value: "pull", label: "Pull" },
  { value: "core", label: "Core" },
  { value: "legs", label: "Legs" },
  { value: "skill", label: "Skill" },
];

export const EQUIPMENT_OPTIONS = [
  { slug: "pull_up_bar_doorframe",    label: "Pull-up bar (doorframe)" },
  { slug: "pull_up_bar_mounted",      label: "Pull-up bar (wall / ceiling mounted)" },
  { slug: "low_bar",                  label: "Low horizontal bar (waist height)" },
  { slug: "dip_bars",                 label: "Dip bars / parallel bars" },
  { slug: "low_parallettes",          label: "Low parallettes" },
  { slug: "high_parallettes",         label: "High parallettes (box height)" },
  { slug: "rings",                    label: "Gymnastic rings" },
  { slug: "ab_roller",                label: "Ab roller" },
  { slug: "resistance_bands_light",   label: "Resistance bands (light — < 25 lb)" },
  { slug: "resistance_bands_heavy",   label: "Resistance bands (heavy — > 50 lb)" },
  { slug: "weight_vest",              label: "Weight vest" },
  { slug: "backpack_load",            label: "Backpack (improvised load)" },
  { slug: "dumbbell",                 label: "Dumbbell" },
  { slug: "kettlebell",               label: "Kettlebell" },
  { slug: "barbell",                  label: "Barbell + plates" },
  { slug: "gymnastics_mat",           label: "Gymnastics / crash mat" },
  { slug: "vertical_pole",            label: "Vertical pole (for flag training)" },
  { slug: "none",                     label: "Nothing — bodyweight only" },
] as const;

// ─── Helpers ───────────────────────────────────────────────────────────────

export function skillsByCategory(category: SkillCategory): Skill[] {
  return SKILLS.filter((s) => s.category === category);
}

export function getSkill(slug: string): Skill | undefined {
  return SKILLS.find((s) => s.slug === slug);
}

/**
 * Filter skills for display in the onboarding form.
 * @param category      - skill category to pull from
 * @param selectedEquipment - equipment the athlete has selected
 * @param excludeSlugs  - slugs to hide (e.g. already selected as current skills)
 */
export function getAvailableSkills(
  category: SkillCategory,
  selectedEquipment: string[],
  excludeSlugs: string[] = [],
): Skill[] {
  const pool = skillsByCategory(category).filter(
    (s) => !excludeSlugs.includes(s.slug),
  );

  // No equipment selected yet → show everything
  if (selectedEquipment.length === 0) return pool;

  // Bodyweight-only selection → show only equipment-free skills
  const effectiveEquipment = selectedEquipment.filter((e) => e !== "none");
  if (effectiveEquipment.length === 0) {
    return pool.filter((s) => s.requiredEquipment.length === 0);
  }

  // Otherwise: show bodyweight + skills matching any selected equipment
  return pool.filter(
    (s) =>
      s.requiredEquipment.length === 0 ||
      s.requiredEquipment.some((e) => effectiveEquipment.includes(e)),
  );
}
