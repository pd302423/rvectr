"use client";

import { useState } from "react";
import { CAMERA_CHART_MAX_MM, CAMERA_SETUPS, SCENARIOS, detectionDetails, type ScenarioKey } from "@/lib/results/errorBudget";
import { ChartFigure, ChartLegend } from "./ChartFigure";

// Chart geometry, in SVG units. The SVG scales with its container.
const W = 560;
const LEFT = 16;
const RIGHT = 56;
const TOP = 6;
const BAR = 14;
const BAR_GAP = 4;
const LABEL_H = 22;
const GROUP_GAP = 18;
const AXIS_H = 30;
const GROUP_H = LABEL_H + 2 * BAR + BAR_GAP + GROUP_GAP;
const H = TOP + CAMERA_SETUPS.length * GROUP_H + AXIS_H;
const TICKS = Array.from({ length: 5 }, (_, i) => (i * CAMERA_CHART_MAX_MM) / 4);

const x = (mm: number) => LEFT + (mm / CAMERA_CHART_MAX_MM) * (W - LEFT - RIGHT);
const fmt = (mm: number | null) => (mm === null ? "not reached" : mm.toFixed(1));

const ARIA_LABEL =
  "Bar chart: the smallest tested depth change that met both limits on the first half of the simulated sessions, for 1 phone from the side, 1 phone at an angle, 2 phones and 3 phones, at controlled and fast paces. Shorter bars are better.";

export function CameraCountChart() {
  const [key, setKey] = useState<ScenarioKey>("clean");
  const scenario = SCENARIOS.find((s) => s.key === key) ?? SCENARIOS[0];
  const details = detectionDetails(key);

  const controls = (
    <div className="grid gap-3">
      <div role="group" aria-label="How noisy the phones are" className="flex flex-wrap gap-2">
        {SCENARIOS.map((s) => (
          <button
            key={s.key}
            type="button"
            aria-pressed={s.key === key}
            onClick={() => setKey(s.key)}
            className="min-h-10 rounded-full border border-border px-4 text-sm transition-colors hover:bg-muted aria-pressed:border-foreground aria-pressed:bg-foreground aria-pressed:text-background"
          >
            {s.label}
          </button>
        ))}
      </div>
      <p aria-live="polite" className="max-w-[65ch] text-sm leading-relaxed text-muted-foreground sm:min-h-10">
        {scenario.note}
      </p>
    </div>
  );

  return (
    <ChartFigure
      controls={controls}
      legend={
        <ChartLegend
          items={[
            { swatch: "bg-data", label: "Controlled pace (2 s down, 2 s up)" },
            { swatch: "bg-data/55", label: "Fast pace (under 1 s down)" },
          ]}
        />
      }
      caption={
        <>
          Smallest tested depth change, in millimetres, that met both limits on the first half of the simulated
          sessions: at least 95% of shallow squats flagged and at most 5% of matching squats wrongly flagged. The chosen
          cutoff is then checked once on the other half. Squats the software calls unclear are still counted, as not
          caught. Values come from a fixed list of tested changes, so nothing is estimated in between. A shorter bar is
          better.
        </>
      }
    >
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ARIA_LABEL} className="block h-auto w-full">
        {TICKS.map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={TOP} y2={H - AXIS_H + 2} className="stroke-border" strokeWidth={1} />
            <text
              x={x(t)}
              y={H - 8}
              textAnchor="middle"
              className="fill-muted-foreground font-mono text-[12px] tabular-nums"
            >
              {t.toFixed(0)}
              {t === CAMERA_CHART_MAX_MM ? " mm" : ""}
            </text>
          </g>
        ))}
        {CAMERA_SETUPS.map((setup, i) => {
          const y0 = TOP + i * GROUP_H;
          const values = scenario.values[i];
          const bars = [
            { id: "controlled", mm: values.controlled, fill: "fill-data" },
            { id: "fast", mm: values.fast, fill: "fill-data/55" },
          ];
          return (
            <g key={setup.id}>
              <text x={LEFT} y={y0 + 14} className="fill-foreground text-[14px]">
                {setup.label}
              </text>
              {bars.map((bar, p) => {
                const y = y0 + LABEL_H + p * (BAR + BAR_GAP);
                return (
                  <g key={bar.id}>
                    <rect
                      x={LEFT}
                      y={y}
                      width={Math.max(1, x(bar.mm ?? CAMERA_CHART_MAX_MM) - LEFT)}
                      height={BAR}
                      rx={2}
                      className={bar.fill}
                    />
                    <text
                      x={x(bar.mm ?? CAMERA_CHART_MAX_MM) + 6}
                      y={y + BAR - 2.5}
                      className="fill-foreground font-mono text-[13px] tabular-nums"
                    >
                      {fmt(bar.mm)}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>
      <div className="sr-only">
        <table>
          <caption>Smallest catchable depth change in millimetres, {scenario.label.toLowerCase()}. Simulated.</caption>
          <thead>
            <tr>
              <th scope="col">Setup</th>
              <th scope="col">Controlled pace</th>
              <th scope="col">Fast pace</th>
            </tr>
          </thead>
          <tbody>
            {CAMERA_SETUPS.map((setup, i) => (
              <tr key={setup.id}>
                <th scope="row">{setup.label}</th>
                <td>{fmt(scenario.values[i].controlled)}</td>
                <td>{fmt(scenario.values[i].fast)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <details className="mt-4 rounded-md border border-border px-4 py-3 text-sm">
        <summary className="cursor-pointer font-medium">First-half result and second-half check, with counts</summary>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[40rem] text-left text-xs">
            <thead className="text-muted-foreground">
              <tr>
                <th className="py-2 pr-3">Setup</th>
                <th className="py-2 pr-3">Pace</th>
                <th className="py-2 pr-3">Tested changes: last that missed, first that passed (first half)</th>
                <th className="py-2 pr-3">Matching squats wrongly flagged (second half)</th>
                <th className="py-2 pr-3">Shallow squats flagged (second half)</th>
                <th className="py-2">Second-half result</th>
              </tr>
            </thead>
            <tbody>
              {details.map((row) => (
                <tr key={`${row.mode}-${row.pace}`} className="border-t border-border">
                  <th scope="row" className="py-2 pr-3 font-normal">{row.mode}</th>
                  <td className="py-2 pr-3">{row.pace}</td>
                  <td className="py-2 pr-3 font-mono">{row.trainingGridMm === null ? "not reached" : `${row.lowerTestedMm}–${row.trainingGridMm} mm`}</td>
                  <td className="py-2 pr-3 font-mono">{row.heldoutFalseAlarms.false_alarms}/{row.heldoutFalseAlarms.matching_total}</td>
                  <td className="py-2 pr-3 font-mono">{row.heldoutDetection.detected_shallow}/{row.heldoutDetection.shallow_total}</td>
                  <td className="py-2">{row.heldoutPass ? "passed: meets both limits" : "did not pass: misses at least one limit"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
          The smallest passing change is chosen using the first half of the sessions. This table shows the single check
          on the other half. It does not look for another value if that check fails.
        </p>
      </details>
    </ChartFigure>
  );
}
