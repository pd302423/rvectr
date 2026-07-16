/**
 * Vector — AI session generation
 * Supports two modes:
 *   "assessment" — generates a strength test battery based on the athlete's profile
 *   workout modes — generates training sessions (future, post CV-grading)
 *
 * AI priority:
 *   1. Amazon Bedrock (Llama 3.3 70B) — primary; uses AWS credits
 *   2. Anthropic Claude — fallback if ANTHROPIC_API_KEY present
 *   3. Mock — local dev fallback when no API keys are configured
 */

import { HARD_PREREQUISITES, OG_DIFFICULTY, INTENSITY_BY_FOCUS } from "./knowledge/overcoming_gravity";
import { getSkill } from "./calisthenics";
import type { SessionFocus } from "./knowledge/overcoming_gravity";
import type { ExerciseIntent } from "./knowledge/overcoming_gravity";

// ─── Types ────────────────────────────────────────────────────────────────────

export type GeneratedExercise = {
  exercise_slug: string;
  order_index: number;
  intent: ExerciseIntent;
  target_sets: number;
  target_reps_min: number;   // for assessment: minimum pass standard
  target_reps_max: number;   // for assessment: test cap
  rest_seconds_min: number;
  rest_seconds_max: number;
  tempo: string;             // for assessment: "max_effort" | "timed_hold" | "graded"
  biomechanical_note: string; // for assessment: form requirements for a valid rep/hold
  progression_context: string; // for assessment: what score means for goal readiness
};

export type GeneratedWorkout = {
  session_focus: SessionFocus;
  week_number: number;
  block: string;
  ai_rationale: string;
  exercises: GeneratedExercise[];
};

export type AthleteProfile = {
  display_name: string;
  days_per_week: number;
  session_minutes: number;
  experience_level?: string;
  training_style?: string;
  equipment: string[];
  current_skills: string[];
  goal_skills: string[];
  injuries: string | null;
  total_workouts_completed?: number;
};

// ─── Main entry point ─────────────────────────────────────────────────────────

export async function generateWorkout(
  profile: AthleteProfile,
  focus: SessionFocus,
): Promise<GeneratedWorkout> {
  const hasBedrockCreds = !!(
    process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY
  );
  const hasAnthropicKey = !!process.env.ANTHROPIC_API_KEY;

  if (hasBedrockCreds) return generateWithBedrock(profile, focus);
  if (hasAnthropicKey) return generateWithClaude(profile, focus);

  // Dev fallback — no API key needed
  if (focus === "assessment") return generateMockAssessment(profile);
  return generateMock(profile, focus);
}

// ─── Amazon Bedrock generation (primary AI path) ──────────────────────────────

/**
 * Default model: Llama 3.3 70B Instruct (cross-region inference profile).
 * Override with BEDROCK_MODEL_ID env var.
 *
 * Alternative cheap options:
 *   amazon.nova-lite-v1:0        — cheapest, ~4× less quality
 *   amazon.nova-pro-v1:0         — Amazon flagship, middle ground
 *   us.meta.llama3-1-70b-instruct-v1:0 — older Llama 3.1 if 3.3 unavailable
 */
const DEFAULT_BEDROCK_MODEL = "us.meta.llama3-3-70b-instruct-v1:0";

async function generateWithBedrock(
  profile: AthleteProfile,
  focus: SessionFocus,
): Promise<GeneratedWorkout> {
  const { BedrockRuntimeClient, ConverseCommand } = await import(
    "@aws-sdk/client-bedrock-runtime"
  );

  const client = new BedrockRuntimeClient({
    region: process.env.AWS_REGION ?? "us-east-1",
    credentials: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
      ...(process.env.AWS_SESSION_TOKEN
        ? { sessionToken: process.env.AWS_SESSION_TOKEN }
        : {}),
    },
  });

  const modelId = process.env.BEDROCK_MODEL_ID ?? DEFAULT_BEDROCK_MODEL;

  const systemPrompt =
    focus === "assessment"
      ? buildAssessmentSystemPrompt()
      : buildWorkoutSystemPrompt();

  const userPrompt =
    focus === "assessment"
      ? buildAssessmentUserPrompt(profile)
      : buildWorkoutUserPrompt(profile, focus);

  const response = await client.send(
    new ConverseCommand({
      modelId,
      system: [{ text: systemPrompt }],
      messages: [{ role: "user", content: [{ text: userPrompt }] }],
      inferenceConfig: {
        maxTokens: 4096,
        temperature: 0.3, // low temp = reliable JSON schema adherence
      },
    }),
  );

  const text = (response.output?.message?.content ?? [])
    .map((b) => ("text" in b ? b.text : ""))
    .join("");

  const jsonMatch =
    text.match(/```json\n([\s\S]*?)\n```/) ||
    text.match(/```\n([\s\S]*?)\n```/) ||
    text.match(/(\{[\s\S]*\})/);

  if (!jsonMatch) throw new Error("Bedrock returned no JSON block");

  const raw = JSON.parse(jsonMatch[1] ?? jsonMatch[0]);
  return raw as GeneratedWorkout;
}

