import { ERROR_BUDGET, ERROR_BUDGET_BASELINE_MM, ERROR_BUDGET_MAX_MM } from "@/lib/results/errorBudget";
import { ChartFigure } from "./ChartFigure";

const W = 560;
const LEFT = 16;
const RIGHT = 56;
const TOP = 6;
const ROW_H = 50;
const BAR_H = 16;
const AXIS_H = 30;
const H = TOP + ERROR_BUDGET.length * ROW_H + AXIS_H;
const TICKS = [0, 2, 4, 6, 8];

const x = (mm: number) => LEFT + (mm / ERROR_BUDGET_MAX_MM) * (W - LEFT - RIGHT);
const fmt = (mm: number) => mm.toFixed(1);

const ARIA_LABEL =
  "Bar chart ranking how many extra millimetres each problem adds to the smallest catchable depth change. Slow drift in hip position adds the most, 7.4 millimetres. Phones one frame out of step and a board tilted 2 degrees add nothing measurable.";

export function ErrorRankingChart() {
  return (
    <ChartFigure
      caption={
        <>
          Extra millimetres added to the smallest catchable change (two phones, slow squat, starting from{" "}
          <span className="font-mono tabular-nums">{fmt(ERROR_BUDGET_BASELINE_MM)} mm</span>). Each problem is set to a
          realistic level, shown in grey.
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
              +{t}
              {t === ERROR_BUDGET_MAX_MM ? " mm" : ""}
            </text>
          </g>
        ))}
        {ERROR_BUDGET.map((source, i) => {
          const y0 = TOP + i * ROW_H;
          const width = Math.max(2, x(source.extraMm) - LEFT);
          return (
            <g key={source.label}>
              <text x={LEFT} y={y0 + 14} className="fill-foreground text-[14px]">
                {source.label}
                {source.level ? (
                  <tspan dx={8} className="fill-muted-foreground font-mono text-[12px]">
                    {source.level}
                  </tspan>
                ) : null}
              </text>
              <rect
                x={LEFT}
                y={y0 + 22}
                width={width}
                height={BAR_H}
                rx={2}
                className={i === 0 ? "fill-warm" : "fill-data"}
              />
              <text
                x={LEFT + width + 6}
                y={y0 + 22 + BAR_H - 3}
                className="fill-foreground font-mono text-[13px] tabular-nums"
              >
                +{fmt(source.extraMm)}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="sr-only">
        <table>
          <caption>
            Extra millimetres each problem adds to the smallest catchable depth change. Two phones, slow squat.
            Simulated.
          </caption>
          <thead>
            <tr>
              <th scope="col">Problem</th>
              <th scope="col">Level used</th>
              <th scope="col">Extra mm</th>
            </tr>
          </thead>
          <tbody>
            {ERROR_BUDGET.map((source) => (
              <tr key={source.label}>
                <th scope="row">{source.label}</th>
                <td>{source.level || "not applicable"}</td>
                <td>+{fmt(source.extraMm)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ChartFigure>
  );
}
