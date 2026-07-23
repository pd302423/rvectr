"use client";

import { JointStatistic } from "@/lib/store";
import { Activity, AlertTriangle, CheckCircle2 } from "lucide-react";

interface TelemetryTableProps {
  joints: JointStatistic[];
}

export function TelemetryTable({ joints }: TelemetryTableProps) {
  if (!joints || joints.length === 0) {
    return (
      <div className="p-8 text-center text-muted-foreground text-sm font-mono border border-dashed rounded-xl">
        No joint kinematic telemetry available. Upload a video to process frames.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-border bg-muted/20">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold tracking-tight">Kinematic Joint Telemetry</h3>
        </div>
        <span className="text-xs font-mono text-muted-foreground">{joints.length} Joints Tracked</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-sans">
          <thead className="bg-muted/40 text-muted-foreground font-mono uppercase text-[10px] tracking-wider border-b border-border">
            <tr>
              <th className="py-3 px-4 font-semibold">Joint</th>
              <th className="py-3 px-4 font-semibold text-right">Mean Angle</th>
              <th className="py-3 px-4 font-semibold text-right">Range of Motion</th>
              <th className="py-3 px-4 font-semibold text-right">Stability</th>
              <th className="py-3 px-4 font-semibold text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {joints.map((item, idx) => {
              const formattedName = item.joint ? item.joint.replace(/_/g, " ") : `Joint ${idx + 1}`;
              return (
                <tr key={idx} className="hover:bg-muted/30 transition-colors">
                  <td className="py-3 px-4 font-medium capitalize flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                    {formattedName}
                  </td>
                  <td className="py-3 px-4 text-right font-mono font-semibold">{item.mean_angle}°</td>
                  <td className="py-3 px-4 text-right font-mono text-muted-foreground">{item.range_of_motion}°</td>
                  <td className="py-3 px-4 text-right font-mono">
                    <span className={item.stability >= 80 ? "text-emerald-600 font-semibold" : "text-amber-600"}>
                      {item.stability}%
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase ${
                        item.status === "normal"
                          ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20"
                          : item.status === "unstable"
                          ? "bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20"
                          : "bg-red-500/10 text-red-700 dark:text-red-400 border border-red-500/20"
                      }`}
                    >
                      {item.status === "normal" ? (
                        <CheckCircle2 className="h-3 w-3" />
                      ) : (
                        <AlertTriangle className="h-3 w-3" />
                      )}
                      {item.status}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
