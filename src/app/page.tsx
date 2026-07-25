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
    <main className="bg-background text-foreground min-h-screen">

      {/* ──────── NAV ──────── */}
      <nav className="fixed inset-x-0 top-0 z-50 border-b border-border bg-background/95 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <span style={{ fontFamily: "var(--font-serif)" }} className="text-xl font-bold italic tracking-tight">
              rvectr
            </span>
            <span className="font-mono text-[10px] uppercase border border-border px-2 py-0.5 text-muted-foreground">
              v1.0-OSS
            </span>
          </div>

          <div className="flex items-center gap-6 font-mono text-xs">
            <Link href="/demo" className="hidden sm:block text-muted-foreground hover:text-foreground transition-colors">
              3D Workspace
            </Link>
            <Link href="/analysis" className="hidden sm:block text-muted-foreground hover:text-foreground transition-colors">
              Kinematics Lab
            </Link>
            <Link href="/test/squat" className="hidden sm:block text-muted-foreground hover:text-foreground transition-colors">
              Live CV
            </Link>
            <a href="#documentation" className="hidden sm:block text-muted-foreground hover:text-foreground transition-colors">
              Documentation
            </a>
            <a
              href="https://github.com/pd302423/rvectr"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 border border-foreground/30 px-3 py-1 text-foreground hover:bg-foreground hover:text-background transition-colors"
            >
              <span>GitHub</span>
              <span className="text-[10px]">↗</span>
            </a>
          </div>
        </div>
      </nav>

      {/* ──────── HERO — Asymmetric 8/4 ──────── */}
      <section className="border-b border-border pt-36 pb-24">
        <div className="mx-auto max-w-7xl px-8">
          <div className="grid grid-cols-1 gap-12 lg:grid-cols-12">

            {/* Left: Editorial display */}
            <div className="lg:col-span-8">
              <div className="flex items-center gap-3 mb-8">
                <span className="font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground">
                  Clinical Biomechanics · 3D Mesh Telemetry · Calisthenics
                </span>
              </div>
              <h1
                style={{ fontFamily: "var(--font-serif)" }}
                className="text-[clamp(3rem,7.5vw,7rem)] leading-[0.95] tracking-tight font-normal"
              >
                A clinical
                <br />
                system that
                <br />
                <span className="italic text-muted-foreground">watches you</span>
                <br />
                train.
              </h1>

              <div className="mt-12 flex flex-wrap items-center gap-4">
                <Link
                  href="/demo"
                  className="px-6 py-3 bg-foreground text-background font-mono text-xs font-bold uppercase tracking-wider hover:bg-foreground/90 transition-colors"
                >
                  Launch 3D Motion Command Workspace →
                </Link>
                <Link
                  href="/test/squat"
                  className="px-6 py-3 border border-border bg-card font-mono text-xs font-bold uppercase tracking-wider hover:bg-secondary transition-colors"
                >
                  Test Optical CV Telemetry
                </Link>
                <a
                  href="https://github.com/pd302423/rvectr"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-6 py-3 border border-border text-muted-foreground font-mono text-xs font-bold uppercase tracking-wider hover:text-foreground transition-colors flex items-center gap-2"
                >
                  <span>pd302423/rvectr</span>
                  <span>↗</span>
                </a>
              </div>
            </div>

            {/* Right: Dense info column */}
            <div className="lg:col-span-4 lg:pt-20">
              <div className="space-y-8 border-l border-border pl-8">
                <div className="space-y-2">
                  <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Primary Moat</p>
                  <p className="text-sm leading-relaxed text-foreground/90 font-mono">
                    Monocular (4D-Humans / HMR2) & Multi-view (EasyMocap) 3D Body Surface Mesh Recovery (SMPL 6,890-vertex parameters).
                  </p>
                </div>

                <div className="space-y-2">
                  <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Telemetry Engine</p>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    rvectr measures every joint angle of every rep. When it detects struggle, joint angular velocity collapse, or form degradation, it diagnoses biomechanical failure in real time.
                  </p>
                </div>

                <div className="space-y-2">
                  <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Sports Science Standards</p>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    Programming follows <em className="italic">Overcoming Gravity</em> (Low, 2016), NSCA periodisation standards, and peer-reviewed sports science literature.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ──────── DOCUMENTATION & ARCHITECTURE SECTION ──────── */}
      <section id="documentation" className="border-b border-border py-24 bg-card/30">
        <div className="mx-auto max-w-7xl px-8">
          <div className="mb-12">
            <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground mb-3">
              § 01 — Architectural Specs
            </p>
            <h2 style={{ fontFamily: "var(--font-serif)" }} className="text-4xl leading-tight tracking-tight">
              System Architecture & Open-Source Engine
            </h2>
            <p className="mt-2 text-sm text-muted-foreground font-mono">
              Complete technical specification for the rvectr motion capture & telemetry stack.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="border border-border p-6 bg-card space-y-4">
              <div className="font-mono text-xs text-muted-foreground uppercase tracking-wider">01 / Monocular HMR2</div>
              <h3 className="font-mono font-bold text-lg">4D-Humans SMPL Recovery</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Fits a 6,890-vertex SMPL body surface mesh directly from single-view consumer camera recordings using local PyTorch ViTDet models.
              </p>
              <div className="pt-2">
                <a
                  href="https://github.com/pd302423/rvectr/tree/main/backend/4D-Humans"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-[11px] underline text-muted-foreground hover:text-foreground"
                >
                  View 4D-Humans Submodule ↗
                </a>
              </div>
            </div>

            <div className="border border-border p-6 bg-card space-y-4">
              <div className="font-mono text-xs text-muted-foreground uppercase tracking-wider">02 / Multi-View Triangulation</div>
              <h3 className="font-mono font-bold text-lg">EasyMocap Triangulation</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Processes multi-camera synchronized recordings to perform 3D spatial keypoint triangulation, solving single-camera self-occlusion.
              </p>
              <div className="pt-2">
                <a
                  href="https://github.com/pd302423/rvectr/tree/main/backend/EasyMocap"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-[11px] underline text-muted-foreground hover:text-foreground"
                >
                  View EasyMocap Submodule ↗
                </a>
              </div>
            </div>

            <div className="border border-border p-6 bg-card space-y-4">
              <div className="font-mono text-xs text-muted-foreground uppercase tracking-wider">03 / WebGL Telemetry Canvas</div>
              <h3 className="font-mono font-bold text-lg">In-Browser Three.js Viewport</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Renders interactive 360° 3D mesh model sequences, real-time MediaPipe joint angle waveforms, and bilateral asymmetry matrices.
              </p>
              <div className="pt-2">
                <Link
                  href="/demo"
                  className="font-mono text-[11px] underline text-muted-foreground hover:text-foreground"
                >
                  Launch Interactive Demo →
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ──────── SAMPLE SESSION REPORT — Single large diagnostic ──────── */}
      <section className="border-b border-border py-24">
        <div className="mx-auto max-w-7xl px-8">

          {/* Meta header */}
          <div className="mb-12 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground mb-3">
                Sample Diagnostic Output
              </p>
              <h2
                style={{ fontFamily: "var(--font-serif)" }}
                className="text-4xl leading-tight tracking-tight"
              >
                Anatomy of a rvectr session.
              </h2>
            </div>
            <p className="text-xs font-mono text-muted-foreground sm:text-right max-w-xs">
              Continuous 30Hz joint telemetry stream & clinical diagnostic evaluation.
            </p>
          </div>

          <SessionReport />

        </div>
      </section>

      {/* ──────── WHAT IS MEASURED — Spec table ──────── */}
      <section id="measurements" className="border-b border-border py-24">
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
                Every metric rvectr observes.
              </h2>
              <p className="mt-6 text-sm leading-relaxed text-muted-foreground max-w-xs">
                Continuous measurement across kinematic, performance, and periodisation domains.
              </p>
            </div>

            <div className="lg:col-span-8">
              <SpecTable />
            </div>
          </div>

        </div>
      </section>

      {/* ──────── FOOTER ──────── */}
      <footer className="border-t border-border bg-card/20">
        <div className="mx-auto max-w-7xl px-8 py-12">
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            <div>
              <p style={{ fontFamily: "var(--font-serif)" }} className="text-xl italic font-bold">
                rvectr
              </p>
              <p className="mt-2 font-mono text-[11px] text-muted-foreground">
                v1.0.0 · Open Source Biomechanics Engine
              </p>
            </div>
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground mb-3">
                Open Source
              </p>
              <ul className="space-y-1.5 text-xs font-mono text-muted-foreground">
                <li>
                  <a href="https://github.com/pd302423/rvectr" target="_blank" rel="noopener noreferrer" className="hover:text-foreground">
                    GitHub Repository (pd302423/rvectr) ↗
                  </a>
                </li>
                <li>
                  <a href="https://github.com/pd302423/rvectr/blob/main/README.md" target="_blank" rel="noopener noreferrer" className="hover:text-foreground">
                    Documentation & Quickstart ↗
                  </a>
                </li>
                <li>
                  <a href="https://github.com/pd302423/rvectr/blob/main/WORKSPACE_SUMMARY.md" target="_blank" rel="noopener noreferrer" className="hover:text-foreground">
                    Architecture Specs ↗
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground mb-3">
                Live Workspaces
              </p>
              <ul className="space-y-1.5 text-xs font-mono text-muted-foreground">
                <li><Link href="/demo" className="hover:text-foreground">3D Motion Workspace</Link></li>
                <li><Link href="/analysis" className="hover:text-foreground">Kinematics Diagnostic Lab</Link></li>
                <li><Link href="/test/squat" className="hover:text-foreground">Live Optical CV Telemetry</Link></li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}

