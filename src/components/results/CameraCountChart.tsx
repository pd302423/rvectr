"use client";

import { useState } from "react";
import { CAMERA_CHART_MAX_MM, CAMERA_SETUPS, SCENARIOS, type ScenarioKey } from "@/lib/results/errorBudget";
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
const TICKS = [0, 5, 10, 15, 20];

const x = (mm: number) => LEFT + (mm / CAMERA_CHART_MAX_MM) * (W - LEFT - RIGHT);
const fmt = (mm: number) => mm.toFixed(1);

const ARIA_LABEL =
  "Bar chart: the smallest change in squat depth that 1 phone from the side, 1 phone at an angle, 2 phones and 3 phones can catch, at a controlled and at a fast pace. Shorter bars are better.";

export function CameraCountChart() {
  const [key, setKey] = useState<ScenarioKey>("clean");
  const scenario = SCENARIOS.find((s) => s.key === key) ?? SCENARIOS[0];

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
          Smallest difference in squat depth the setup can catch, in millimetres. Shorter bar = better.
          &quot;Catch&quot; means it flags at least 95 out of 100 truly shallower squats while wrongly flagging at most
          5 out of 100 normal ones.
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
              {t}
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
                      width={Math.max(1, x(bar.mm) - LEFT)}
                      height={BAR}
                      rx={2}
                      className={bar.fill}
                    />
                    <text
                      x={x(bar.mm) + 6}
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
    </ChartFigure>
  );
}
