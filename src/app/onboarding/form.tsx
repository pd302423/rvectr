"use client";

import { useState, useTransition } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";

import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

import {
  CATEGORIES,
  EQUIPMENT_OPTIONS,
  getAvailableSkills,
  type Skill,
  type SkillCategory,
} from "@/lib/calisthenics";
import { profileSchema, type ProfileInput } from "./schema";
import { saveProfile } from "./actions";

export function OnboardingForm({
  defaultDisplayName,
}: {
  defaultDisplayName: string;
}) {
  const [isPending, startTransition] = useTransition();
  const [serverError, setServerError] = useState<string | null>(null);

  const form = useForm<ProfileInput>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      display_name: defaultDisplayName,
      days_per_week: 3,
      session_minutes: 45,
      equipment: [],
      current_skills: [],
      goal_skills: [],
      not_sure_goals: false,
      experience_level: "beginner",
      training_style: "Strength",
      injuries: "",
    },
  });

  function onSubmit(values: ProfileInput) {
    setServerError(null);
    startTransition(async () => {
      const result = await saveProfile(values);
      if (result && !result.ok) {
        setServerError(result.error);
        toast.error(result.error);
      }
      // On success, the server action redirects — nothing to do here.
    });
  }

  const currentSkillsCount = form.watch("current_skills").length;
  const goalSkillsCount = form.watch("goal_skills").length;
  const equipmentCount = form.watch("equipment").length;
  const daysPerWeek = form.watch("days_per_week");
  const sessionMinutes = form.watch("session_minutes");

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">

        {/* ---------- Section 1: About you ---------- */}
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="text-foreground">Athlete identification</CardTitle>
            <CardDescription className="text-muted-foreground">
              Used for session reports and AI communication. rvector does not share this data.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <FormField
              control={form.control}
              name="display_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-foreground">Display name</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="e.g. Parth"
                      className="bg-background border-border text-foreground"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

          </CardContent>
        </Card>

        {/* ---------- Section 2: Schedule ---------- */}
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="text-foreground">Training frequency</CardTitle>
            <CardDescription className="text-muted-foreground">
              rvector uses this to calculate weekly volume load and recovery windows. Be accurate.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-8">
            <FormField
              control={form.control}
              name="days_per_week"
              render={({ field }) => (
                <FormItem>
                  <div className="flex items-center justify-between">
                    <FormLabel className="text-foreground">Days per week</FormLabel>
                    <span className="text-2xl font-semibold tabular-nums text-foreground">
                      {daysPerWeek}
                    </span>
                  </div>
                  <FormControl>
                    <input
                      type="range"
                      min={1}
                      max={7}
                      step={1}
                      value={field.value}
                      onChange={(e) => field.onChange(Number(e.target.value))}
                      className="mt-4 w-full h-1 cursor-pointer appearance-none rounded-full bg-muted
                        [&::-webkit-slider-thumb]:appearance-none
                        [&::-webkit-slider-thumb]:h-3.5
                        [&::-webkit-slider-thumb]:w-3.5
                        [&::-webkit-slider-thumb]:rounded-full
                        [&::-webkit-slider-thumb]:bg-foreground
                        [&::-moz-range-thumb]:h-3.5
                        [&::-moz-range-thumb]:w-3.5
                        [&::-moz-range-thumb]:rounded-full
                        [&::-moz-range-thumb]:border-0
                        [&::-moz-range-thumb]:bg-foreground"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="session_minutes"
              render={({ field }) => (
                <FormItem>
                  <div className="flex items-center justify-between">
                    <FormLabel className="text-foreground">Minutes per session</FormLabel>
                    <span className="text-2xl font-semibold tabular-nums text-foreground">
                      {sessionMinutes}
                    </span>
                  </div>
                  <FormControl>
                    <input
                      type="range"
                      min={10}
                      max={120}
                      step={5}
                      value={field.value}
                      onChange={(e) => field.onChange(Number(e.target.value))}
                      className="mt-4 w-full h-1 cursor-pointer appearance-none rounded-full bg-muted
                        [&::-webkit-slider-thumb]:appearance-none
                        [&::-webkit-slider-thumb]:h-3.5
                        [&::-webkit-slider-thumb]:w-3.5
                        [&::-webkit-slider-thumb]:rounded-full
                        [&::-webkit-slider-thumb]:bg-foreground
                        [&::-moz-range-thumb]:h-3.5
                        [&::-moz-range-thumb]:w-3.5
                        [&::-moz-range-thumb]:rounded-full
                        [&::-moz-range-thumb]:border-0
                        [&::-moz-range-thumb]:bg-foreground"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        {/* ---------- Section 2.5: Experience & Style ---------- */}
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="text-foreground">Training profile</CardTitle>
            <CardDescription className="text-muted-foreground">
              Helps calibrate initial progression steps and periodisation focus.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-8">
            <FormField
              control={form.control}
              name="experience_level"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-foreground">Experience level</FormLabel>
                  <FormControl>
                    <div className="flex flex-wrap gap-2">
                      {["beginner", "intermediate", "advanced"].map((level) => {
                        const checked = field.value === level;
                        return (
                          <button
                            key={level}
                            type="button"
                            onClick={() => field.onChange(level)}
                            className={`inline-flex items-center rounded-full border px-4 py-2 text-xs font-medium transition-colors ${
                              checked
                                ? "border-foreground bg-foreground text-background"
                                : "border-border bg-card text-muted-foreground hover:border-foreground/40 hover:text-foreground"
                            }`}
                          >
                            {level.charAt(0).toUpperCase() + level.slice(1)}
                          </button>
                        );
                      })}
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="training_style"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-foreground">Primary focus</FormLabel>
                  <FormControl>
                    <div className="flex flex-wrap gap-2">
                      {["Strength", "Hypertrophy", "Endurance", "Skill"].map((style) => {
                        const checked = field.value === style;
                        return (
                          <button
                            key={style}
                            type="button"
                            onClick={() => field.onChange(style)}
                            className={`inline-flex items-center rounded-full border px-4 py-2 text-xs font-medium transition-colors ${
                              checked
                                ? "border-foreground bg-foreground text-background"
                                : "border-border bg-card text-muted-foreground hover:border-foreground/40 hover:text-foreground"
                            }`}
                          >
                            {style}
                          </button>
                        );
                      })}
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        {/* ---------- Section 3: Equipment ---------- */}
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-foreground">
              <span>Available equipment</span>
              {equipmentCount > 0 && (
                <Badge className="bg-emerald-50 text-emerald-800 border-emerald-200">
                  {equipmentCount} selected
                </Badge>
              )}
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Determines which force vectors and lever positions are available in your programme.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FormField
              control={form.control}
              name="equipment"
              render={({ field }) => (
                <FormItem>
                  <div className="flex flex-wrap gap-2">
                    {EQUIPMENT_OPTIONS.map((opt) => {
                      const checked = field.value.includes(opt.slug);
                      return (
                        <button
                          key={opt.slug}
                          type="button"
                          onClick={() => {
                            if (checked) {
                              field.onChange(field.value.filter((v) => v !== opt.slug));
                            } else {
                              field.onChange([...field.value, opt.slug]);
                            }
                          }}
                          className={`inline-flex items-center rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                            checked
                              ? "border-emerald-700 bg-emerald-50 text-emerald-900"
                              : "border-border bg-card text-muted-foreground hover:border-foreground/40 hover:text-foreground"
                          }`}
                        >
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        {/* ---------- Section 4: AI Assessment Toggle ---------- */}
        <div className="space-y-6">
          <FormField
            control={form.control}
            name="not_sure_goals"
            render={({ field }) => (
              <div className="flex items-center gap-3 rounded-lg border border-border bg-card p-4">
                <button
                  type="button"
                  onClick={() => {
                    field.onChange(!field.value);
                    if (!field.value) {
                      form.setValue("current_skills", []);
                    }
                  }}
                  className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors ${
                    field.value ? "bg-foreground" : "bg-input"
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-background shadow ring-0 transition duration-200 ease-in-out ${
                      field.value ? "translate-x-4" : "translate-x-0"
                    }`}
                  />
                </button>
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-foreground">Not sure — test my base strength</span>
                  <span className="text-xs text-muted-foreground">We will automatically generate a full baseline assessment.</span>
                </div>
              </div>
            )}
          />

          {/* ---------- Section 5: Current & Goal skills ---------- */}
          <div className="space-y-6">
            {!form.watch("not_sure_goals") && (
              <SkillsSection
                form={form}
                fieldName="current_skills"
                title="Current skill baseline"
                description="Mark every movement you can perform with consistent, controlled form. Overreporting leads to inaccurate programming."
                count={currentSkillsCount}
                selectedEquipment={form.watch("equipment")}
                excludeSlugs={[]}
              />
            )}

            <SkillsSection
              form={form}
              fieldName="goal_skills"
              title="Target skill objectives"
              description="Select 1–5 skills. rvector will identify the biomechanical gap and engineer the progression path."
              count={goalSkillsCount}
              selectedEquipment={form.watch("equipment")}
              excludeSlugs={form.watch("current_skills")}
              accent
            />
          </div>
        </div>

        {/* ---------- Section 6: Injuries ---------- */}
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="text-foreground">Contraindications</CardTitle>
            <CardDescription className="text-muted-foreground">
              Injuries, mobility deficits, loading restrictions. rvector will exclude or modify affected patterns.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FormField
              control={form.control}
              name="injuries"
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <Textarea
                      {...field}
                      placeholder="e.g. Tight shoulder mobility — go easy on overhead work. No wrist pain so far."
                      className="min-h-[100px] bg-background border-border text-foreground"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        {/* ---------- Submit ---------- */}
        {serverError && (
          <div className="rounded border border-red-300 bg-red-50 p-4 text-sm text-red-800">
            {serverError}
          </div>
        )}
        <div className="flex justify-end">
          <Button
            type="submit"
            disabled={isPending}
            size="lg"
            className="bg-foreground text-background hover:opacity-90 disabled:opacity-50"
          >
            {isPending ? "Saving…" : "Run initial assessment →"}
          </Button>
        </div>
      </form>
    </Form>
  );
}

// ---------- Skills picker, reused for current + goal ----------

type SkillsSectionProps = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  form: any;
  fieldName: "current_skills" | "goal_skills";
  title: string;
  description: string;
  count: number;
  selectedEquipment: string[];
  excludeSlugs: string[];
  accent?: boolean;
};

function SkillsSection({
  form,
  fieldName,
  title,
  description,
  count,
  selectedEquipment,
  excludeSlugs,
  accent,
}: SkillsSectionProps) {
  const isFiltered = selectedEquipment.length > 0;

  return (
    <Card className="border-border bg-card">
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-foreground">
          <span>{title}</span>
          <div className="flex items-center gap-2">
            {isFiltered && (
              <span className="font-mono text-[9px] uppercase tracking-wider text-amber-700 border border-amber-200 bg-amber-50 rounded px-1.5 py-0.5">
                filtered by equipment
              </span>
            )}
            {count > 0 && (
              <Badge
                className={
                  accent
                    ? "bg-cyan-50 text-cyan-800 border-cyan-200"
                    : "bg-emerald-50 text-emerald-800 border-emerald-200"
                }
              >
                {count} selected
              </Badge>
            )}
          </div>
        </CardTitle>
        <CardDescription className="text-muted-foreground">{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <FormField
          control={form.control}
          name={fieldName}
          render={({ field }: { field: { value: string[]; onChange: (v: string[]) => void } }) => (
            <FormItem>
              <div className="space-y-5">
                {CATEGORIES.map((cat) => (
                  <CategoryBlock
                    key={cat.value}
                    category={cat.value}
                    label={cat.label}
                    selected={field.value}
                    selectedEquipment={selectedEquipment}
                    excludeSlugs={excludeSlugs}
                    onToggle={(slug) => {
                      if (field.value.includes(slug)) {
                        field.onChange(field.value.filter((v) => v !== slug));
                      } else {
                        field.onChange([...field.value, slug]);
                      }
                    }}
                    accent={accent}
                  />
                ))}
              </div>
              <FormMessage />
            </FormItem>
          )}
        />
      </CardContent>
    </Card>
  );
}

function CategoryBlock({
  category,
  label,
  selected,
  selectedEquipment,
  excludeSlugs,
  onToggle,
  accent,
}: {
  category: SkillCategory;
  label: string;
  selected: string[];
  selectedEquipment: string[];
  excludeSlugs: string[];
  onToggle: (slug: string) => void;
  accent?: boolean;
}) {
  const skills: Skill[] = getAvailableSkills(category, selectedEquipment, excludeSlugs);

  const groupedSkills = skills.reduce((acc, skill) => {
    const key = skill.family || skill.slug;
    if (!acc[key]) acc[key] = [];
    acc[key].push(skill);
    return acc;
  }, {} as Record<string, Skill[]>);

  if (skills.length === 0) return null;

  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      <div className="flex flex-wrap gap-2">
        {Object.entries(groupedSkills).map(([key, groupSkills]) => {
          if (groupSkills.length === 1 && (!groupSkills[0].family || groupSkills[0].family === groupSkills[0].slug)) {
            const s = groupSkills[0];
            const checked = selected.includes(s.slug);
            const checkedClass = accent
              ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-900 dark:text-cyan-100"
              : "border-emerald-500/30 bg-emerald-500/10 text-emerald-900 dark:text-emerald-100";
            return (
              <button
                key={s.slug}
                type="button"
                onClick={() => onToggle(s.slug)}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                  checked
                    ? checkedClass
                    : "border-border bg-card text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                <DifficultyDots level={s.difficulty} checked={checked} />
                {s.label}
              </button>
            );
          } else {
            return (
              <SkillGroup
                key={key}
                family={key}
                skills={groupSkills}
                selected={selected}
                onToggle={onToggle}
                accent={accent}
              />
            );
          }
        })}
      </div>
    </div>
  );
}

function SkillGroup({
  family,
  skills,
  selected,
  onToggle,
  accent,
}: {
  family: string;
  skills: Skill[];
  selected: string[];
  onToggle: (slug: string) => void;
  accent?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const selectedCount = skills.filter((s) => selected.includes(s.slug)).length;

  const hasSelectionClass = accent
    ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-900 dark:text-cyan-100"
    : "border-emerald-500/30 bg-emerald-500/10 text-emerald-900 dark:text-emerald-100";

  return (
    <div className={`flex flex-col rounded-2xl border transition-colors ${selectedCount > 0 ? hasSelectionClass : "border-border bg-card"}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
          selectedCount > 0 ? "text-current" : "text-muted-foreground hover:text-foreground"
        }`}
      >
        <span className="flex items-center gap-1.5">
          {isOpen ? (
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m18 15-6-6-6 6"/></svg>
          ) : (
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6"/></svg>
          )}
          {family}
        </span>
        {selectedCount > 0 && (
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-foreground text-[11px] font-bold text-background shadow-sm">
            {selectedCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="flex flex-wrap gap-2 p-2 pt-0">
          {skills.map((s) => {
            const checked = selected.includes(s.slug);
            const checkedClass = accent
              ? "border-cyan-500/30 bg-cyan-500/20 text-cyan-950 dark:text-cyan-50"
              : "border-emerald-500/30 bg-emerald-500/20 text-emerald-950 dark:text-emerald-50";
            return (
              <button
                key={s.slug}
                type="button"
                onClick={() => onToggle(s.slug)}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                  checked
                    ? checkedClass
                    : "border-transparent bg-foreground/5 text-foreground/70 hover:bg-foreground/10 hover:text-foreground"
                }`}
              >
                <DifficultyDots level={s.difficulty} checked={checked} />
                {s.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function DifficultyDots({ level, checked }: { level: number; checked: boolean }) {
  return (
    <span className="flex gap-[2px]">
      {[1, 2, 3, 4, 5].map((i) => (
        <span
          key={i}
          className={`h-1 w-1 rounded-full bg-current transition-opacity ${
            i <= level ? "opacity-100" : "opacity-25"
          }`}
        />
      ))}
    </span>
  );
}
