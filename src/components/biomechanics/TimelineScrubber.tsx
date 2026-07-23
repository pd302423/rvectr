"use client";

import { useBiomechanicsStore } from "@/lib/store";
import { Play, Pause, SkipBack, SkipForward, RotateCcw } from "lucide-react";
import { useEffect, useRef } from "react";

interface TimelineScrubberProps {
  totalFrames: number;
  fps?: number;
}

export function TimelineScrubber({ totalFrames, fps = 30 }: TimelineScrubberProps) {
  const { activeFrame, isPlaying, setActiveFrame, togglePlay, setPlaying } = useBiomechanicsStore();
  const animRef = useRef<number | null>(null);

  useEffect(() => {
    if (isPlaying) {
      const interval = setInterval(() => {
        useBiomechanicsStore.setState((state) => {
          if (state.activeFrame >= totalFrames - 1) {
            return { activeFrame: 0, isPlaying: false };
          }
          return { activeFrame: state.activeFrame + 1 };
        });
      }, 1000 / fps);

      return () => clearInterval(interval);
    }
  }, [isPlaying, totalFrames, fps]);

  const currentTime = (activeFrame / fps).toFixed(2);
  const totalTime = (totalFrames / fps).toFixed(2);
  const progressPercent = totalFrames > 0 ? (activeFrame / totalFrames) * 100 : 0;

  return (
    <div className="p-4 rounded-xl border border-border bg-card shadow-xs">
      <div className="flex items-center justify-between gap-4">
        {/* Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveFrame(0)}
            className="p-2 rounded-lg bg-secondary hover:bg-muted text-secondary-foreground transition-colors"
            title="Reset to frame 0"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
          <button
            onClick={() => setActiveFrame(Math.max(0, activeFrame - 1))}
            className="p-2 rounded-lg bg-secondary hover:bg-muted text-secondary-foreground transition-colors"
            title="Step Back 1 Frame"
          >
            <SkipBack className="h-4 w-4" />
          </button>
          <button
            onClick={togglePlay}
            className="p-2.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-xs"
            title={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 fill-current" />}
          </button>
          <button
            onClick={() => setActiveFrame(Math.min(totalFrames - 1, activeFrame + 1))}
            className="p-2 rounded-lg bg-secondary hover:bg-muted text-secondary-foreground transition-colors"
            title="Step Forward 1 Frame"
          >
            <SkipForward className="h-4 w-4" />
          </button>
        </div>

        {/* Scrubber Track */}
        <div className="flex-1 mx-4">
          <div className="flex justify-between items-center text-[10px] font-mono text-muted-foreground mb-1">
            <span>Frame {activeFrame} / {totalFrames}</span>
            <span>{currentTime}s / {totalTime}s</span>
          </div>
          <input
            type="range"
            min={0}
            max={Math.max(0, totalFrames - 1)}
            value={activeFrame}
            onChange={(e) => setActiveFrame(Number(e.target.value))}
            className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary focus:outline-none"
          />
        </div>

        {/* Telemetry info */}
        <div className="text-right font-mono text-xs">
          <span className="px-2 py-1 rounded bg-muted/60 text-muted-foreground">{fps} FPS</span>
        </div>
      </div>
    </div>
  );
}