// ─── Claude generation (fallback) ────────────────────────────────────────────

async function generateWithClaude(
  profile: AthleteProfile,
  focus: SessionFocus,
): Promise<GeneratedWorkout> {
  const Anthropic = (await import("@anthropic-ai/sdk")).default;
  const client = new Anthropic();

  const systemPrompt = focus === "assessment"
    ? buildAssessmentSystemPrompt()
    : buildWorkoutSystemPrompt();

  const userPrompt = focus === "assessment"
    ? buildAssessmentUserPrompt(profile)
    : buildWorkoutUserPrompt(profile, focus);

  const message = await client.messages.create({
    model: "claude-sonnet-4-5",
    max_tokens: 4096,
    system: systemPrompt,
    messages: [{ role: "user", content: userPrompt }],
  });

  const text = message.content
    .filter((b) => b.type === "text")
    .map((b) => (b as { type: "text"; text: string }).text)
    .join("");

  const jsonMatch = text.match(/```json\n([\s\S]*?)\n```/) ||
                    text.match(/\{[\s\S]*\}/);
  if (!jsonMatch) throw new Error("Claude returned no JSON block");

  const raw = JSON.parse(jsonMatch[1] ?? jsonMatch[0]);
  return raw as GeneratedWorkout;
}

// ─── Assessment prompts ───────────────────────────────────────────────────────

function buildAssessmentSystemPrompt(): string {
  return `You are rvector's assessment engine — a biomechanical strength testing system grounded in Low (2016) "Overcoming Gravity" 2nd ed. and NSCA CSCS 4th ed. principles.

Your role is to generate a comprehensive, personalised strength test battery (5–8 tests) that determines the athlete's ACTUAL capability independent of self-report. All tests will be recorded on video and graded by a computer vision classifier — your form criteria must be precise enough for a camera to evaluate.

═══ TEST SELECTION RULES ═══
- Select 5–8 exercises covering the full movement profile: push, pull, core compression, core anti-extension, and goal-specific prerequisites
- Each test must directly reveal something about readiness for the athlete's stated goals
- Verify self-reported skills — if they claim archer push-ups, include an archer push-up test
- Always include: (1) one max push test, (2) one max pull test if bar available, (3) one core isometric test, (4) one or more goal-prerequisite tests
- Order tests: push → pull → core → goal-specific → structural integrity/tendon
- rest_seconds_min = rest_seconds_max = 300 always (non-negotiable — 5 min full recovery)
- target_sets = 1 always

═══ PROTOCOL DEFINITIONS ═══
tempo field must be exactly one of:
  "max_effort"  — reps to volitional failure. Stop when form breaks, not just when tired.
  "timed_hold"  — hold position until the specific failure criterion stated in biomechanical_note is met.
  "graded"      — fixed rep count; form quality is scored, not quantity. Execute deliberately.

target_reps_min = minimum score to pass / qualify for next progression
target_reps_max = cap at which the test is complete (no need to continue beyond this)

═══ BIOMECHANICAL NOTE REQUIREMENTS ═══
Each biomechanical_note must include ALL of:
1. Joint angles at the start position (e.g., "elbows at 165–180° in dead hang")
2. Joint angles at the peak/end position (e.g., "chin clearly above bar — not just level with bar")
3. Primary movers and key stabilisers (e.g., "lats, lower trap, biceps brachii; infraspinatus for GH stability")
4. Body position requirements (pelvic tilt, body line, shoulder packing, foot position)
5. EXACTLY what constitutes an invalid rep (the CV classifier uses this to reject reps)
6. Common compensation patterns to watch for (kipping, hip pike, elbow flare, neck jut, etc.)

═══ PROGRESSION CONTEXT REQUIREMENTS ═══
Each progression_context must include ALL of:
1. Exact quantitative thresholds with OG level references:
   "X+ reps / Xs hold → [next skill] (OG Level Y)"
   "X–Y reps → maintain current level"
   "< X reps → regress to [easier variation]"
2. What the score tells rvector about readiness for each of the athlete's specific goal skills
3. Why this threshold matters physiologically (e.g., "tendon-to-muscle force ratio", "neuromuscular recruitment pattern")

═══ AI RATIONALE ═══
Write 2–3 paragraphs covering:
  Paragraph 1: Which movement patterns are being tested and why they reveal the athlete's true capacity
  Paragraph 2: How each specific test maps to the athlete's named goal skills
  Paragraph 3: What rvector will do with the results — how it drives programming

Return ONLY valid JSON — no prose outside the JSON block:
\`\`\`json
{
  "session_focus": "assessment",
  "week_number": 1,
  "block": "accumulation",
  "ai_rationale": "...",
  "exercises": [
    {
      "exercise_slug": "pull_up",
      "order_index": 1,
      "intent": "strength",
      "target_sets": 1,
      "target_reps_min": 8,
      "target_reps_max": 20,
      "rest_seconds_min": 300,
      "rest_seconds_max": 300,
      "tempo": "max_effort",
      "biomechanical_note": "Start: dead hang, elbows at 165–180° extension, shoulders actively depressed (not shrugged). Initiate by depressing scapulae further BEFORE any elbow flexion — this is the scapular motor pattern the CV model checks first. Pull until chin clearly clears the bar (not neck, not forehead — chin). Primary movers: latissimus dorsi, lower trapezius, biceps brachii. Stabilisers: infraspinatus and teres minor (glenohumeral), serratus anterior (scapular). INVALID REP: chin does not clear bar, elbows do not reach 90° flexion, kipping or leg swing detected, incomplete return to dead hang between reps. Common compensations: shrugging at initiation (upper trap dominant pattern), stopping at eye level, using momentum from hips.",
      "progression_context": "OG Level 5 movement. Thresholds: 10+ strict dead-hang reps → cleared for weighted pull-up progression and bar muscle-up skill work (OG L8). 6–9 reps → consolidate pull-up volume (3 × max sets). 3–5 reps → add negative pull-ups (5s eccentric, 5 × 3) for connective tissue loading. < 3 reps → regress to Australian pull-ups and ring rows to establish scapular motor pattern. For one-arm chin-up goal (OG L12): 15+ dead-hang reps required as base before archer pull-up phase begins (Low 2016, Ch. 11). For front lever goal (OG L10–12): pull-up strength contributes 40% of lever capacity — 12+ reps is the minimum base."
    }
  ]
}
\`\`\``;
}

