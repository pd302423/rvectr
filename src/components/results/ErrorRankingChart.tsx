import { ERROR_BUDGET, ERROR_BUDGET_BASELINE_MM, ERROR_BUDGET_MAX_MM } from "@/lib/results/errorBudget";
import { ChartFigure } from "./ChartFigure";

const W = 620;
const LEFT = 16;
const RIGHT = 58;
const TOP = 6;
const ROW_H = 54;
const BAR_H = 15;
const AXIS_H = 34;
const H = TOP + ERROR_BUDGET.length * ROW_H + AXIS_H;
const TICKS = Array.from({ length: 5 }, (_, i) => (i * ERROR_BUDGET_MAX_MM) / 4);
const x = (mm: number) => LEFT + (mm / ERROR_BUDGET_MAX_MM) * (W - LEFT - RIGHT);
const fmt = (mm: number | null) => mm === null ? "not reached" : `${mm.toFixed(1)} mm`;

export function ErrorRankingChart() {
  return (
    <ChartFigure
      caption={
        <>
          Smallest tested depth change that met both limits on the first half of the simulated sessions, for two cameras
          at controlled pace. The baseline is {" "}
          <span className="font-mono tabular-nums">{fmt(ERROR_BUDGET_BASELINE_MM)}</span>. Each row then reports,
          for the other half of the sessions, how many matching squats were wrongly flagged, how many shallow squats were
          flagged, and whether the locked cutoff passed both limits.
        </>
      }
    >
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Smallest passing depth change on the first half of the sessions, and the check on the other half, for each assumed error in the two-camera case." className="block h-auto w-full">
        {TICKS.map((tick) => (
          <g key={tick}>
            <line x1={x(tick)} x2={x(tick)} y1={TOP} y2={H - AXIS_H + 2} className="stroke-border" strokeWidth={1} />
            <text x={x(tick)} y={H - 8} textAnchor="middle" className="fill-muted-foreground font-mono text-[12px] tabular-nums">
              {tick.toFixed(0)}{tick === ERROR_BUDGET_MAX_MM ? " mm" : ""}
            </text>
          </g>
        ))}
        {ERROR_BUDGET.map((row, i) => {
          const y = TOP + i * ROW_H;
          const width = row.trainingMddMm === null ? 0 : Math.max(2, x(row.trainingMddMm) - LEFT);
          return (
            <g key={row.label}>
              <text x={LEFT} y={y + 14} className="fill-foreground text-[13px]">{row.label}</text>
              {row.trainingMddMm === null ? (
                <text x={LEFT} y={y + 35} className="fill-muted-foreground text-[12px]">No tested depth change passed</text>
              ) : (
                <>
                  <rect x={LEFT} y={y + 22} width={width} height={BAR_H} rx={2} className="fill-data" />
                  <text x={LEFT + width + 6} y={y + 34} className="fill-foreground font-mono text-[12px] tabular-nums">{fmt(row.trainingMddMm)}</text>
                </>
              )}
              <text x={LEFT} y={y + 50} className="fill-muted-foreground text-[11px]">
                Other half: {row.falseAlarms}/{row.falseAlarmTotal} matching wrongly flagged; {row.detectedShallow}/{row.shallowTotal} shallow flagged; {row.heldoutPass ? "passed" : "did not pass"}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="sr-only">
        <table>
          <caption>Smallest passing depth change on the first half of the sessions, and the locked check on the other half. Simulation only.</caption>
          <thead><tr><th scope="col">Assumed error</th><th scope="col">Smallest passing depth change (first half)</th><th scope="col">Matching squats wrongly flagged (other half)</th><th scope="col">Shallow squats flagged (other half)</th><th scope="col">Result on the other half</th></tr></thead>
          <tbody>{ERROR_BUDGET.map((row) => <tr key={row.label}>
            <th scope="row">{row.label}</th><td>{fmt(row.trainingMddMm)}</td>
            <td>{row.falseAlarms}/{row.falseAlarmTotal}</td><td>{row.detectedShallow}/{row.shallowTotal}</td>
            <td>{row.heldoutPass ? "passed" : "did not pass"}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </ChartFigure>
  );
}
