"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useFormStatus } from "react-dom";
import { Input } from "@/components/ui/input";
import { signIn, signUp } from "./actions";

type Mode = "signin" | "signup";

// ─── Submit button with pending state ────────────────────────────────────────

function SubmitButton({ mode }: { mode: Mode }) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="group flex w-full items-center justify-between border-b border-foreground pb-2 pt-3 text-sm transition-all hover:pb-3 disabled:opacity-50"
    >
      <span>
        {pending
          ? mode === "signin" ? "Signing in…" : "Creating account…"
          : mode === "signin" ? "Sign in" : "Create account"}
      </span>
      {pending ? (
        <span className="inline-block h-3 w-3 rounded-full border-2 border-foreground/30 border-t-foreground animate-spin" />
      ) : (
        <span className="transition-transform group-hover:translate-x-1">→</span>
      )}
    </button>
  );
}

// ─── Main form ────────────────────────────────────────────────────────────────

export function AuthForm({
  initialMode = "signin",
  initialError,
  initialMessage,
}: {
  initialMode?: Mode;
  initialError?: string;
  initialMessage?: string;
}) {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>(initialMode);

  // Error and message are stored in local state so they can be cleared
  // independently of the URL — switching tabs clears the error, "Back to
  // sign in" navigates to /signin which resets everything.
  const [error, setError] = useState<string | undefined>(initialError);
  const [message, setMessage] = useState<string | undefined>(initialMessage);

  function switchMode(newMode: Mode) {
    if (newMode === mode) return;
    setMode(newMode);
    setError(undefined); // ← clears error when switching tabs
    if (message) {
      setMessage(undefined);
      router.replace("/signin", { scroll: false });
    }
  }

  return (
    <>
      {/* ── Eyebrow ── */}
      <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground mb-8">
        § Authentication
      </p>

      {/* ── Heading ── */}
      <h1
        style={{ fontFamily: "var(--font-serif)" }}
        className="text-4xl leading-tight tracking-tight"
      >
        {mode === "signin" ? "Sign in to rvector." : "Create your account."}
      </h1>

      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
        {mode === "signin"
          ? "Enter your email and password to continue."
          : "Choose a password — minimum 8 characters."}
      </p>

      {/* ── Mode toggle ── */}
      <div className="mt-8 flex gap-0 border-b border-border">
        {(["signin", "signup"] as Mode[]).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => switchMode(m)}
            className={`pb-2 pt-1 mr-6 font-mono text-[10px] uppercase tracking-[0.18em] transition-colors border-b-2 -mb-px ${
              mode === m
                ? "border-foreground text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {m === "signin" ? "Returning athlete" : "New athlete"}
          </button>
        ))}
      </div>

      {/* ── Confirm-email state ── */}
      {message === "confirm_email" ? (
        <div className="mt-10 space-y-4">
          <div className="border border-emerald-200 bg-emerald-50 px-4 py-3 font-mono text-xs">
            <span className="text-emerald-700">✓</span>
            <span className="ml-2 text-emerald-800">confirmation email sent</span>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            A confirmation link was sent to your inbox. Click it to activate
            your account, then return here to sign in.
          </p>
          <p className="text-xs text-muted-foreground/60">
            Can&apos;t find it? Check your spam folder.
          </p>
          {/* Full navigation — clears message from URL on hard refresh too */}
          <a
            href="/signin"
            className="inline-block font-mono text-xs text-foreground border-b border-foreground/30 hover:border-foreground transition-colors"
          >
            Back to sign in →
          </a>
        </div>
      ) : (
        /* ── Form ── */
        <form
          action={mode === "signin" ? signIn : signUp}
          className="mt-8 space-y-4"
        >
          <div className="space-y-1.5">
            <label
              htmlFor="email"
              className="font-mono text-[10px] text-muted-foreground uppercase tracking-[0.2em]"
            >
              Email address
            </label>
            <Input
              id="email"
              name="email"
              type="email"
              required
              autoFocus
              autoComplete="email"
              placeholder="you@example.com"
              className="h-11 bg-card border-border text-foreground placeholder:text-muted-foreground/40 font-mono text-sm rounded-none"
            />
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="password"
              className="font-mono text-[10px] text-muted-foreground uppercase tracking-[0.2em]"
            >
              Password
            </label>
            <Input
              id="password"
              name="password"
              type="password"
              required
              autoComplete={mode === "signin" ? "current-password" : "new-password"}
              placeholder={mode === "signup" ? "min. 8 characters" : "••••••••"}
              className="h-11 bg-card border-border text-foreground placeholder:text-muted-foreground/40 font-mono text-sm rounded-none"
            />
          </div>

          {error && (
            <div className="border border-red-200 bg-red-50 px-3 py-2.5 font-mono text-xs text-red-700 leading-relaxed">
              {decodeURIComponent(error)}
            </div>
          )}

          <SubmitButton mode={mode} />

          <p className="text-[11px] text-muted-foreground/50 leading-relaxed">
            Your data is private and used only to inform your biomechanical
            coaching profile. rvector does not sell or share athlete data.
          </p>
        </form>
      )}
    </>
  );
}
