import { HEADLINE_NUMBERS } from "@/lib/results/errorBudget";

interface HeadlineStatsProps {
  /**
   * "results" = each card explains itself (wording from the results page).
   * "home" = short cards; a shared note under them gives the conditions.
   */
  variant?: "results" | "home";
}

/** The three headline numbers. Simulated, never measured. */
export function HeadlineStats({ variant = "results" }: HeadlineStatsProps) {
  return (
    <div className="grid gap-4">
      <ul aria-label="First passing training-grid result by camera count, with held-out counts (simulated)" className="grid gap-4 sm:grid-cols-3">
        {HEADLINE_NUMBERS.map((stat) => (
          <li key={stat.phones} className="grid content-start gap-2 rounded-xl border border-border bg-card p-5">
            <span className="flex items-center justify-between gap-3 font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">
              {stat.phones} {stat.phones === 1 ? "phone" : "phones"}
              <span className="rounded-full border border-warm/50 px-2 py-0.5 text-[10px] tracking-[0.1em] text-warm">
                Simulated
              </span>
            </span>
            <span className="font-mono text-4xl tabular-nums text-data">
              {stat.mm === null ? "not reached on tested grid" : `${stat.mm.toFixed(1)} mm`}
            </span>
            <span className="text-sm leading-relaxed text-muted-foreground">
              {stat.label}. First passing tested training-grid value for the lower-noise, controlled-pace setting.
            </span>
            <span className="text-xs leading-relaxed text-muted-foreground">
              Held out: {stat.heldout.falseAlarms}/{stat.heldout.falseAlarmTotal} matching flagged; {stat.heldout.shallowDetected}/{stat.heldout.shallowTotal} shallow flagged; {stat.heldout.pass ? "pass" : "fail"}.
            </span>
          </li>
        ))}
      </ul>
      {variant === "home" ? (
        <p className="max-w-[65ch] text-sm leading-relaxed text-muted-foreground">
          The cutoff is chosen from training sessions then evaluated once on held-out sessions. These are model results,
          not real-camera measurements. Unclear attempts stay in the denominators and count as not detected.
        </p>
      ) : null}
    </div>
  );
}