function buildAssessmentUserPrompt(profile: AthleteProfile): string {
  const prerequisites = profile.goal_skills.flatMap((slug) =>
    (HARD_PREREQUISITES[slug] ?? [])
  );
  const uniquePrereqs = [...new Set(prerequisites)];

  return `Generate a comprehensive strength assessment battery for this athlete. Follow the system prompt requirements exactly — 5–8 tests, full biomechanical notes with joint angles and failure criteria, and exact OG-referenced progression thresholds.

ATHLETE PROFILE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name: ${profile.display_name}
Experience level: ${profile.experience_level ?? "Not sure"}
Primary focus: ${profile.training_style ?? "Not sure"}
Available equipment: ${profile.equipment.join(", ") || "bodyweight only — no bar"}
Self-reported current skills: ${profile.current_skills.join(", ") || "none listed"}
Goal skills: ${profile.goal_skills.join(", ") || "none listed"}
Injuries / contraindications: ${profile.injuries ?? "none reported"}
Training frequency: ${profile.days_per_week} days/week
Session duration: ${profile.session_minutes} minutes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

KNOWN PREREQUISITES FOR THEIR GOALS (from OG skill tree):
${uniquePrereqs.length > 0 ? uniquePrereqs.join(", ") : "No specific prerequisites mapped — use your knowledge of OG progressions"}

REQUIRED TESTS (select the most relevant):
1. Push test — select the hardest push they can plausibly do based on self-report. Verify it.
2. Pull test — only if equipment allows (bar, rings). Select level matching self-report.
3. Core isometric — test compression (L-sit) or anti-extension (hollow hold / plank) based on goals.
4. Goal prerequisite test(s) — one or more tests that directly gate their primary goal skill.
5. Structural integrity / tendon test — assess connective tissue readiness for their training load.
6. Optional: secondary push/pull or unilateral movement if goal-relevant.

IMPORTANT: Write biomechanical notes that a computer vision model can USE to grade reps. Include exact joint angles, body line requirements, and specific failure criteria. Be clinical and precise.`;
}

// ─── Workout prompts (future use, post-CV) ────────────────────────────────────

