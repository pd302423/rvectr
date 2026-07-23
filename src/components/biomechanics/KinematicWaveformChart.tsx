"use client";

import { useBiomechanicsStore } from "@/lib/store";
import { LineChart, Activity, Zap, Shield } from "lucide-react";
import { useRef, useCallback } from "react";

interface KinematicWaveformChartProps {
  totalFrames?: number;
  fps?: number;
}

export function KinematicWaveformChart({ totalFrames = 180, fps = 30 }: KinematicWaveformChartProps) {
  const { activeFrame, setActiveFrame } = useBiomechanicsStore();
  const containerRef = useRef<HTMLDivElement>(null);

  const handlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
      const targetFrame = Math.round((x / rect.width) * (totalFrames - 1));
      setActiveFrame(targetFrame);
    },
    [totalFrames, setActiveFrame]
  );

  // Generate synthetic sine/cosine kinematic wave curves for demonstration
  const points = Array.from({ length: totalFrames }, (_, i) => {
    const angle = 90 + Math.sin(i / 15) * 35;
    const velocity = Math.cos(i / 15) * 120;
    const force = 1200 + Math.sin((i - 20) / 15) * 600;
    return { frame: i, angle, velocity, force };
  });

  const cursorXPercent = totalFrames > 0 ? (activeFrame / (totalFrames - 1)) * 100 : 0;
  const currentPt = points[activeFrame] || points[0];

  return (
    <div className="p-5 rounded-xl border border-border bg-card shadow-xs space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold tracking-tight">Kinematic Waveform Studio</h3>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono">
          <span className="flex items-center gap-1 text-sky-500">
            <span className="h-2 w-2 rounded-full bg-sky-500" /> Angle ({currentPt.angle.toFixed(1)}°)
          </span>
          <span className="flex items-center gap-1 text-indigo-500">
            <span className="h-2 w-2 rounded-full bg-indigo-500" /> Velocity ({currentPt.velocity.toFixed(0)}°/s)
          </span>
          <span className="flex items-center gap-1 text-emerald-500">
            <span className="h-2 w-2 rounded-full bg-emerald-500" /> Force ({currentPt.force.toFixed(0)}N)
          </span>
        </div>
      </div>

      {/* Synchronized Interactive SVG Chart Area */}
      <div
        ref={containerRef}
        onPointerDown={handlePointerDown}
        className="relative h-44 w-full cursor-crosshair bg-slate-950/80 rounded-lg border border-slate-800 overflow-hidden select-none"
      >
        <svg className="h-full w-full" preserveAspectRatio="none" viewBox={`0 0 ${totalFrames} 100`}>
          {/* Grid lines */}
          <line x1="0" y1="25" x2={totalFrames} y2="25" stroke="#1e293b" strokeDasharray="3 3" />
          <line x1="0" y1="50" x2={totalFrames} y2="50" stroke="#1e293b" strokeDasharray="3 3" />
          <line x1="0" y1="75" x2={totalFrames} y2="75" stroke="#1e293b" strokeDasharray="3 3" />

          {/* Trace 1: Knee Angle Curve (Sky blue) */}
          <path
            d={points
              .map((p, i) => `${i === 0 ? "M" : "L"} ${p.frame} ${100 - (p.angle / 180) * 100}`)
              .join(" ")}
            fill="none"
            stroke="#38bdf8"
            strokeWidth="1.8"
          />

          {/* Trace 2: Angular Velocity Curve (Indigo) */}
          <path
            d={points
              .map((p, i) => `${i === 0 ? "M" : "L"} ${p.frame} ${50 - (p.velocity / 300) * 50}`)
              .join(" ")}
            fill="none"
            stroke="#818cf8"
            strokeWidth="1.5"
            strokeDasharray="2 2"
          />

          {/* Trace 3: Ground Reaction Force (Emerald) */}
          <path
            d={points
              .map((p, i) => `${i === 0 ? "M" : "L"} ${p.frame} ${100 - (p.force / 2400) * 80}`)
              .join(" ")}
            fill="none"
            stroke="#10b981"
            strokeWidth="1.5"
          />
        </svg>

        {/* Synchronized Cursor Line */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-red-500 shadow-md transition-all duration-75 pointer-events-none"
          style={{ left: `${cursorXPercent}%` }}
        >
          <div className="absolute -top-1 -left-2.5 px-1.5 py-0.5 rounded bg-red-600 text-white font-mono text-[9px] font-bold">
            F{activeFrame}
          </div>
        </div>
      </div>

      <div className="flex justify-between items-center text-[10px] font-mono text-muted-foreground">
        <span>0.00s (Frame 0)</span>
        <span>Click or drag on waveform to scrub video & 3D mesh frame-by-frame</span>
        <span>{(totalFrames / fps).toFixed(2)}s (Frame {totalFrames})</span>
      </div>
    </div>
  );
}
