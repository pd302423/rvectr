import { CheckCircle2, TriangleAlert } from "lucide-react";
import { HEADLINE_NUMBERS } from "@/lib/results/errorBudget";
import { cn } from "@/lib/utils";

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
      <ul
        aria-label="Smallest depth change caught in the simulation, by camera count, with the result of the check on new simulated sessions (simulated)"
        className="grid gap-4 sm:grid-cols-3"
      >
        {HEADLINE_NUMBERS.map((stat) => {
          const passed = stat.heldout.pass;
          const CheckIcon = passed ? CheckCircle2 : TriangleAlert;
          return (
            <li key={stat.phones} className="grid content-start gap-3 rounded-xl border border-border bg-card p-5">
              <span className="flex items-center justify-between gap-3 font-mono text-xs uppercase tracking-[0.12em] text-muted-foreground">
                {stat.phones} {stat.phones === 1 ? "phone" : "phones"}
                <span className="rounded-full border border-warm/50 px-2 py-0.5 text-[10px] tracking-[0.1em] text-warm">
                  Simulated
                </span>
              </span>
              <span className="font-mono text-4xl tabular-nums text-data">
                {stat.mm === null ? "not reached" : `${stat.mm.toFixed(1)} mm`}
              </span>
              <span className="text-sm leading-relaxed text-muted-foreground">
                {stat.label}.{" "}
                {stat.mm === null
                  ? "No tested depth change met both limits on the first half of the simulated sessions (lower random noise, controlled pace)."
                  : "Smallest tested depth change that met both limits on the first half of the simulated sessions (lower random noise, controlled pace)."}
              </span>
              <span
                className={cn(
                  "flex items-start gap-2 rounded-lg border px-3 py-2 text-sm font-semibold leading-snug",
                  passed ? "border-data/40 bg-data/5 text-data" : "border-warm/50 bg-warm/10 text-warm",
                )}
              >
                <CheckIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
                <span>{passed ? "Passed on new simulated sessions" : "Did not pass on new simulated sessions"}</span>
              </span>
              <span className="text-xs leading-relaxed text-muted-foreground">
                Check on the other half of the sessions: {stat.heldout.falseAlarms} of {stat.heldout.falseAlarmTotal}{" "}
                matching squats wrongly flagged; {stat.heldout.shallowDetected} of {stat.heldout.shallowTotal} shallow
                squats flagged.
              </span>
            </li>
          );
        })}
      </ul>
      {variant === "home" ? (
        <p className="max-w-[65ch] text-sm leading-relaxed text-muted-foreground">
          The two limits are: flag at least 95% of the shallow squats, and wrongly flag at most 5% of the matching
          squats. The simulation picks its cutoff using half of the computer-made sessions, then checks it once on the
          other half. These are results from a computer model, not measurements from real cameras. Squats the software
          cannot judge (&ldquo;unclear&rdquo;) are still counted, as not caught.
        </p>
      ) : null}
    </div>
  );
}
