"use client";

import { useBiomechanicsStore } from "@/lib/store";
import { Compass, Ruler, Pencil, Trash2, Camera, UserCheck, Shield } from "lucide-react";

export function TelestratorToolbar() {
  const { userRole, setUserRole, telestratorTool, setTelestratorTool } = useBiomechanicsStore();

  return (
    <div className="flex items-center justify-between p-2.5 rounded-xl border border-border bg-card shadow-xs">
      {/* Role Mode Switcher */}
      <div className="flex items-center gap-1 bg-secondary/80 p-1 rounded-lg border border-border">
        <button
          onClick={() => setUserRole("coach")}
          className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-mono transition-all ${
            userRole === "coach"
              ? "bg-primary text-primary-foreground shadow-xs font-semibold"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Shield className="h-3.5 w-3.5" />
          <span>Coach / Scientist Mode</span>
        </button>
        <button
          onClick={() => setUserRole("athlete")}
          className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-mono transition-all ${
            userRole === "athlete"
              ? "bg-primary text-primary-foreground shadow-xs font-semibold"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <UserCheck className="h-3.5 w-3.5" />
          <span>Athlete Mode</span>
        </button>
      </div>

      {/* Coach Telestrator Tools */}
      {userRole === "coach" && (
        <div className="flex items-center gap-1">
          <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground mr-2 hidden sm:inline">
            Telestrator Tools:
          </span>
          <button
            onClick={() => setTelestratorTool(telestratorTool === "protractor" ? "none" : "protractor")}
            className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-mono transition-all ${
              telestratorTool === "protractor"
                ? "bg-emerald-500 text-white font-semibold shadow-xs"
                : "bg-secondary text-secondary-foreground hover:bg-muted"
            }`}
            title="Measure 3-Point Joint Angle Protractor"
          >
            <Compass className="h-3.5 w-3.5" />
            <span className="hidden md:inline">Angle Protractor</span>
          </button>

          <button
            onClick={() => setTelestratorTool(telestratorTool === "ruler" ? "none" : "ruler")}
            className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-mono transition-all ${
              telestratorTool === "ruler"
                ? "bg-emerald-500 text-white font-semibold shadow-xs"
                : "bg-secondary text-secondary-foreground hover:bg-muted"
            }`}
            title="Measure Displacement Ruler in cm"
          >
            <Ruler className="h-3.5 w-3.5" />
            <span className="hidden md:inline">Distance Ruler</span>
          </button>

          <button
            onClick={() => setTelestratorTool(telestratorTool === "draw" ? "none" : "draw")}
            className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-mono transition-all ${
              telestratorTool === "draw"
                ? "bg-emerald-500 text-white font-semibold shadow-xs"
                : "bg-secondary text-secondary-foreground hover:bg-muted"
            }`}
            title="Freehand Vector Draw"
          >
            <Pencil className="h-3.5 w-3.5" />
            <span className="hidden md:inline">Vector Draw</span>
          </button>

          {telestratorTool !== "none" && (
            <button
              onClick={() => setTelestratorTool("none")}
              className="p-1.5 rounded bg-red-500/10 text-red-600 hover:bg-red-500/20 transition-colors ml-1"
              title="Clear Telestrator Overlay"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
