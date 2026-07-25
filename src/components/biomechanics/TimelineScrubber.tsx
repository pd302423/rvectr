"use client";

import { useBiomechanicsStore } from "@/lib/store";
import { Play, Pause, SkipBack, SkipForward, RotateCcw } from "lucide-react";
import { useEffect } from "react";

interface TimelineScrubberProps {
  totalFrames: number;
  fps?: number;
}

export function TimelineScrubber({ totalFrames, fps = 30 }: TimelineScrubberProps) {
  const { activeFrame, isPlaying, setActiveFrame, togglePlay } = useBiomechanicsStore();

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

  return (
    <div className="p-3 border border-[#262626] bg-[#0a0a0a] text-[#ffffff] font-mono">
      <div className="flex items-center justify-between gap-4">
        {/* Playback Controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveFrame(0)}
            className="p-2 border border-[#262626] bg-[#000000] text-[#ffffff] hover:bg-[#ffffff] hover:text-[#000000] transition-colors"
            title="Reset to frame 0"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setActiveFrame(Math.max(0, activeFrame - 1))}
            className="p-2 border border-[#262626] bg-[#000000] text-[#ffffff] hover:bg-[#ffffff] hover:text-[#000000] transition-colors"
            title="Previous Frame"
          >
            <SkipBack className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={togglePlay}
            className="p-2 border border-[#ffffff] bg-[#ffffff] text-[#000000] hover:bg-[#a3a3a3] transition-colors font-bold"
            title={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5 fill-current" />}
          </button>
          <button
            onClick={() => setActiveFrame(Math.min(totalFrames - 1, activeFrame + 1))}
            className="p-2 border border-[#262626] bg-[#000000] text-[#ffffff] hover:bg-[#ffffff] hover:text-[#000000] transition-colors"
            title="Next Frame"
          >
            <SkipForward className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Timeline Slider Track */}
        <div className="flex-1 mx-4">
          <div className="flex justify-between items-center text-[10px] text-[#a3a3a3] mb-1 font-mono uppercase">
            <span>Frame {activeFrame + 1} / {totalFrames}</span>
            <span>{currentTime}s / {totalTime}s</span>
          </div>
          <input
            type="range"
            min={0}
            max={Math.max(0, totalFrames - 1)}
            value={activeFrame}
            onChange={(e) => setActiveFrame(Number(e.target.value))}
            className="w-full h-1 bg-[#262626] appearance-none cursor-pointer accent-[#ffffff]"
          />
        </div>

        {/* FPS Indicator */}
        <div className="text-right text-[10px] font-mono text-[#ffffff] border border-[#262626] px-2.5 py-1 bg-[#000000]">
          <span>{fps} FPS</span>
        </div>
      </div>
    </div>
  );
}
