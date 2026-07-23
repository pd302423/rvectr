"use client";

import Link from "next/link";
import { Navbar } from "@/components/layout/Navbar";
import { StatCard } from "@/components/ui/StatCard";
import { Activity, Target, Film, Bone, Upload, Cpu, ArrowRight } from "lucide-react";

export default function DashboardPage() {
  const stats = [
    { label: "Total Analyses", value: "12", icon: Activity, subtext: "Lifetime session records" },
    { label: "Avg Posture Score", value: "92.4", icon: Target, subtext: "Excellent alignment grade", status: "nominal" as const },
    { label: "Videos Processed", value: "18", icon: Film, subtext: "3D mesh extracted" },
    { label: "Joints Tracked", value: "33", icon: Bone, subtext: "MediaPipe pose landmarks" },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-foreground font-sans">
              Athlete Dashboard
            </h1>
            <p className="mt-1 text-sm text-muted-foreground font-sans">
              Overview of your biomechanical telemetry and movement records.
            </p>
          </div>

          <Link
            href="/upload"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors shadow-xs w-fit"
          >
            <Upload className="h-4 w-4" />
            <span>New Video Analysis</span>
          </Link>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          {stats.map((stat, idx) => (
            <StatCard
              key={idx}
              label={stat.label}
              value={stat.value}
              icon={stat.icon}
              subtext={stat.subtext}
              status={stat.status}
            />
          ))}
        </div>

        {/* Action Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
          <Link
            href="/upload"
            className="p-6 rounded-xl border border-border bg-card hover:border-primary/50 transition-all group flex flex-col justify-between"
          >
            <div>
              <div className="p-3 rounded-lg bg-secondary text-primary w-fit mb-4 group-hover:scale-105 transition-transform">
                <Upload className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-card-foreground">Upload Movement Video</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Upload 2D video files to compute 3D landmark coordinates, joint angle series, and report metrics.
              </p>
            </div>
            <div className="mt-6 flex items-center gap-2 text-xs font-semibold text-primary">
              <span>Start Upload</span>
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </div>
          </Link>

          <Link
            href="/demo"
            className="p-6 rounded-xl border border-border bg-card hover:border-emerald-500/50 transition-all group flex flex-col justify-between"
          >
            <div>
              <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-600 w-fit mb-4 group-hover:scale-105 transition-transform">
                <Cpu className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-card-foreground">3-Camera Science Command Center</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Stream 3 synchronized camera angles (Frontal 0°, Sagittal 90°, Diagonal 45°) for Science Exhibition demos.
              </p>
            </div>
            <div className="mt-6 flex items-center gap-2 text-xs font-semibold text-emerald-600">
              <span>Open Command Center</span>
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </div>
          </Link>
        </div>
      </main>
    </div>
  );
}
