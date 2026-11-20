import { DROPOUTS } from "@/lib/results/errorBudget";
import { ChartFigure, ChartLegend } from "./ChartFigure";

const W = 560;
const H = 270;
const LEFT = 48;
const RIGHT = 36;
const TOP = 16;
const BOTTOM = 62;
const TICKS = [0, 25, 50, 75, 100];

const last = DROPOUTS.labels.length - 1;
const x = (i: number) => LEFT + (i * (W - LEFT - RIGHT)) / last;
const y = (percent: number) => TOP + (1 - percent / 100) * (H - TOP - BOTTOM);

const ARIA_LABEL =
  "Line chart: the share of squats judged unclear as missed hip detections become more frequent, for the old rule and the new rule. The old rule gives up on 6% of squats at 1 miss in 200 frames and 30% at 1 in 50. The new rule gives up on none up to 1 in 50 and on 14% at 1 in 33.";

const SERIES = [
  { id: "old", name: "Old rule", values: DROPOUTS.oldRule, stroke: "stroke-warm", fill: "fill-warm" },
  { id: "new", name: "New rule", values: DROPOUTS.newRule, stroke: "stroke-data", fill: "fill-data" },
] as const;

export function DropoutChart() {
  return (
    <ChartFigure
      legend={
        <ChartLegend
          items={[
            { swatch: "bg-warm", label: "Old rule" },
            { swatch: "bg-data", label: "New rule" },
          ]}
        />
      }
      caption={
        <>
          When the pose detector sometimes misses a hip, how many squats does the software refuse to judge? Missing
          points are never filled in, so a refusal is the honest answer. The old rule gave up on 6% of squats with only
          1 miss in 200 frames.
        </>
      }
    >
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ARIA_LABEL} className="block h-auto w-full">
        {TICKS.map((t) => (
          <g key={t}>
            <line x1={LEFT} x2={W - RIGHT} y1={y(t)} y2={y(t)} className="stroke-border" strokeWidth={1} />
            <text
              x={LEFT - 8}
              y={y(t) + 4}
              textAnchor="end"
              className="fill-muted-foreground font-mono text-[12px] tabular-nums"
            >
              {t}%
            </text>
          </g>
        ))}
        {DROPOUTS.labels.map((label, i) => (
          <text
            key={label}
            x={x(i)}
            y={H - BOTTOM + 20}
            textAnchor="middle"
            className="fill-muted-foreground font-mono text-[12px]"
          >
            {label}
          </text>
        ))}
        <text
          x={(LEFT + W - RIGHT) / 2}
          y={H - 8}
          textAnchor="middle"
          className="fill-muted-foreground font-mono text-[12px]"
        >
          how often a hip goes undetected (per phone, per frame)
        </text>
        {SERIES.map((series) => (
          <g key={series.id}>
            <polyline
              points={series.values.map((v, i) => `${x(i)},${y(v)}`).join(" ")}
              fill="none"
              strokeWidth={2.5}
              strokeLinejoin="round"
              className={series.stroke}
            />
            {series.values.map((v, i) => (
              <circle key={i} cx={x(i)} cy={y(v)} r={3.5} className={series.fill} />
            ))}
          </g>
        ))}
        <text
          x={x(1) - 6}
          y={y(DROPOUTS.oldRule[1]) - 8}
          textAnchor="end"
          className="fill-warm font-mono text-[13px] tabular-nums"
        >
          6%
        </text>
        <text
          x={x(3) - 8}
          y={y(DROPOUTS.oldRule[3]) - 6}
          textAnchor="end"
          className="fill-foreground font-mono text-[13px] tabular-nums"
        >
          30% vs 0%
        </text>
      </svg>
      <div className="sr-only">
        <table>
          <caption>Share of squats judged unclear, by how often a hip goes undetected. Simulated.</caption>
          <thead>
            <tr>
              <th scope="col">Hip undetected</th>
              <th scope="col">Old rule</th>
              <th scope="col">New rule</th>
            </tr>
          </thead>
          <tbody>
            {DROPOUTS.labels.map((label, i) => (
              <tr key={label}>
                <th scope="row">{label}</th>
                <td>{DROPOUTS.oldRule[i]}%</td>
                <td>{DROPOUTS.newRule[i]}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ChartFigure>
  );
}
