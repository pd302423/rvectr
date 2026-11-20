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
  ANGLED_PHONE_BIAS_MM,
  NOISE_DEFINITIONS,
  NOT_SHOWN_YET,
  OLD_VS_NEW,
  PAUSE_CASES,
  SIMULATION_SETUP,
  SOURCE_RUN,
  formatValue,
  type TextPart,
} from "@/lib/results/errorBudget";

export const metadata: Metadata = {
  title: "Results",
  description:
    "Simulated results for the Rvectr squat-depth software: how much a second and third phone help, what the biggest sources of error are, and what the software does with pauses and missing data. Simulation only, not measurements.",
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
        <PageHeader eyebrow="Results · simulation only" title="What the new squat software can measure">
          <p>
            Results of the work done 15&ndash;18 November 2026: the two-phone squat-depth software, the error
            simulation, the better depth reading and the one-phone comparison.
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
          In the simulation, <strong className="font-semibold">yes, but the gain shrinks</strong>. Going from one phone
          to two helps more than going from two to three. A faster squat always makes the job harder.
        </p>
        <HeadlineStats variant="results" />
        <CameraCountChart />
        <p className="max-w-[65ch] leading-relaxed">
          One trap showed up:{" "}
          <strong className="font-semibold">
            a single phone placed at an angle reads every squat about {ANGLED_PHONE_BIAS_MM} mm too shallow
          </strong>
          , because the hips move towards it and get bigger in the picture. Comparing squats against each other still
          works, but the absolute depth is off. Two phones fix this, because they measure real 3D positions.
        </p>
      </section>

      <section aria-labelledby="estimator" className="grid gap-6">
        <SectionHeading id="estimator" eyebrow="Change: better depth reading">
          The old rule exaggerated depth; the new one doesn&apos;t
        </SectionHeading>
        <p className="max-w-[65ch] leading-relaxed">
          The old software took the single highest standing point and the single lowest point. Shaky points pushed both
          outward, so every squat looked deeper than it was. The new software takes the middle value of the standing
          period and fits a smooth curve through the bottom of the squat.
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

      <section aria-labelledby="budget" className="grid gap-6">
        <SectionHeading id="budget" eyebrow="Error budget">
          Slow drift is the biggest risk, not phone timing
        </SectionHeading>
        <p className="max-w-[65ch] leading-relaxed">
          The simulation switched on one problem at a time and measured how much worse the result got. Slow wobble in
          the detected hip position matters most. Phones being slightly out of step, the board being slightly tilted,
          or the phones being close together barely matter, because depth is an up-and-down distance and the hips are
          almost still at the bottom of a squat.
        </p>
        <ErrorRankingChart />
        <p className="max-w-[65ch] leading-relaxed">
          One more honesty check: with slow drift, the error bar the software prints for each squat is{" "}
          <strong className="font-semibold">2 to 3 times too small</strong>. Without drift it is right. So the real
          recordings must be checked against known stool heights, not against the software&apos;s own error bars.
        </p>
      </section>

      <section aria-labelledby="pauses" className="grid gap-6">
        <SectionHeading id="pauses" eyebrow="Change: pauses and edge cases">
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
        <p>{NOISE_DEFINITIONS}</p>
      </div>
    </Container>
  );
}