function buildWorkoutSystemPrompt(): string {
  return `You are rvector's AI coach — a biomechanical precision coaching system for calisthenics athletes.

Your programming is grounded in Steven Low's "Overcoming Gravity" (2nd ed., 2016) and NSCA CSCS principles.

Rules:
- Select exercises appropriate for the athlete's current skills and goal skills
- Respect equipment constraints — only prescribe exercises the athlete can perform
- Never include an exercise whose hard prerequisites the athlete hasn't met
- Include a push AND pull movement in every non-leg session
- Core work in every session
- Write biomechanical notes in clinical language (cite joint angles, muscle actions)
- Progression context should reference Low's difficulty scale and the athlete's goal skill
- Return ONLY valid JSON matching the GeneratedWorkout schema — no prose outside the JSON block

Schema:
\`\`\`json
{
  "session_focus": "strength|skill|volume|legs",
  "week_number": 1,
  "block": "accumulation|intensification|realisation|deload",
  "ai_rationale": "One paragraph explaining the session logic",
  "exercises": [
    {
      "exercise_slug": "pull_up",
      "order_index": 1,
      "intent": "strength|hypertrophy|skill_acquisition|tendon_prep|active_recovery",
      "target_sets": 3,
      "target_reps_min": 4,
      "target_reps_max": 6,
      "rest_seconds_min": 180,
      "rest_seconds_max": 300,
      "tempo": "30X0",
      "biomechanical_note": "Clinical note about the exercise",
      "progression_context": "Where this sits in the skill journey"
    }
  ]
}
\`\`\``;
}

function buildWorkoutUserPrompt(profile: AthleteProfile, focus: SessionFocus): string {
  const prerequisites = profile.goal_skills.flatMap((slug) =>
    HARD_PREREQUISITES[slug] ?? []
  );

  return `Generate a ${focus} session for this athlete:

Name: ${profile.display_name}
Experience level: ${profile.experience_level ?? "Not sure"}
Primary focus: ${profile.training_style ?? "Not sure"}
Training days/week: ${profile.days_per_week}
Session length: ${profile.session_minutes} minutes
Equipment: ${profile.equipment.join(", ")}
Current skills: ${profile.current_skills.join(", ")}
Goal skills: ${profile.goal_skills.join(", ") || "none listed"}
Injuries/contraindications: ${profile.injuries ?? "none"}
Total sessions completed: ${profile.total_workouts_completed ?? 0}

Known prerequisites for their goals: ${prerequisites}

Session focus: ${focus}
${INTENSITY_BY_FOCUS[focus] ? `Target: ${INTENSITY_BY_FOCUS[focus].sets} sets × ${INTENSITY_BY_FOCUS[focus].rep_range[0]}–${INTENSITY_BY_FOCUS[focus].rep_range[1]} reps, RPE ${INTENSITY_BY_FOCUS[focus].rpe_target}` : ""}

Select 4–6 exercises. Prioritise movements that bridge current skills to goal skills.`;
}

// ─── Mock assessment ──────────────────────────────────────────────────────────

