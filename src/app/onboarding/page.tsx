import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { OnboardingForm } from "./form";

export default async function OnboardingPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) redirect("/signin");

  const { data: profile } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user.id)
    .single();

  if (profile?.onboarded) redirect("/dashboard");

  return (
    <main className="min-h-screen bg-background py-12 px-6">
      <div className="mx-auto max-w-2xl">

        <header className="mb-12 border-b border-border pb-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground mb-4">
            § Initial assessment
          </p>
          <h1
            style={{ fontFamily: "var(--font-serif)" }}
            className="text-5xl leading-tight tracking-tight"
          >
            Athlete profile.
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground max-w-lg">
            rvector requires this data to generate biomechanically accurate programming.
            All fields inform the periodisation model — be precise.
          </p>
        </header>

        <OnboardingForm
          defaultDisplayName={profile?.display_name ?? user.email?.split("@")[0] ?? ""}
        />
      </div>
    </main>
  );
}
