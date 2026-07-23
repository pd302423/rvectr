"use client";

import { useState } from "react";
import { ThreeMeshCanvas } from "./ThreeMeshCanvas";
import { Video, Box, Columns, Maximize2 } from "lucide-react";

interface DualViewportProps {
  videoUrl?: string;
  posterUrl?: string;
}

export function DualViewport({ videoUrl, posterUrl }: DualViewportProps) {
  const [viewMode, setViewMode] = useState<"dual" | "video" | "3d">("dual");

  return (
    <div className="flex flex-col gap-3">
      {/* View Mode Controls */}
      <div className="flex items-center justify-between px-2">
        <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
          Biomechanical Telemetry Viewport
        </span>
        <div className="flex items-center gap-1 bg-secondary/80 p-1 rounded-lg border border-border">
          <button
            onClick={() => setViewMode("dual")}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono transition-all ${
              viewMode === "dual"
                ? "bg-background text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Columns className="h-3.5 w-3.5" />
            <span>Dual View</span>
          </button>
          <button
            onClick={() => setViewMode("video")}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono transition-all ${
              viewMode === "video"
                ? "bg-background text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Video className="h-3.5 w-3.5" />
            <span>Video Only</span>
          </button>
          <button
            onClick={() => setViewMode("3d")}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono transition-all ${
              viewMode === "3d"
                ? "bg-background text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Box className="h-3.5 w-3.5" />
            <span>3D Mesh</span>
          </button>
        </div>
      </div>

      {/* Viewports Grid */}
      <div
        className={`grid gap-4 transition-all ${
          viewMode === "dual"
            ? "grid-cols-1 md:grid-cols-2"
            : "grid-cols-1"
        }`}
      >
        {/* Left Viewport: Original Video / Keypoint Overlay */}
        {(viewMode === "dual" || viewMode === "video") && (
          <div className="relative rounded-xl border border-border bg-black overflow-hidden aspect-video flex items-center justify-center group shadow-md">
            <div className="absolute top-3 left-3 z-10 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/70 border border-white/10 backdrop-blur-md text-xs font-mono text-white">
              <Video className="h-3.5 w-3.5 text-emerald-400" />
              <span>Original Video Feed</span>
            </div>

            {videoUrl ? (
              <video
                src={videoUrl}
                controls
                className="w-full h-full object-contain"
                poster={posterUrl}
              />
            ) : (
              <div className="flex flex-col items-center justify-center p-8 text-center text-zinc-500">
                <Video className="h-12 w-12 stroke-[1.5] mb-2 text-zinc-700" />
                <span className="text-xs font-mono">Video Stream Feed Placeholder</span>
                <span className="text-[10px] text-zinc-600 mt-1">Video playback synchronizes with 3D canvas</span>
              </div>
            )}
          </div>
        )}

        {/* Right Viewport: Three.js 3D WebGL Skeleton */}
        {(viewMode === "dual" || viewMode === "3d") && (
          <ThreeMeshCanvas height="100%" />
        )}
      </div>
    </div>
  );
}