function generateMockAssessment(profile: AthleteProfile): GeneratedWorkout {
  const equipment = profile.equipment.filter((e) => e !== "none");
  const hasBar = equipment.some((e) =>
    ["pull_up_bar_doorframe", "pull_up_bar_mounted", "rings"].includes(e)
  );

  const exercises: GeneratedExercise[] = [];
  let idx = 1;

  function addTest(
    slug: string,
    intent: ExerciseIntent,
    tempo: string,
    repsMin: number,
    repsMax: number,
    note: string,
    ctx: string,
  ) {
    exercises.push({
      exercise_slug: slug,
      order_index: idx++,
      intent,
      target_sets: 1,
      target_reps_min: repsMin,
      target_reps_max: repsMax,
      rest_seconds_min: 300,
      rest_seconds_max: 300,
      tempo,
      biomechanical_note: note,
      progression_context: ctx,
    });
  }

  // ── 1. Push test ─────────────────────────────────────────────────────────
  const pushSlug = pickByDifficulty(profile.current_skills, [
    "pseudo_planche_push_up", "archer_push_up", "diamond_push_up", "push_up", "incline_push_up",
  ]);
  addTest(
    pushSlug,
    "strength",
    "max_effort",
    5, 30,
    getPushTestNote(pushSlug),
    getPushTestStandard(pushSlug, profile.goal_skills),
  );

  // ── 2. Pull test (bar required) ──────────────────────────────────────────
  if (hasBar) {
    const pullSlug = pickByDifficulty(profile.current_skills, [
      "pull_up", "negative_pull_up", "ring_rows",
    ]);
    addTest(
      pullSlug,
      "strength",
      pullSlug === "negative_pull_up" ? "timed_hold" : "max_effort",
      pullSlug === "ring_rows" ? 8 : 3,
      pullSlug === "ring_rows" ? 20 : 15,
      getPullTestNote(pullSlug),
      getPullTestStandard(pullSlug, profile.goal_skills),
    );
  }

  // ── 3. Core isometric test ────────────────────────────────────────────────
  const coreSlug = pickByDifficulty(profile.current_skills, [
    "l_sit", "tuck_l_sit", "hollow_hold", "plank",
  ]);
  const coreIsHold = ["l_sit", "tuck_l_sit", "hollow_hold", "plank"].includes(coreSlug);
  addTest(
    coreSlug,
    "skill_acquisition",
    coreIsHold ? "timed_hold" : "max_effort",
    coreSlug === "plank" ? 30 : coreSlug === "hollow_hold" ? 20 : coreSlug === "tuck_l_sit" ? 10 : 5,
    coreSlug === "plank" ? 120 : 60,
    getCoreTestNote(coreSlug),
    getCoreTestStandard(coreSlug, profile.goal_skills),
  );

  // ── 4. Goal prerequisite test (if applicable) ─────────────────────────────
  const primaryGoal = profile.goal_skills[0];
  if (primaryGoal) {
    const prereqs = HARD_PREREQUISITES[primaryGoal] ?? [];
    const prereqToTest = prereqs.find(
      (p) => !exercises.some((e) => e.exercise_slug === p)
    );
    if (prereqToTest) {
      addTest(
        prereqToTest,
        "strength",
        "graded",
        3, 8,
        `Maintain strict form throughout all reps. No momentum or compensation. This is a form-quality test, not a max-effort test.`,
        `${getSkill(prereqToTest)?.label ?? prereqToTest} is a direct prerequisite for ${getSkill(primaryGoal)?.label ?? primaryGoal} (OG L${OG_DIFFICULTY[primaryGoal] ?? "?"}). Quality of execution here determines readiness to progress.`,
      );
    }
  }

  // ── 4.5 Leg test ──────────────────────────────────────────────────────────
  const isLegGoal = primaryGoal && ["parallel_squat", "full_squat", "pistol_squat", "split_squat", "beginner_shrimp_squat"].includes(primaryGoal);
  if (isLegGoal || exercises.length < 4) {
    const legSlug = pickByDifficulty(profile.current_skills, [
      "pistol_squat", "intermediate_shrimp_squat", "split_squat", "full_squat",
    ]);
    addTest(
      legSlug,
      "strength",
      "max_effort",
      10, 30,
      "Hip crease must drop below the top of the knee at the bottom of the squat. Keep heel of the working leg firmly on the floor. Maintain a neutral spine (avoid excessive butt wink).",
      `${getSkill(legSlug)?.label ?? legSlug} assessment. 20+ reps -> advance to harder unilateral variations. <10 reps -> focus on volume and depth.`,
    );
  }

  // ── 5. Dead hang (structural integrity, bar only) ─────────────────────────
  if (hasBar && exercises.length < 6) {
    addTest(
      "negative_pull_up",
      "tendon_prep",
      "timed_hold",
      30, 120,
      "Jump to top position (chin above bar), then lower as slowly as possible (target 5–8s descent). Shoulders actively packed throughout descent. Full elbow extension at bottom before releasing.",
      "Eccentric capacity: <3s descent → connective tissue not yet conditioned for high-load pulling. 5–8s descent → adequate baseline. Use this to flag tendon risk before progressing.",
    );
  }

  const goalLabel = getSkill(primaryGoal ?? "")?.label ?? "your target skill";

  return {
    session_focus: "assessment",
    week_number: 1,
    block: "accumulation",
    ai_rationale:
      `This assessment battery is designed to verify ${profile.display_name}'s self-reported baseline and identify the biomechanical gaps between current capability and ${goalLabel}. ` +
      `Each test will be graded by computer vision for strict form — only clean repetitions count. ` +
      `Rest fully (5 minutes minimum) between tests. Fatigue between tests invalidates results. ` +
      `Results from this session will drive rvector's periodisation engine and determine your starting block.`,
    exercises,
  };
}

// ─── Assessment note helpers ──────────────────────────────────────────────────

function getPushTestNote(slug: string): string {
  const notes: Record<string, string> = {
    push_up:
      "Chest touches floor at bottom (0° between upper arm and torso floor plane). Arms fully locked at top. Body forms rigid plank — no sagging hips. Elbows 20–40° from torso.",
    diamond_push_up:
      "Hands directly under sternum, thumbs and forefingers touching. Elbows track straight back (posterior). Full lockout at top. Body rigid throughout.",
    pseudo_planche_push_up:
      "Hands turned 45° outward, fingers pointing lateral. 20–25° forward lean maintained throughout entire rep. Hips level — no piking. Elbows track back, not flaring.",
    archer_push_up:
      "Working arm: full depth (upper arm parallel to floor). Non-working arm: fully extended. Hips square to floor throughout. No rotation of the torso.",
    incline_push_up:
      "Chest touches surface at bottom. Arms fully locked at top. Body forms straight line from ankle to shoulder — no sagging.",
  };
  return notes[slug] ?? "Full ROM. Arms locked at top. Body rigid. No momentum.";
}

