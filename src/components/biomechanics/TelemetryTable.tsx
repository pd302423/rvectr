"use client";

import { JointStatistic } from "@/lib/store";
import { Activity, CheckCircle2 } from "lucide-react";

interface TelemetryTableProps {
  jointData?: JointStatistic[];
  joints?: JointStatistic[];
}

export function TelemetryTable({ jointData, joints }: TelemetryTableProps) {
  const data = jointData || joints || [];

  if (!data || data.length === 0) {
    return (
      <div className="p-8 text-center text-[#a3a3a3] text-xs font-mono border border-dashed border-[#262626]">
        No joint kinematic telemetry available.
      </div>
    );
  }

  return (
    <div className="border border-[#262626] bg-[#0a0a0a] overflow-hidden font-mono">
      <div className="flex items-center justify-between p-4 border-b border-[#262626] bg-[#000000]">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-[#ffffff]" />
          <h3 className="text-xs font-bold uppercase tracking-widest text-[#ffffff]">Kinematic Joint Telemetry</h3>
        </div>
        <span className="text-[10px] text-[#a3a3a3]">{data.length} JOINTS TRACKED</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#121212] text-[#a3a3a3] text-[10px] uppercase tracking-widest border-b border-[#262626]">
            <tr>
              <th className="py-3 px-4 font-bold">Joint</th>
              <th className="py-3 px-4 font-bold text-right">Mean Angle</th>
              <th className="py-3 px-4 font-bold text-right">Range of Motion</th>
              <th className="py-3 px-4 font-bold text-right">Stability</th>
              <th className="py-3 px-4 font-bold text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#262626]">
            {data.map((item, idx) => {
              const formattedName = item.joint ? item.joint.replace(/_/g, " ") : `Joint ${idx + 1}`;
              return (
                <tr key={idx} className="hover:bg-[#121212] transition-colors">
                  <td className="py-3 px-4 font-bold text-[#ffffff] capitalize flex items-center gap-2">
                    <span className="h-1.5 w-1.5 bg-[#ffffff]" />
                    {formattedName}
                  </td>
                  <td className="py-3 px-4 text-right font-bold text-[#ffffff]">{item.mean_angle}°</td>
                  <td className="py-3 px-4 text-right text-[#a3a3a3]">{item.range_of_motion}°</td>
                  <td className="py-3 px-4 text-right text-[#ffffff] font-bold">
                    {item.stability}%
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 border border-[#262626] bg-[#000000] text-[#ffffff] text-[10px] font-bold uppercase">
                      <CheckCircle2 className="h-3 w-3 text-[#ffffff]" />
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
