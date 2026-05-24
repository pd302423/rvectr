import { z } from "zod";

export const profileSchema = z.object({
  display_name: z.string().min(1, "Required").max(80),
  days_per_week: z.number().int().min(1).max(7),
  session_minutes: z.number().int().min(10).max(240),
  equipment: z.array(z.string()).min(1, "Pick at least one (or 'Nothing')"),
  current_skills: z.array(z.string()),
  goal_skills: z.array(z.string()).min(1, "Pick at least one goal skill"),
  injuries: z.string().max(2000),
});

export type ProfileInput = z.infer<typeof profileSchema>;