function getPushTestStandard(slug: string, goals: string[]): string {
  const isPlancheGoal = goals.some((g) =>
    ["tuck_planche", "adv_tuck_planche", "straddle_planche", "full_planche"].includes(g)
  );

  const standards: Record<string, string> = {
    push_up: isPlancheGoal
      ? "15+ strict reps → ready to progress to diamond / pseudo planche push-ups. 8–14 → build volume at this level. <8 → technique and volume needed."
      : "20+ strict reps → advance to diamond push-up. 10–19 → build volume. <10 → form and strength work required.",
    diamond_push_up:
      "12+ reps → advance to pseudo planche push-up. 6–11 → consolidate. <6 → return to push-up volume.",
    pseudo_planche_push_up:
      "8+ reps at 20° lean → qualified for tuck planche work. 4–7 → increase lean angle progressively. <4 → diamond push-up strength needs building.",
    archer_push_up:
      "5+ controlled reps each side → one-arm push-up prerequisites met. 2–4 → continue unilateral development.",
    incline_push_up:
      "15+ reps → advance to floor push-up. 8–14 → lower incline height. <8 → maintain current incline.",
  };

  return (
    standards[slug] ??
    `OG difficulty L${OG_DIFFICULTY[slug] ?? "?"}. Score compared to Overcoming Gravity progression standards.`
  );
}

function getPullTestNote(slug: string): string {
  const notes: Record<string, string> = {
    pull_up:
      "Dead hang start (elbows fully locked, ~165° extension). Chin clearly above bar at top — not just level. Shoulders depressed throughout. No kipping, no leg swing. Controlled descent back to dead hang.",
    negative_pull_up:
      "Jump or step to top position (chin above bar). Descend as slowly as possible. Target 5+ seconds per rep. Full extension at bottom (dead hang) before releasing. Tests eccentric strength and tendon tolerance.",
    ring_rows:
      "Body angle determines difficulty — more horizontal = harder. Scapulae retracted and depressed before pulling. Elbows finish at 90° at chest height. Body rigid throughout — no hip sagging.",
  };
  return notes[slug] ?? "Full ROM. Initiating with scapular depression. Controlled at all times.";
}

function getPullTestStandard(slug: string, goals: string[]): string {
  const hasPullGoal = goals.some((g) =>
    ["tuck_front_lever", "full_front_lever", "strict_bar_muscle_up", "ring_muscle_up", "one_arm_chin_up"].includes(g)
  );

  const standards: Record<string, string> = {
    pull_up: hasPullGoal
      ? "10+ strict reps → prerequisites for weighted pull-up met. 5–9 → continue pull-up volume. <5 → negative pull-ups and ring rows first."
      : "8+ strict reps → advance to weighted pull-up. 4–7 → build to 8. <4 → negative pull-ups.",
    negative_pull_up:
      "5s+ eccentric on 3 reps → tendon tolerance adequate for pull-up training. <3s → connective tissue conditioning needed before full pull-ups.",
    ring_rows:
      "15+ reps at 30° body angle → progress to incline pull-up or band-assisted pull-up. <15 → continue ring rows.",
  };

  return (
    standards[slug] ??
    `OG difficulty L${OG_DIFFICULTY[slug] ?? "?"}. Reference Low (2016) progression standards.`
  );
}

function getCoreTestNote(slug: string): string {
  const notes: Record<string, string> = {
    plank:
      "Elbows directly under shoulders. Posterior pelvic tilt — lower back flat (not arched). Glutes contracted. No hip pike or sag. Body forms straight line from ankle to crown.",
    hollow_hold:
      "Lower back pressed flat against floor — this is the diagnostic. Arms overhead (increases difficulty). Legs elevated. Hold until lower back lifts off floor — that is the failure point.",
    tuck_l_sit:
      "Supported on parallel bars, floor, or parallettes. Shoulders depressed and pushed down. Hips at or above wrist height. Knees tucked to chest. Hold until hips drop.",
    l_sit:
      "Legs parallel to floor. Feet together. Shoulders actively depressed. Hold until legs drop below parallel — that is failure.",
  };
  return notes[slug] ?? "Maintain position until form breaks. That is the true failure point.";
}

