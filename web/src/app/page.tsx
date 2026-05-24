import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { isSupabaseConfigured } from "@/lib/supabase/env";

export default async function Home() {
  if (isSupabaseConfigured()) {
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      const { data: profile } = await supabase
        .from("profiles")
        .select("onboarded")
        .eq("id", user.id)
        .single();
      redirect(profile?.onboarded ? "/dashboard" : "/onboarding");
    }
  }

  return (
    <main className="bg-background text-foreground">

      {/* ──────── NAV ──────── */}
      <nav className="fixed inset-x-0 top-0 z-50 border-b border-border bg-background">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-8 py-4">
          <span style={{ fontFamily: "var(--font-serif)" }} className="text-lg italic tracking-tight">
            Vector
          </span>
          <div className="flex items-center gap-8">
            <a href="#methodology" className="hidden sm:block text-xs text-muted-foreground hover:text-foreground transition-colors tracking-wide">
              Methodology
            </a>
            <a href="#measurements" className="hidden sm:block text-xs text-muted-foreground hover:text-foreground transition-colors tracking-wide">
              Measurements
            </a>
            <Link
              href="/signin"
              className="text-xs text-foreground tracking-wide border-b border-foreground/30 pb-0.5 hover:border-foreground transition-colors"
            >
              Sign in
            </Link>
          </div>
        </div>
      </nav>

      {/* ──────── HERO — asymmetric 8/4 ──────── */}
      <section className="border-b border-border pt-32 pb-24">
        <div className="mx-auto max-w-7xl px-8">
          <div className="grid grid-cols-1 gap-16 lg:grid-cols-12 lg:gap-12">

            {/* Left: Editorial display */}
            <div className="lg:col-span-8">
              <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground mb-12">
                Calisthenics · Coaching system · v0.1
              </p>
              <h1
                style={{ fontFamily: "var(--font-serif)" }}
                className="text-[clamp(3rem,8vw,7.5rem)] leading-[0.95] tracking-tight font-normal"
              >
                A coaching
                <br />
                system that
                <br />
                <span className="italic text-muted-foreground">watches you</span>
                <br />
                train.
              </h1>
            </div>

            {/* Right: dense info column */}
            <div className="lg:col-span-4 lg:pt-32">
              <div className="space-y-8">
                <p className="text-sm leading-relaxed text-muted-foreground">
                  Vector measures every joint angle of every rep. When it detects struggle,
                  form degradation, or readiness for progression, it adapts your training
                  in real time.
                </p>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  Programming follows <em className="italic">Overcoming Gravity</em> (Low, 2016),
                  NSCA periodisation standards, and peer-reviewed sports biomechanics literature.
                  Vector cites its sources.
                </p>
                <div className="pt-4">
                  <Link
                    href="/signin"
                    className="inline-flex items-center gap-3 text-sm border-b border-foreground pb-1.5 hover:gap-4 transition-all"
                  >
                    Begin initial assessment
                    <span>→</span>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ──────── SAMPLE SESSION REPORT — single large diagnostic ──────── */}
      <section className="border-b border-border py-24">
        <div className="mx-auto max-w-7xl px-8">

          {/* Meta header */}
          <div className="mb-12 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground mb-3">
                Sample session report
              </p>
              <h2
                style={{ fontFamily: "var(--font-serif)" }}
                className="text-4xl leading-tight tracking-tight"
              >
                Anatomy of a Vector session.
              </h2>
            </div>
            <p className="text-xs text-muted-foreground sm:text-right max-w-xs">
              Each session produces a structured report.
              <br />
              Below is the actual output format.
            </p>
          </div>

          {/* The full report — a single dense lab-style document */}
          <SessionReport />

        </div>
      </section>

      {/* ──────── METHODOLOGY — long-form editorial ──────── */}
      <section id="methodology" className="border-b border-border py-32">
        <div className="mx-auto max-w-3xl px-8">

          <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground mb-6">
            § 01 — Methodology
          </p>

          <h2
            style={{ fontFamily: "var(--font-serif)" }}
            className="text-5xl leading-tight tracking-tight mb-12"
          >
            Coaching, but as <span className="italic">measurement</span>.
          </h2>

          <div className="space-y-8 text-base leading-[1.75] text-foreground/85 max-w-prose">
            <p>
              Most fitness applications produce scores. Vector produces diagnoses.
              The distinction is consequential. A score is an opinion compressed into a number;
              a diagnosis is a measurement paired with a clinical interpretation, citable
              to the literature it derives from.
            </p>

            <p>
              When you perform a pull-up in front of your camera, Vector extracts
              thirty-three skeletal landmarks at thirty frames per second using Google&apos;s
              MediaPipe pose estimation. From these, the system computes joint angles —
              elbow flexion, scapular position, glenohumeral elevation, lumbar curvature —
              and compares each against population-validated standards drawn from the{" "}
              <em>Journal of Strength and Conditioning Research</em>, the NSCA{" "}
              <em>Essentials of Strength Training and Conditioning</em>, and the FIG Code
              of Points for gymnastic movements.
            </p>

            <p>
              Rep counting is the trivial part. The substantive output is the{" "}
              <span className="text-foreground">struggle profile</span>:
              the velocity at which each rep was completed, the form deviation observed
              across the set, the inter-rep rest pattern. From this profile Vector
              estimates the&nbsp;<em>effective</em> rep count, distinct from the counted
              rep count, and uses the difference to inform the next session.
            </p>

            <PullQuote
              text="A movement performed at sixty percent of fresh velocity is not the same movement. Vector treats it as a different data point."
              source="Vector technical documentation, § 4.2"
            />

            <p>
              Programming is structured around the periodisation principles articulated
              in Steven Low&apos;s <em>Overcoming Gravity</em> (2nd ed., 2016): block
              periodisation with intra-week intensity oscillation, push-pull-core volume
              balance, prerequisite gating between skill progressions, and explicit
              connective-tissue adaptation windows. Vector will not advance an athlete
              to the next progression purely on the basis of acute strength; tendon
              adaptation timelines (typically eight to twelve weeks per progression) are
              enforced.
            </p>

            <p>
              The result is a coaching system that behaves less like a fitness app and
              more like a laboratory instrument. It does not motivate. It does not gamify.
              It measures.
            </p>
          </div>

          {/* citations */}
          <div className="mt-16 border-t border-border pt-8">
            <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground mb-4">
              References
            </p>
            <ol className="space-y-2 text-xs text-muted-foreground font-mono leading-relaxed">
              <li>[1] Low, S. (2016). <em className="italic font-sans">Overcoming Gravity</em>, 2nd ed. Battle Ground Creative.</li>
              <li>[2] Haff, G.G. & Triplett, N.T. (2016). <em className="italic font-sans">NSCA&apos;s Essentials of Strength Training and Conditioning</em>, 4th ed.</li>
              <li>[3] Hewett, T.E. et al. (2005). <em className="italic font-sans">Am J Sports Med</em>, 33(4):492-501. Biomechanical measures of neuromuscular control.</li>
              <li>[4] Ludewig, P.M. & Cook, T.M. (2000). <em className="italic font-sans">JOSPT</em>, 30(1):24-37. Alterations in shoulder kinematics.</li>
              <li>[5] FIG Code of Points (2022). Men&apos;s Artistic Gymnastics. Fédération Internationale de Gymnastique.</li>
            </ol>
          </div>

        </div>
      </section>

      {/* ──────── WHAT IS MEASURED — spec table ──────── */}
      <section id="measurements" className="border-b border-border py-32">
        <div className="mx-auto max-w-7xl px-8">

          <div className="grid grid-cols-1 gap-16 lg:grid-cols-12">
            <div className="lg:col-span-4">
              <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground mb-6">
                § 02 — Measurements
              </p>
              <h2
                style={{ fontFamily: "var(--font-serif)" }}
                className="text-4xl leading-tight tracking-tight"
              >
                Every metric Vector observes.
              </h2>
              <p className="mt-6 text-sm leading-relaxed text-muted-foreground max-w-xs">
                Continuous measurement across the kinematic, performance, and
                physiological domains. All values are real-time.
              </p>
            </div>

            <div className="lg:col-span-8">
              <SpecTable />
            </div>
          </div>

        </div>
      </section>

      {/* ──────── CTA — minimal ──────── */}
      <section className="py-32">
        <div className="mx-auto max-w-3xl px-8 text-center">
          <h2
            style={{ fontFamily: "var(--font-serif)" }}
            className="text-5xl leading-tight tracking-tight"
          >
            Begin your initial assessment.
          </h2>
          <p className="mt-6 text-sm leading-relaxed text-muted-foreground max-w-md mx-auto">
            Vector requires a baseline athlete profile before it can generate programming.
            Setup takes approximately two minutes.
          </p>
          <div className="mt-10">
            <Link
              href="/signin"
              className="inline-flex items-center gap-3 text-sm border-b border-foreground pb-1.5 hover:gap-4 transition-all"
            >
              Continue to authentication
              <span>→</span>
            </Link>
          </div>
        </div>
      </section>

      {/* ──────── FOOTER ──────── */}
      <footer className="border-t border-border">
        <div className="mx-auto max-w-7xl px-8 py-12">
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            <div>
              <p style={{ fontFamily: "var(--font-serif)" }} className="text-lg italic">
                Vector
              </p>
              <p className="mt-2 font-mono text-[11px] text-muted-foreground">
                v0.1.0 · calisthenics build
              </p>
            </div>
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground mb-3">
                System
              </p>
              <ul className="space-y-1.5 text-xs text-muted-foreground">
                <li>Methodology</li>
                <li>Citations</li>
                <li>Changelog</li>
              </ul>
            </div>
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground mb-3">
                Legal
              </p>
              <ul className="space-y-1.5 text-xs text-muted-foreground">
                <li>Privacy</li>
                <li>Terms</li>
                <li>Not medical advice</li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}

