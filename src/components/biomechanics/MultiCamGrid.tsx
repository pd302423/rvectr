"use client";

import { useState } from "react";
import { ThreeMeshCanvas } from "./ThreeMeshCanvas";
import { Camera, Volume2, Cpu, CheckCircle } from "lucide-react";

export function MultiCamGrid() {
  const [synced, setSynced] = useState(true);

  const cameras = [
    {
      id: "frontal",
      title: "CAMERA 1: FRONTAL (0°)",
      description: "Frontal Plane — Knee Valgus & Hip Tilt",
      status: "NOMINAL",
      metrics: "Knee Valgus: 4.2° (PASS)",
    },
    {
      id: "sagittal",
      title: "CAMERA 2: SAGITTAL (90°)",
      description: "Sagittal Plane — Depth & Spinal Flexion",
      status: "NOMINAL",
      metrics: "Max Depth: 82° Flexion (PASS)",
    },
    {
      id: "diagonal",
      title: "CAMERA 3: DIAGONAL (45°)",
      description: "Depth & Occlusion Resolution",
      status: "NOMINAL",
      metrics: "Torso Lean: 22.1°",
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      {/* Sync Status Banner - Monochromatic Black & White */}
      <div className="flex items-center justify-between p-4 border border-[#262626] bg-[#0a0a0a] text-[#ffffff]">
        <div className="flex items-center gap-3">
          <div className="p-2 border border-[#262626] bg-[#000000] text-[#ffffff]">
            <Volume2 className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2 font-bold text-xs font-mono tracking-widest uppercase">
              <CheckCircle className="h-4 w-4 text-[#ffffff]" />
              <span>Audio-Clap Sync Engine Active</span>
            </div>
            <p className="text-xs font-mono text-[#a3a3a3] mt-0.5">
              3 Cameras Synced at Clap Peak (+0.00ms Offset) • Frame-Exact Triangulation
            </p>
          </div>
        </div>
        <button
          onClick={() => setSynced(!synced)}
          className="px-3 py-1 border border-[#ffffff] bg-[#ffffff] text-[#000000] hover:bg-[#a3a3a3] text-xs font-mono font-bold uppercase tracking-widest transition-colors"
        >
          Re-Sync Feeds
        </button>
      </div>

      {/* 4-Panel Grid (3 Camera Angles + 1 3D Mesh Visualizer) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {cameras.map((cam) => (
          <div
            key={cam.id}
            className="relative border border-[#262626] bg-[#000000] aspect-video flex flex-col justify-between p-3"
          >
            {/* Header */}
            <div className="flex items-center justify-between z-10 font-mono">
              <div className="flex items-center gap-2 px-2.5 py-1 bg-[#0a0a0a] border border-[#262626] text-xs text-[#ffffff]">
                <Camera className="h-3.5 w-3.5 text-[#ffffff]" />
                <span>{cam.title}</span>
              </div>
              <span className="text-[10px] px-2 py-0.5 border border-[#262626] bg-[#000000] text-[#ffffff] font-bold">
                {cam.status}
              </span>
            </div>

            {/* Center Video Placeholder graphic */}
            <div className="flex flex-col items-center justify-center my-auto text-[#525252] text-center">
              <div className="h-12 w-12 border border-dashed border-[#333333] flex items-center justify-center mb-2">
                <Cpu className="h-6 w-6 text-[#737373]" />
              </div>
              <span className="text-xs font-mono text-[#a3a3a3]">{cam.description}</span>
            </div>

            {/* Telemetry Overlay Footer */}
            <div className="z-10 px-3 py-2 bg-[#0a0a0a] border border-[#262626] text-xs font-mono text-[#ffffff] flex items-center justify-between">
              <span>{cam.metrics}</span>
              <span className="text-[10px] text-[#737373]">60 FPS</span>
            </div>
          </div>
        ))}

        {/* 4th Viewport: Interactive 3D SMPL Mesh */}
        <div className="flex flex-col">
          <ThreeMeshCanvas height="100%" />
        </div>
      </div>
    </div>
  );
}