function getCoreTestStandard(slug: string, goals: string[]): string {
  const standards: Record<string, string> = {
    plank:
      "60s → adequate anti-extension for most skill work. 90s+ → strong core base. <30s → prioritise core conditioning before advanced skills.",
    hollow_hold:
      "30s → advance to hanging leg raises. 20–29s → build to 30s. <20s → technique and strengthening required.",
    tuck_l_sit:
      "15s → advance to L-sit training. 10–14s → build to 15s. <10s → hollow hold and shoulder depression work first.",
    l_sit:
      "10s → OG progression standard met; advance to straddle L-sit. 5–9s → build to 10s. <5s → return to tuck L-sit.",
  };
  return (
    standards[slug] ??
    `OG difficulty L${OG_DIFFICULTY[slug] ?? "?"}. Reference Low (2016) core progression standards.`
  );
}

// ─── Mock workout generation (non-assessment, for future use) ─────────────────

function generateMock(profile: AthleteProfile, focus: SessionFocus): GeneratedWorkout {
  const intensity = INTENSITY_BY_FOCUS[focus];
  const [rMin, rMax] = intensity.rep_range;
  const [restMin, restMax] = intensity.rest_seconds;

  const equipment = profile.equipment.filter((e) => e !== "none");
  const hasBar = equipment.some((e) =>
    ["pull_up_bar_doorframe", "pull_up_bar_mounted", "rings"].includes(e)
  );

  const pushSlug = pickByDifficulty(profile.current_skills, [
    "pseudo_planche_push_up", "diamond_push_up", "push_up", "incline_push_up",
  ]);
  const pullSlug = hasBar
    ? pickByDifficulty(profile.current_skills, [
        "archer_pull_up", "weighted_pull_up", "pull_up", "negative_pull_up", "ring_rows",
      ])
    : null;
  const coreSlug = pickByDifficulty(profile.current_skills, [
    "l_sit", "tuck_l_sit", "hollow_hold", "plank",
  ]);
  const goalBridge = profile.goal_skills[0] ?? null;
  const bridgeSlug = goalBridge ? (HARD_PREREQUISITES[goalBridge]?.[0] ?? pushSlug) : null;

  const exercises: GeneratedExercise[] = [];
  let idx = 1;

  const addExercise = (
    slug: string,
    intent: ExerciseIntent,
    note: string,
    ctx: string,
    setsOverride?: number,
  ) => {
    exercises.push({
      exercise_slug: slug,
      order_index: idx++,
      intent,
      target_sets: setsOverride ?? intensity.sets,
      target_reps_min: rMin,
      target_reps_max: rMax,
      rest_seconds_min: restMin,
      rest_seconds_max: restMax,
      tempo: focus === "strength" ? "31X0" : focus === "skill" ? "10X0" : "20X0",
      biomechanical_note: note,
      progression_context: ctx,
    });
  };

  addExercise(
    pushSlug,
    focus === "volume" ? "hypertrophy" : focus === "skill" ? "skill_acquisition" : "strength",
    getPushNote(pushSlug),
    getPushContext(pushSlug, profile.goal_skills),
  );

  if (bridgeSlug && bridgeSlug !== pushSlug && focus !== "legs") {
    addExercise(
      bridgeSlug,
      "skill_acquisition",
      `Bridge movement toward ${getSkill(goalBridge ?? "")?.label ?? "goal skill"}. Focus on motor pattern quality.`,
      `Prerequisite for ${getSkill(goalBridge ?? "")?.label ?? "target skill"} (OG L${OG_DIFFICULTY[goalBridge ?? ""] ?? "??"}).`,
      3,
    );
  }

  if (pullSlug && focus !== "legs") {
    addExercise(
      pullSlug,
      focus === "volume" ? "hypertrophy" : "strength",
      getPullNote(pullSlug),
      getPullContext(pullSlug, profile.goal_skills),
    );
  }

  addExercise(coreSlug, "strength", getCoreNote(coreSlug),
    "Core anti-extension and hip flexor compression support all upper-body skills.", 3);

  if (focus === "legs") {
    const legSlug = pickByDifficulty(profile.current_skills, [
      "pistol_squat", "intermediate_shrimp_squat", "beginner_shrimp_squat", "split_squat", "full_squat",
    ]);
    addExercise(legSlug, "strength",
      "Single-leg loading develops hip stability and neuromuscular coordination. Control the descent over 3–4 seconds.",
      "Unilateral leg strength transfers directly to explosive pulling power and landing mechanics.");
    addExercise("nordic_curl", "tendon_prep",
      "Nordic curl eccentrically loads the hamstring–biceps femoris complex at long muscle lengths.",
      "Hamstring-to-quad strength ratio ≥0.6 associated with reduced ACL injury risk (NSCA CSCS).", 3);
  }

  const block = getBlock(profile.total_workouts_completed ?? 0);

  return {
    session_focus: focus,
    week_number: Math.floor((profile.total_workouts_completed ?? 0) / (profile.days_per_week || 3)) + 1,
    block,
    ai_rationale: buildRationale(profile, focus, block),
    exercises,
  };
}

