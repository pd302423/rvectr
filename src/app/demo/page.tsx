"use client";

import { Navbar } from "@/components/layout/Navbar";
import { MultiCamGrid } from "@/components/biomechanics/MultiCamGrid";
import { Cpu, Award, Zap, ShieldCheck } from "lucide-react";

export default function DemoPage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Banner */}
        <div className="p-6 rounded-xl border border-emerald-500/30 bg-emerald-500/5 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Award className="h-5 w-5 text-emerald-600" />
              <span className="text-xs font-mono uppercase tracking-wider text-emerald-700 dark:text-emerald-400 font-semibold">
                Science Exhibition Command Center
              </span>
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-foreground font-sans">
              Markerless 3-Camera 3D Motion Capture
            </h1>
            <p className="text-xs text-muted-foreground font-sans max-w-2xl">
              Synchronized 3-camera capture (Frontal 0°, Sagittal 90°, Diagonal 45°) resolving depth occlusion and camera distortion via 3D computer vision.
            </p>
          </div>

          <div className="flex items-center gap-2 font-mono text-xs text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20 w-fit">
            <Zap className="h-4 w-4" />
            <span>Audio-Clap Synced</span>
          </div>
        </div>

        {/* 3-Camera Grid Component */}
        <MultiCamGrid />

        {/* Pitch Notes */}
        <div className="p-6 rounded-xl border border-border bg-card space-y-3">
          <h3 className="text-sm font-semibold tracking-tight flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary" />
            <span>Science Exhibition Key Innovation Points</span>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-sans">
            <div className="p-3 rounded-lg bg-secondary/50 border border-border">
              <span className="font-semibold text-foreground">Solves Occlusion</span>
              <p className="mt-1 text-muted-foreground text-[11px]">
                When one camera angle is blocked by limbs, the remaining two views resolve the 3D joint coordinate.
              </p>
            </div>
            <div className="p-3 rounded-lg bg-secondary/50 border border-border">
              <span className="font-semibold text-foreground">Democratizes MoCap</span>
              <p className="mt-1 text-muted-foreground text-[11px]">
                Replaces $50,000+ laboratory camera arrays with 3 standard smartphone cameras and local GPU software.
              </p>
            </div>
            <div className="p-3 rounded-lg bg-secondary/50 border border-border">
              <span className="font-semibold text-foreground">Real-time Telemetry</span>
              <p className="mt-1 text-muted-foreground text-[11px]">
                Computes Knee Valgus inward drop, squat depth, and asymmetry index with instantaneous clinical feedback.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
