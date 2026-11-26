import type { FrameAnalysisData } from "@/lib/store";

export function BilateralAsymmetryMatrix({ frames }: { frames: FrameAnalysisData[] }) {
  const rows = ["hip", "knee"].map((joint) => {
    const pairs = frames.map(({ joint_angles }) => [
      joint_angles[`left_${joint}`]?.angle, joint_angles[`right_${joint}`]?.angle,
    ]).filter(([l, r]) => Number.isFinite(l) && Number.isFinite(r));
    const mean = (side: number) => pairs.reduce((sum, pair) => sum + pair[side], 0) / pairs.length;
    return { joint, samples: pairs.length, left: mean(0), right: mean(1) };
  });
  return (
    <section className="space-y-4 rounded-xl border border-border bg-card p-6">
      <h3 className="font-bold">Left and right angles</h3>
      <p className="text-sm text-muted-foreground">Mean across paired frames in the displayed series.</p>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead><tr><th>Joint</th><th>Frames</th><th>Left (°)</th><th>Right (°)</th></tr></thead>
          <tbody>{rows.map(({ joint, samples, left, right }) => (
            <tr key={joint} className="border-t border-border">
              <th className="py-3 text-left capitalize">{joint}</th><td>{samples}</td>
              <td>{samples ? left.toFixed(1) : "Unknown"}</td><td>{samples ? right.toFixed(1) : "Unknown"}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </section>
  );
}
