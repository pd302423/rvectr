/**
 * Top-down sketch: two phones look at the same hip from different angles.
 * The two lines of sight cross at the hip. That crossing is its 3D position.
 * A drawing of the idea, not data.
 */

const HIP = { x: 180, y: 92 };
const PHONES = [
  { id: "A", x: 66, y: 214 },
  { id: "B", x: 294, y: 214 },
] as const;

function angleToHip(from: { x: number; y: number }) {
  return (Math.atan2(HIP.y - from.y, HIP.x - from.x) * 180) / Math.PI;
}

export function TriangulationDiagram() {
  return (
    <svg
      viewBox="0 0 360 250"
      role="img"
      aria-label="Top-down drawing. Phone A and phone B stand apart and both look at the same hip. The line of sight from each phone is drawn as a dashed line. The two lines cross at the hip, which gives its 3D position."
      className="block h-auto w-full"
    >
      <circle cx={HIP.x} cy={HIP.y} r={40} fill="none" strokeWidth={1} strokeDasharray="2 5" className="stroke-border" />
      {PHONES.map((phone) => (
        <g key={phone.id}>
          <line
            x1={phone.x}
            y1={phone.y}
            x2={HIP.x}
            y2={HIP.y}
            strokeWidth={1.5}
            strokeDasharray="6 5"
            className="stroke-data"
          />
          <g transform={`translate(${phone.x} ${phone.y}) rotate(${angleToHip(phone)})`}>
            <rect x={-16} y={-8} width={32} height={16} rx={2} className="fill-card stroke-foreground" strokeWidth={1.5} />
            <circle cx={9} cy={0} r={3.5} className="fill-foreground" />
          </g>
          <text
            x={phone.x}
            y={phone.y + 28}
            textAnchor="middle"
            className="fill-muted-foreground font-mono text-[12px] uppercase tracking-widest"
          >
            Phone {phone.id}
          </text>
        </g>
      ))}
      <circle cx={HIP.x} cy={HIP.y} r={9} className="fill-data/25" />
      <circle cx={HIP.x} cy={HIP.y} r={4.5} className="fill-data" />
      <text x={HIP.x} y={HIP.y - 52} textAnchor="middle" className="fill-foreground font-mono text-[12px] uppercase tracking-widest">
        Hip
      </text>
    </svg>
  );
}
