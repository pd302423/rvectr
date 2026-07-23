"use client";

import { useState } from "react";
import { ThreeMeshCanvas } from "./ThreeMeshCanvas";
import { Camera, Volume2, ShieldAlert, Cpu, CheckCircle } from "lucide-react";

export function MultiCamGrid() {
  const [synced, setSynced] = useState(true);

  const cameras = [
    {
      id: "frontal",
      title: "CAMERA 1: FRONTAL (0°)",
      description: "Frontal Plane — Knee Valgus & Hip Tilt",
      status: "Nominal",
      metrics: "Knee Valgus: 4.2° (PASS)",
      color: "emerald",
    },
    {
      id: "sagittal",
      title: "CAMERA 2: SAGITTAL (90°)",
      description: "Sagittal Plane — Depth & Spinal Flexion",
      status: "Nominal",
      metrics: "Max Depth: 82° Flexion (PASS)",
      color: "blue",
    },
    {
      id: "diagonal",
      title: "CAMERA 3: DIAGONAL (45°)",
      description: "Depth & Occlusion Resolution",
      status: "Nominal",
      metrics: "Torso Lean: 22.1°",
      color: "indigo",
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      {/* Sync Status Banner */}
      <div className="flex items-center justify-between p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/5 text-emerald-950 dark:text-emerald-300">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-600">
            <Volume2 className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 font-semibold text-sm">
              <CheckCircle className="h-4 w-4 text-emerald-500" />
              <span>Audio-Clap Audio Synchronization Active</span>
            </div>
            <p className="text-xs font-mono text-emerald-700 dark:text-emerald-400 mt-0.5">
              3 Cameras Synced at Clap Peak (+0.00ms Offset) • Frame-Exact Triangulation
            </p>
          </div>
        </div>
        <button
          onClick={() => setSynced(!synced)}
          className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 text-xs font-mono transition-colors"
        >
          Re-Sync Clap Peak
        </button>
      </div>

      {/* 4-Panel Grid (3 Camera Angles + 1 3D Mesh Visualizer) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {cameras.map((cam) => (
          <div
            key={cam.id}
            className="relative rounded-xl border border-border bg-slate-950 overflow-hidden aspect-video flex flex-col justify-between p-3 group shadow-md"
          >
            {/* Header */}
            <div className="flex items-center justify-between z-10">
              <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-slate-900/80 border border-slate-700/60 backdrop-blur-md text-xs font-mono text-slate-200">
                <Camera className="h-3.5 w-3.5 text-sky-400" />
                <span>{cam.title}</span>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                {cam.status}
              </span>
            </div>

            {/* Center Video Placeholder graphic */}
            <div className="flex flex-col items-center justify-center my-auto text-slate-600 text-center">
              <div className="h-12 w-12 rounded-full border border-dashed border-slate-700 flex items-center justify-center mb-2">
                <Cpu className="h-6 w-6 text-slate-500" />
              </div>
              <span className="text-xs font-mono text-slate-400">{cam.description}</span>
            </div>

            {/* Telemetry Overlay Footer */}
            <div className="z-10 px-3 py-2 rounded bg-slate-900/90 border border-slate-800 text-xs font-mono text-slate-300 flex items-center justify-between">
              <span>{cam.metrics}</span>
              <span className="text-[10px] text-slate-500">60 FPS</span>
            </div>
          </div>
        ))}

        {/* 4th Viewport: Interactive 3D Skeleton Mesh */}
        <div className="flex flex-col">
          <ThreeMeshCanvas height="100%" />
        </div>
      </div>
    </div>
  );
}
