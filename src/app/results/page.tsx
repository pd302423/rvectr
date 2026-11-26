import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { CameraCountChart } from "@/components/results/CameraCountChart";
import { DropoutChart } from "@/components/results/DropoutChart";
import { ErrorRankingChart } from "@/components/results/ErrorRankingChart";
import { HeadlineStats } from "@/components/results/HeadlineStats";
import { Container } from "@/components/site/Container";
import { Notice } from "@/components/site/Notice";
import { PageHeader } from "@/components/site/PageHeader";
import { SectionHeading } from "@/components/site/SectionHeading";
import {
  DEFAULT_TOLERANCE_CM,
  FIXED_RULE_CURVE,
  NOISE_DEFINITIONS,
  NOT_SHOWN_YET,
  OLD_VS_NEW,
  PAUSE_CASES,
  SIMULATION_SETUP,
  SIMULATION_INFO,
  SOURCE_RUN,
  TARGETED_3MM,
  formatValue,
  type TextPart,
} from "@/lib/results/errorBudget";

export const metadata: Metadata = {
  title: "Results",
  description:
    "Simulation results for the Rvectr squat-depth software: camera-count comparisons, modeled error settings, and the effects of pauses and missing data. These are predictions, not measurements.",
};

function renderParts(parts: readonly TextPart[]) {
  return parts.map((part, i) => {
    if (typeof part === "string") return part;
    return part.style === "num" ? (
      <span key={i} className="font-mono tabular-nums">
        {part.text}
      </span>
    ) : (
      <strong key={i} className="font-semibold text-foreground">
        {part.text}
      </strong>
    );
  });
}

const TH = "py-2 pr-4 text-left text-xs font-medium text-muted-foreground";
const TD = "border-t border-border py-3 pr-4 align-top";
const TD_NUM = `${TD} whitespace-nowrap font-mono tabular-nums`;