// ─── Shared helpers ───────────────────────────────────────────────────────────

function pickByDifficulty(currentSkills: string[], candidates: string[]): string {
  for (const slug of candidates) {
    if (currentSkills.includes(slug)) return slug;
  }
  return candidates[candidates.length - 1];
}

function getBlock(completedWorkouts: number): string {
  const weekInCycle = Math.floor(completedWorkouts / 3) % 9;
  if (weekInCycle <= 2) return "accumulation";
  if (weekInCycle <= 5) return "intensification";
  if (weekInCycle <= 7) return "realisation";
  return "deload";
}

function buildRationale(profile: AthleteProfile, focus: SessionFocus, block: string): string {
  const goal = profile.goal_skills[0];
  const goalLabel = getSkill(goal ?? "")?.label ?? "your target skill";
  return (
    `${block.charAt(0).toUpperCase() + block.slice(1)} phase — ${focus} session. ` +
    `Programming is structured toward ${goalLabel} by addressing prerequisite strength gaps. ` +
    `Push and pull movements are paired to balance anterior/posterior shoulder loading, ` +
    `consistent with Low (2016) Ch. 7. Core work included every session.`
  );
}

function getPushNote(slug: string): string {
  const notes: Record<string, string> = {
    push_up: "Elbows 20–40° from torso. Lower chest to floor (0° at bottom). Active scapular protraction. 3s eccentric minimum.",
    diamond_push_up: "Hands under sternum, elbows tracking posterior. Emphasises triceps long head. Wrist in neutral.",
    pseudo_planche_push_up: "15–25° forward lean. Hands turned out 45°. Anterior deltoid at near-90° abduction. Wrist extension ≤70°.",
    archer_push_up: "Working arm: elbow 85–95° at bottom. Non-working arm: 165–180° extension.",
    incline_push_up: "Elevate hands to reduce load. Full ROM critical — chest to surface.",
  };
  return notes[slug] ?? "Full ROM, controlled tempo. Scapular stability throughout.";
}

function getPullNote(slug: string): string {
  const notes: Record<string, string> = {
    pull_up: "Dead hang initiation — scapular depression before elbow flexion. Chin clearly over bar. 165° elbow at start.",
    negative_pull_up: "Jump to top. 5–8s controlled descent. Primary tendon adaptation stimulus.",
    weighted_pull_up: "Add load via belt. Maintain strict dead hang. Do not swing under load.",
    archer_pull_up: "Working arm pulls; non-working arm extended, hand open on bar for minimal assistance.",
    ring_rows: "Pronated grip. Body angle determines load. Retract scapulae before pulling.",
  };
  return notes[slug] ?? "Full ROM. Initiate with scapular depression.";
}

function getCoreNote(slug: string): string {
  const notes: Record<string, string> = {
    plank: "Posterior pelvic tilt — lumbar neutral. Glutes engaged. Target: 60s, zero pelvic rotation.",
    hollow_hold: "Lower back flat against floor. Arms overhead increases lever. 20–30s hold.",
    tuck_l_sit: "Shoulders depressed and protracted. Hips at or above wrist height.",
    l_sit: "Legs parallel to floor. Hip flexors at full shortening. 10s hold = progression standard.",
  };
  return notes[slug] ?? "Maintain braced neutral spine. Quality over duration.";
}

function getPushContext(slug: string, goalSkills: string[]): string {
  const goal = goalSkills.find((g) =>
    ["tuck_planche", "adv_tuck_planche", "straddle_planche", "full_planche"].includes(g)
  );
  if (goal) {
    return `Direct prerequisite for ${getSkill(goal)?.label ?? "planche goal"} (OG L${OG_DIFFICULTY[goal] ?? "??"}).`;
  }
  return `OG difficulty L${OG_DIFFICULTY[slug] ?? "??"} — progressive overload toward next push tier.`;
}

function getPullContext(slug: string, goalSkills: string[]): string {
  const goal = goalSkills.find((g) =>
    ["full_front_lever", "strict_bar_muscle_up", "ring_muscle_up", "one_arm_chin_up"].includes(g)
  );
  if (goal) {
    return `Builds pulling capacity toward ${getSkill(goal)?.label ?? "pull goal"} (OG L${OG_DIFFICULTY[goal] ?? "??"}).`;
  }
  return `OG difficulty L${OG_DIFFICULTY[slug] ?? "??"} — progressive overload toward next pull tier.`;
}