/* ─────────────────────────────────────────────
   Session report — diagnostic mockup component
   ───────────────────────────────────────────── */

function SessionReport() {
  return (
    <div className="border border-border bg-card font-mono text-xs">

      {/* Document header */}
      <header className="grid grid-cols-2 gap-x-8 gap-y-4 border-b border-border px-6 py-5 sm:grid-cols-4">
        <Field label="athlete_id" value="ATH-0042" />
        <Field label="session_id" value="SES-2026-07-25-T1845" />
        <Field label="duration" value="00:42:17" />
        <Field label="status" value="completed" tone="emerald" />
      </header>

      {/* Movement: Pull-up */}
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
                    tone === "emerald" ? "text-emerald-500"
                    : tone === "amber" ? "text-amber-500"
                    : "text-red-500";
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
            >
              <line x1="0" y1="80" x2="280" y2="80" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
              <line x1="0" y1="50" x2="280" y2="50" stroke="rgba(255,255,255,0.05)" strokeWidth="1" strokeDasharray="2 4" />
              <polyline
                points="0,20 35,22 70,28 105,40 140,55 175,68 210,82 245,92"
                fill="none"
                stroke="#38bdf8"
                strokeWidth="1.5"
              />
              <line x1="0" y1="70" x2="280" y2="70" stroke="rgba(255,255,255,0.2)" strokeWidth="1" strokeDasharray="3 3" />
              <text
                x="276"
                y="68"
                fill="#a3a3a3"
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

        <div className="border-t border-border bg-secondary/20 px-6 py-4">
          <p className="text-muted-foreground uppercase tracking-wider text-[10px] mb-2">rvectr diagnosis</p>
          <p className="text-foreground leading-relaxed font-sans text-xs">
            Scapular depression strength is the limiting factor — not pulling strength.
            Velocity collapse precedes form failure by ~1 rep, indicating central fatigue. Prescribed corrective: scapular pull-ups 3×8 prior to next pulling session.
          </p>
        </div>
      </div>

      {/* Session summary */}
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
    emerald: "text-emerald-400",
    amber: "text-amber-400",
    red: "text-red-400",
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
    { domain: "Kinematic", metric: "3D Body Surface Mesh (SMPL)", unit: "6,890 vertices", rate: "frame-by-frame" },
    { domain: "Kinematic", metric: "Bilateral asymmetry matrix", unit: "percent", rate: "per rep" },
    { domain: "Performance", metric: "Effective rep count", unit: "reps", rate: "per set" },
    { domain: "Performance", metric: "Velocity loss across set", unit: "percent", rate: "per set" },
    { domain: "Performance", metric: "Form degradation index", unit: "0–1", rate: "per rep" },
    { domain: "Periodisation", metric: "Weekly volume (sets)", unit: "sets/week", rate: "rolling 7d" },
    { domain: "Periodisation", metric: "Connective tissue exposure", unit: "weeks", rate: "per movement" },
  ];

  let lastDomain = "";
  return (
    <div className="border border-border font-mono text-xs">
      <div className="border-b border-border bg-secondary/30 grid grid-cols-12 px-4 py-2.5 text-[10px] uppercase tracking-wider text-muted-foreground">
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
              className="grid grid-cols-12 px-4 py-2.5 items-baseline border-b border-border/60 last:border-b-0"
            >
              <div className={`col-span-3 ${newDomain ? "text-foreground font-bold" : "text-muted-foreground/30"}`}>
                {newDomain ? r.domain : "·"}
              </div>
              <div className="col-span-5 text-foreground">{r.metric}</div>
              <div className="col-span-2 text-muted-foreground">{r.unit}</div>
              <div className="col-span-2 text-muted-foreground text-right">{r.rate}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