/* ─────────────────────────────────────────────
   Pull quote — editorial component
   ───────────────────────────────────────────── */

function PullQuote({ text, source }: { text: string; source: string }) {
  return (
    <blockquote className="my-12 border-l-2 border-foreground pl-6 py-2">
      <p
        style={{ fontFamily: "var(--font-serif)" }}
        className="text-2xl leading-snug italic"
      >
        &ldquo;{text}&rdquo;
      </p>
      <cite className="mt-3 block font-mono text-[11px] not-italic uppercase tracking-[0.2em] text-muted-foreground">
        — {source}
      </cite>
    </blockquote>
  );
}

/* ─────────────────────────────────────────────
   Session report — the big diagnostic mockup
   ───────────────────────────────────────────── */

function SessionReport() {
  return (
    <div className="border border-border bg-card font-mono text-xs">

      {/* ── Document header ── */}
      <header className="grid grid-cols-2 gap-x-8 gap-y-4 border-b border-border px-6 py-5 sm:grid-cols-4">
        <Field label="athlete_id" value="ATH-0042" />
        <Field label="session_id" value="SES-2026-05-23-T1845" />
        <Field label="duration" value="00:42:17" />
        <Field label="status" value="completed" tone="emerald" />
      </header>

      {/* ── Movement: Pull-up ── */}
      <div className="border-b border-border">
        <div className="flex items-baseline justify-between border-b border-border bg-secondary/30 px-6 py-3">
          <p className="text-foreground"><span className="text-muted-foreground">movement_01</span> &nbsp; pull_up</p>
          <p className="text-muted-foreground">sets: 4 / reps_counted: 26 / effective: 22.4</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2">

          {/* Rep-by-rep table */}
          <div className="border-b border-border lg:border-b-0 lg:border-r">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-border bg-secondary/20">
                  <th className="text-left px-6 py-2 text-muted-foreground font-medium uppercase tracking-wider">set·rep</th>
                  <th className="text-right px-6 py-2 text-muted-foreground font-medium uppercase tracking-wider">elbow_top</th>
                  <th className="text-right px-6 py-2 text-muted-foreground font-medium uppercase tracking-wider">velocity</th>
                  <th className="text-right px-6 py-2 text-muted-foreground font-medium uppercase tracking-wider">quality</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {([
                  ["1·1", "176°", "1.00", "1.00", "emerald"],
                  ["1·3", "175°", "0.94", "0.98", "emerald"],
                  ["1·5", "173°", "0.82", "0.92", "emerald"],
                  ["1·7", "168°", "0.61", "0.78", "amber"],
                  ["1·8", "162°", "0.41", "0.54", "red"],
                  ["2·1", "175°", "0.96", "0.99", "emerald"],
                  ["2·5", "169°", "0.71", "0.84", "amber"],
                  ["2·7", "159°", "0.38", "0.46", "red"],
                ] as const).map(([id, angle, vel, qual, tone]) => {
                  const toneClass =
                    tone === "emerald" ? "text-emerald-700"
                    : tone === "amber" ? "text-amber-700"
                    : "text-red-700";
                  return (
                    <tr key={id}>
                      <td className="px-6 py-1.5 text-muted-foreground">{id}</td>
                      <td className={`px-6 py-1.5 text-right tabular-nums ${toneClass}`}>{angle}</td>
                      <td className={`px-6 py-1.5 text-right tabular-nums ${toneClass}`}>{vel}</td>
                      <td className={`px-6 py-1.5 text-right tabular-nums ${toneClass}`}>{qual}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Velocity curve SVG */}
          <div className="px-6 py-5">
            <p className="text-muted-foreground uppercase tracking-wider text-[10px] mb-4">velocity curve (set 1)</p>
            <svg
              viewBox="0 0 280 110"
              className="w-full"
              preserveAspectRatio="none"
              data-darkreader-ignore
            >
              {/* baseline + gridlines */}
              <line x1="0" y1="80" x2="280" y2="80" stroke="oklch(0 0 0 / 12%)" strokeWidth="1" />
              <line x1="0" y1="50" x2="280" y2="50" stroke="oklch(0 0 0 / 6%)" strokeWidth="1" strokeDasharray="2 4" />
              <line x1="0" y1="20" x2="280" y2="20" stroke="oklch(0 0 0 / 6%)" strokeWidth="1" strokeDasharray="2 4" />
              {/* velocity drop curve */}
              <polyline
                points="0,20 35,22 70,28 105,40 140,55 175,68 210,82 245,92"
                fill="none"
                stroke="oklch(0.50 0.16 162)"
                strokeWidth="1.5"
              />
              {/* fail threshold */}
              <line x1="0" y1="70" x2="280" y2="70" stroke="oklch(0 0 0 / 22%)" strokeWidth="1" strokeDasharray="3 3" />
              <text
                x="276"
                y="68"
                fill="oklch(0.50 0 0)"
                textAnchor="end"
                fontSize="9"
                fontFamily="var(--font-geist-mono), monospace"
              >
                failure_threshold
              </text>
            </svg>
            <div className="mt-4 grid grid-cols-3 gap-2 text-[10px]">
              <div>
                <p className="text-muted-foreground">v_drop</p>
                <p className="text-foreground tabular-nums">−59%</p>
              </div>
              <div>
                <p className="text-muted-foreground">fail_at_rep</p>
                <p className="text-foreground tabular-nums">8 of 8</p>
              </div>
              <div>
                <p className="text-muted-foreground">limit_factor</p>
                <p className="text-foreground">scap. fatigue</p>
              </div>
            </div>
          </div>

        </div>

        {/* Movement diagnosis */}
        <div className="border-t border-border bg-secondary/20 px-6 py-4">
          <p className="text-muted-foreground uppercase tracking-wider text-[10px] mb-2">diagnosis</p>
          <p className="text-foreground leading-relaxed font-sans">
            Scapular depression strength is the limiting factor — not pulling strength.
            Velocity collapse precedes form failure by ~1 rep, indicating central rather
            than peripheral fatigue. Confirmed 3 sessions running. Prescribed corrective:
            band pull-aparts 2×20 + scapular pull-ups 3×8 prior to next pulling session.
          </p>
        </div>
      </div>

      {/* ── Movement: Pseudo planche push-up ── */}
      <div className="border-b border-border">
        <div className="flex items-baseline justify-between border-b border-border bg-secondary/30 px-6 py-3">
          <p className="text-foreground"><span className="text-muted-foreground">movement_02</span> &nbsp; pseudo_planche_push_up</p>
          <p className="text-muted-foreground">sets: 3 / reps_counted: 18 / effective: 16.8</p>
        </div>
        <div className="grid grid-cols-2 gap-x-8 gap-y-4 px-6 py-5 sm:grid-cols-4">
          <Field label="lean_angle_avg" value="22°" tone="emerald" />
          <Field label="wrist_extension" value="68°" tone="emerald" />
          <Field label="elbow_flare" value="36°" tone="emerald" />
          <Field label="form_score" value="0.93" tone="emerald" />
        </div>
        <div className="border-t border-border bg-secondary/20 px-6 py-4">
          <p className="text-muted-foreground uppercase tracking-wider text-[10px] mb-2">progression status</p>
          <p className="text-foreground leading-relaxed font-sans">
            Week 4 of 8 in current progression. Form quality consistent across volume.
            Connective tissue adaptation window: 4 weeks remaining before tuck planche
            attempt clearance. Continue current intensity.
          </p>
        </div>
      </div>

      {/* ── Session summary ── */}
      <div className="grid grid-cols-2 gap-x-8 gap-y-4 px-6 py-5 sm:grid-cols-4">
        <Field label="weekly_volume" value="68 sets" />
        <Field label="weekly_load" value="nominal" tone="emerald" />
        <Field label="next_session" value="+2 days" />
        <Field label="next_focus" value="legs · core" />
      </div>
    </div>
  );
}

function Field({ label, value, tone = "fg" }: { label: string; value: string; tone?: "fg" | "emerald" | "amber" | "red" }) {
  const colorMap = {
    fg: "text-foreground",
    emerald: "text-emerald-700",
    amber: "text-amber-700",
    red: "text-red-700",
  };
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className={`mt-1 tabular-nums ${colorMap[tone]}`}>{value}</p>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Spec table — what's measured
   ───────────────────────────────────────────── */

function SpecTable() {
  const rows: { domain: string; metric: string; unit: string; rate: string }[] = [
    { domain: "Kinematic", metric: "Joint angles (33 landmarks)", unit: "degrees", rate: "30 Hz" },
    { domain: "Kinematic", metric: "Angular velocity", unit: "deg/s", rate: "30 Hz" },
    { domain: "Kinematic", metric: "Joint trajectory deviation", unit: "mm", rate: "30 Hz" },
    { domain: "Kinematic", metric: "Bilateral asymmetry", unit: "percent", rate: "per rep" },
    { domain: "Performance", metric: "Effective rep count", unit: "reps", rate: "per set" },
    { domain: "Performance", metric: "Velocity loss across set", unit: "percent", rate: "per set" },
    { domain: "Performance", metric: "Form degradation index", unit: "0–1", rate: "per rep" },
    { domain: "Performance", metric: "Inter-rep rest pattern", unit: "seconds", rate: "per set" },
    { domain: "Periodisation", metric: "Weekly volume (sets)", unit: "sets/week", rate: "rolling 7d" },
    { domain: "Periodisation", metric: "Volume distribution (P/P/C/L)", unit: "ratio", rate: "rolling 7d" },
    { domain: "Periodisation", metric: "Connective tissue exposure", unit: "weeks", rate: "per movement" },
    { domain: "Periodisation", metric: "Deload markers", unit: "boolean", rate: "session-end" },
    { domain: "Physiological", metric: "Resting HR (via wearable)", unit: "bpm", rate: "daily" },
    { domain: "Physiological", metric: "HRV trend", unit: "ms", rate: "daily" },
    { domain: "Physiological", metric: "Sleep duration", unit: "hours", rate: "daily" },
  ];

  let lastDomain = "";
  return (
    <div className="border border-border">
      <div className="border-b border-border bg-secondary/30 grid grid-cols-12 px-4 py-2.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
        <div className="col-span-3">Domain</div>
        <div className="col-span-5">Metric</div>
        <div className="col-span-2">Unit</div>
        <div className="col-span-2 text-right">Sampling</div>
      </div>
      <div>
        {rows.map((r, i) => {
          const newDomain = r.domain !== lastDomain;
          lastDomain = r.domain;
          return (
            <div
              key={i}
              className="grid grid-cols-12 px-4 py-2.5 text-xs items-baseline border-b border-border/60 last:border-b-0"
            >
              <div className={`col-span-3 font-mono ${newDomain ? "text-foreground" : "text-muted-foreground/30"}`}>
                {newDomain ? r.domain : "·"}
              </div>
              <div className="col-span-5 text-foreground">{r.metric}</div>
              <div className="col-span-2 font-mono text-muted-foreground">{r.unit}</div>
              <div className="col-span-2 font-mono text-muted-foreground text-right">{r.rate}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