export default function ResultsPage() {
  return (
    <Container size="reading" className="grid gap-16 py-12 sm:py-16">
      <div className="grid gap-6">
        <PageHeader eyebrow="Results · simulation only" title="What the simulation predicts about squat-depth measurement">
          <p>
            Simulated squat-depth results, comparisons between camera setups, and checks of the depth-reading rules.
          </p>
        </PageHeader>
        <Notice title="These are predictions from a computer simulation, not measurements.">
          <p>No real two-phone footage exists yet. The pilot recording will test whether these numbers hold.</p>
        </Notice>
      </div>

      <section aria-labelledby="question" className="grid gap-6">
        <SectionHeading id="question" eyebrow="Research question">
          Do more cameras catch smaller changes in squat depth?
        </SectionHeading>
        <p className="max-w-[65ch] text-lg leading-relaxed">
          In this model, the estimates depend on camera count and movement speed. The result varies with the assumed
          noise and camera geometry, and needs a real recording before it can answer whether more phones help in practice.
        </p>
        <HeadlineStats variant="results" />
        <CameraCountChart />
        <p className="max-w-[65ch] leading-relaxed">
          A single camera cannot recover distance along its viewing direction from one image alone. In this simulation,
          the one-camera comparison uses image scale measured at the standing distance throughout the movement. The
          front-oblique camera sees the pelvis move away from it as the person moves backward while squatting, so the
          fixed standing-distance scale underestimates depth in this layout. The direction and size depend on camera
          placement and motion. Two or three views add depth information, while calibration and timing errors can still
          affect the result.
        </p>
        <p className="max-w-[65ch] leading-relaxed text-muted-foreground">
          The chart reports a cutoff selected from tested grid values on training sessions and checked on separate
          held-out sessions. The table below shows a different result: the pipeline&apos;s fixed {DEFAULT_TOLERANCE_CM} cm
          rule applied directly to the simulation. It was not trained or evaluated as a held-out cutoff.
        </p>
      </section>

      <section aria-labelledby="estimator" className="grid gap-6">
        <SectionHeading id="estimator" eyebrow="Depth estimator comparison">
          Two rules for estimating squat depth
        </SectionHeading>
        <p className="max-w-[65ch] leading-relaxed">
          The old rule used the highest standing point and lowest bottom point. The newer rule uses the median standing
          height and fits a curve around the bottom. In the simulated cases shown here, the older rule tended to read
          deeper; these results do not establish performance on real footage.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Old rule against new rule. Two phones, slow squat. Simulated.</caption>
            <thead>
              <tr>
                <th scope="col" className={TH}>
                  Two phones, slow squat
                </th>
                <th scope="col" className={TH}>
                  Old rule
                </th>
                <th scope="col" className={TH}>
                  New rule
                </th>
              </tr>
            </thead>
            <tbody>
              {OLD_VS_NEW.map((row) => (
                <tr key={row.measure}>
                  <th scope="row" className={`${TD} font-normal`}>
                    {row.measure}
                  </th>
                  <td className={`${TD_NUM} text-warm`}>{formatValue(row.oldRule, row.kind)}</td>
                  <td className={`${TD_NUM} text-data`}>{formatValue(row.newRule, row.kind)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <DropoutChart />
      </section>

      <section aria-labelledby="fixed-rule" className="grid gap-6">
        <SectionHeading id="fixed-rule" eyebrow="Fixed pipeline rule">
          What the 3 cm rule flags in this simulation
        </SectionHeading>
        <p className="max-w-[65ch] leading-relaxed">
          These values come from the versioned simulation summary for standard noise and controlled pace. Each cell
          lists flagged, unclear and missed shares, in that order. The fixed {DEFAULT_TOLERANCE_CM} cm rule is applied
          directly; these values are separate from the training-grid cutoff and its held-out check.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[48rem] text-sm">
            <caption className="sr-only">Fixed pipeline rule results from simulation, with flagged, unclear and missed shares for two phones and one front-oblique phone.</caption>
            <thead>
              <tr>
                <th scope="col" className={TH}>True depth difference</th>
                <th scope="col" className={TH}>2 phones flagged / unclear / missed</th>
                <th scope="col" className={TH}>1 front-oblique phone flagged / unclear / missed</th>
              </tr>
            </thead>
            <tbody>
              {FIXED_RULE_CURVE.map((row) => {
                const percent = (value: number | null) => value == null ? "unknown" : `${value.toFixed(1)}%`;
                return (
                  <tr key={row.differenceCm}>
                    <th scope="row" className={`${TD} font-normal`}>{row.differenceCm} cm</th>
                    <td className={TD_NUM}>{percent(row.twoCameraFlaggedPercent)} / {percent(row.twoCameraUnclearPercent)} / {percent(row.twoCameraMissedPercent)}</td>
                    <td className={TD_NUM}>{percent(row.angledFlaggedPercent)} / {percent(row.angledUnclearPercent)} / {percent(row.angledMissedPercent)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="budget" className="grid gap-6">
        <SectionHeading id="budget" eyebrow="Error budget">
          How modeled error settings changed the cutoff
        </SectionHeading>
        <p className="max-w-[65ch] leading-relaxed">
          These one-at-a-time runs compare specific assumed error sizes. Independent slow drift in the camera hip
          detections changed the selected cutoff in this model. That does not estimate the real frequency or size of such drift.
          Other camera-specific calibration errors, motion-dependent detector noise and shared missing-frame bursts are
          included in separate sensitivity cases. None has yet been measured from real phones.
        </p>
        <ErrorRankingChart />
        <p className="max-w-[65ch] leading-relaxed">
          In the simulated slow-drift case, the software&apos;s per-squat error bar was smaller than the across-session
          spread. That check uses a model with independent frame noise in its error-bar formula and correlated drift
          added to the observations. Real recordings must be compared with measured targets; the model&apos;s error bars
          are not validated.
        </p>
      </section>

      <section aria-labelledby="pauses" className="grid gap-6">
        <SectionHeading id="pauses" eyebrow="Pauses and edge cases">
          Resting at the bottom, or stopping the video too early
        </SectionHeading>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">What the software does in four edge cases. Simulated.</caption>
            <thead>
              <tr>
                <th scope="col" className={TH}>
                  Situation
                </th>
                <th scope="col" className={TH}>
                  What the software does
                </th>
              </tr>
            </thead>
            <tbody>
              {PAUSE_CASES.map((row) => (
                <tr key={row.situation}>
                  <th scope="row" className={`${TD} font-normal`}>
                    {row.situation}
                  </th>
                  <td className={TD}>{renderParts(row.outcome)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="not-yet" className="grid gap-6">
        <SectionHeading id="not-yet" eyebrow="What this does not show yet">
          The pilot decides whether these numbers are real
        </SectionHeading>
        <ul className="grid max-w-[65ch] list-disc gap-2 pl-5 leading-relaxed marker:text-warm">
          {NOT_SHOWN_YET.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p>
          <Link
            href="/"
            className="inline-flex min-h-10 items-center gap-2 text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            Back to the project overview
            <ArrowRight aria-hidden="true" className="size-4" />
          </Link>
        </p>
      </section>

      <div className="grid gap-2 border-t border-border pt-6 text-xs leading-relaxed text-muted-foreground">
        <p>
          Source: simulation run <span className="font-mono">{SOURCE_RUN}</span>, {SIMULATION_SETUP}
        </p>
        <p>
          Seed {SIMULATION_INFO.seed}; {SIMULATION_INFO.sessions_per_condition} sessions per condition; tested depth
          grid {SIMULATION_INFO.settings.reference_grid_cm.join(", ")} cm; source revision {SIMULATION_INFO.code_version}
          {SIMULATION_INFO.source_dirty ? " (working tree contained local edits; file hashes below identify the simulation code)" : ""}.
        </p>
        <p>
          Targeted 3 mm held-out check: threshold {TARGETED_3MM.threshold_mm.toFixed(2)} mm; matching false alarms{" "}
          {TARGETED_3MM.heldout_matching_counts.false_alarms}/{TARGETED_3MM.heldout_matching_counts.matching_total}; shallow attempts
          detected {TARGETED_3MM.heldout_shallow_counts.detected_shallow}/{TARGETED_3MM.heldout_shallow_counts.shallow_total};{" "}
          {TARGETED_3MM.passes_on_heldout_sessions ? "met" : "did not meet"} the two limits on held-out sessions.
          Bootstrap intervals across whole sessions: false alarms {Math.round(TARGETED_3MM.heldout_matching_false_alarm_rate_95ci[0] * 100)}–
          {Math.round(TARGETED_3MM.heldout_matching_false_alarm_rate_95ci[1] * 100)}%; shallow detected {Math.round(TARGETED_3MM.heldout_shallow_detection_rate_95ci[0] * 100)}–
          {Math.round(TARGETED_3MM.heldout_shallow_detection_rate_95ci[1] * 100)}%.
        </p>
        <details>
          <summary className="cursor-pointer">Simulation code hashes and units</summary>
          <ul className="mt-2 grid gap-1 pl-4 font-mono">
            {Object.entries({ ...SIMULATION_INFO.source_sha256, ...SIMULATION_INFO.supporting_source_sha256 }).map(([path, hash]) => (
              <li key={path}>
                {path}: {hash}
              </li>
            ))}
          </ul>
          <p className="mt-2">Depth is computed in metres; charts report millimetres and centimetres. Camera timing is in frames; camera angles are in degrees.</p>
          <p className="mt-2">Baseline geometry: {SIMULATION_INFO.settings.baseline_camera_geometry}. Main comparison at 60 fps; 30 fps is the frame-rate sensitivity.</p>
          <p className="mt-2">Squat pipeline defaults used by the simulation:</p>
          <pre className="mt-1 overflow-x-auto rounded bg-muted p-2">{JSON.stringify(SIMULATION_INFO.settings.pipeline_defaults_squat, null, 2)}</pre>
          <p className="mt-2">Frozen dependency lock SHA-256: {SIMULATION_INFO.dependency_lock_sha256}</p>
          <p className="mt-2">Simulation runtime: Python {SIMULATION_INFO.runtime.python}, NumPy {SIMULATION_INFO.runtime.numpy}, SciPy {SIMULATION_INFO.runtime.scipy}.</p>
        </details>
        <p>{NOISE_DEFINITIONS}</p>
      </div>
    </Container>
  );
}
