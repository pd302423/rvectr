import Link from "next/link";
import { AuthForm } from "./auth-form";

export default async function SignInPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; message?: string; mode?: string }>;
}) {
  const params = await searchParams;

  return (
    <div className="flex min-h-screen flex-col lg:flex-row bg-background">

      {/* ── Left — identity panel ── */}
      <div className="relative flex flex-col justify-between overflow-hidden border-b border-border bg-card p-10 lg:w-1/2 lg:border-b-0 lg:border-r">

        {/* wordmark */}
        <Link href="/">
          <span style={{ fontFamily: "var(--font-serif)" }} className="text-2xl italic">
            Vector
          </span>
        </Link>

        {/* centre editorial display */}
        <div className="max-w-lg">
          <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground mb-8">
            Biomechanical coaching system
          </p>
          <h2
            style={{ fontFamily: "var(--font-serif)" }}
            className="text-[clamp(2rem,5vw,4rem)] leading-[1.05] tracking-tight"
          >
            Sign in to begin
            <br />
            <span className="italic text-muted-foreground">your initial</span>
            <br />
            assessment.
          </h2>

          {/* data callouts */}
          <div className="mt-12 grid grid-cols-3 gap-px border border-border bg-border">
            {[
              { v: "33", l: "skeletal landmarks tracked" },
              { v: "30 Hz", l: "real-time sampling rate" },
              { v: "0.93", l: "form classifier f1 score" },
            ].map(({ v, l }) => (
              <div key={v} className="bg-card p-4">
                <p className="font-mono text-xl tabular-nums text-foreground">{v}</p>
                <p className="mt-1 text-[10px] leading-snug text-muted-foreground">{l}</p>
              </div>
            ))}
          </div>

          <p className="mt-10 text-[11px] text-muted-foreground/60 leading-relaxed max-w-md">
            Standards from Low (2016), NSCA <em>CSCS Essentials</em> 4th ed.,
            and the FIG Code of Points for gymnastic movements.
          </p>
        </div>

        {/* version stamp */}
        <p className="font-mono text-[10px] text-muted-foreground/40 tracking-wider">
          vector · build 0.1.0 · calisthenics
        </p>
      </div>

      {/* ── Right — auth ── */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 bg-background">
        <div className="w-full max-w-sm">
          <AuthForm
            initialMode={params.mode === "signup" ? "signup" : "signin"}
            initialError={params.error}
            initialMessage={params.message}
          />

          <div className="mt-16 border-t border-border pt-6">
            <Link
              href="/"
              className="font-mono text-[11px] text-muted-foreground/50 hover:text-muted-foreground transition-colors tracking-wider"
            >
              ← vector
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
