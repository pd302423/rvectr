"use client";

import { ThreeMeshCanvas } from "./ThreeMeshCanvas";
import { Box } from "lucide-react";

export function DualViewport() {
  return (
    <div className="flex flex-col gap-3 font-mono">
      {/* Viewport Header Bar */}
      <div className="flex items-center justify-between px-1">
        <span className="text-xs uppercase tracking-widest font-bold text-[#ffffff] flex items-center gap-2">
          <Box className="h-4 w-4 text-[#ffffff]" />
          <span>Biomechanical Telemetry & 3D Surface Viewport</span>
        </span>
      </div>

      {/* Interactive 3D WebGL Surface Mesh Viewport */}
      <div className="w-full h-full">
        <ThreeMeshCanvas height="100%" />
      </div>
    </div>
  );
}
