import { type EmailOtpType } from "@supabase/supabase-js";
import { type NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const token_hash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const rawNext = searchParams.get("next") ?? "/onboarding";
  // Guard against open-redirect: only allow same-origin relative paths.
  const next = rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : "/onboarding";

  if (token_hash && type) {
    const supabase = await createClient();
    const { error } = await supabase.auth.verifyOtp({ type, token_hash });

    if (!error) {
      // Check if the user has completed onboarding; route accordingly.
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        const { data: profile } = await supabase
          .from("profiles")
          .select("onboarded")
          .eq("id", user.id)
          .single();

        if (profile?.onboarded) {
          return NextResponse.redirect(new URL("/dashboard", request.url));
        }
      }
      return NextResponse.redirect(new URL(next, request.url));
    }

    console.error("[auth/confirm] verifyOtp error:", error);
  }

  return NextResponse.redirect(
    new URL("/signin?error=invalid_or_expired_link", request.url),
  );
}
