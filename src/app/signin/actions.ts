"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { isSupabaseConfigured } from "@/lib/supabase/env";

// ── SIGN IN ────────────────────────────────────────────────────────────────────

export async function signIn(formData: FormData) {
  if (!isSupabaseConfigured()) {
    redirect("/signin?error=Supabase+not+configured");
  }

  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  if (!email || !password) {
    redirect("/signin?error=Email+and+password+are+required");
  }

  const supabase = await createClient();
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (error) {
    // Make the "email not confirmed" error actionable
    if (error.message.toLowerCase().includes("not confirmed")) {
      redirect(
        "/signin?error=Email+not+confirmed.+Check+your+inbox+for+the+confirmation+link,+then+try+again.+If+you+can%27t+find+it%2C+contact+the+organiser.",
      );
    }
    redirect(`/signin?error=${encodeURIComponent(error.message)}`);
  }

  // Use the user returned directly from sign-in (avoids a second round-trip)
  const user = data.user;
  if (!user) redirect("/signin?error=Sign+in+failed.+Please+try+again.");

  const { data: profile } = await supabase
    .from("profiles")
    .select("onboarded")
    .eq("id", user.id)
    .single();

  redirect(profile?.onboarded ? "/dashboard" : "/onboarding");
}

// ── SIGN UP ────────────────────────────────────────────────────────────────────

export async function signUp(formData: FormData) {
  if (!isSupabaseConfigured()) {
    redirect("/signin?error=Supabase+not+configured&mode=signup");
  }

  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  if (!email || !password) {
    redirect("/signin?error=Email+and+password+are+required&mode=signup");
  }

  if (password.length < 8) {
    redirect(
      "/signin?error=Password+must+be+at+least+8+characters&mode=signup",
    );
  }

  const supabase = await createClient();
  const headersList = await headers();
  const host = headersList.get("host") ?? "localhost:3000";
  const protocol = host.startsWith("localhost") ? "http" : "https";
  const origin = `${protocol}://${host}`;

  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo: `${origin}/auth/confirm`,
    },
  });

  if (error) {
    // Duplicate email — guide them to sign in instead
    if (
      error.message.toLowerCase().includes("already registered") ||
      error.message.toLowerCase().includes("already been registered") ||
      error.message.toLowerCase().includes("user already exists")
    ) {
      redirect(
        "/signin?error=An+account+with+this+email+already+exists.+Sign+in+instead.",
      );
    }
    redirect(
      `/signin?error=${encodeURIComponent(error.message)}&mode=signup`,
    );
  }

  // When Supabase has "Confirm email" disabled, signUp returns a session
  // immediately — redirect straight to onboarding.
  if (data.session) {
    redirect("/onboarding");
  }

  // "Confirm email" is enabled — ask the user to check their inbox.
  redirect("/signin?message=confirm_email");
}
