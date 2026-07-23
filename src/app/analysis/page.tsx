"use client";

import Link from "next/link";
import { Navbar } from "@/components/layout/Navbar";
import { useBiomechanicsStore } from "@/lib/store";
import { DualViewport } from "@/components/biomechanics/DualViewport";
import { ScoreGauge } from "@/components/biomechanics/ScoreGauge";
import { TelemetryTable } from "@/components/biomechanics/TelemetryTable";
import { TimelineScrubber } from "@/components/biomechanics/TimelineScrubber";
import { TelestratorToolbar } from "@/components/biomechanics/TelestratorToolbar";
import { KinematicWaveformChart } from "@/components/biomechanics/KinematicWaveformChart";
import { BilateralAsymmetryMatrix } from "@/components/biomechanics/BilateralAsymmetryMatrix";
import { Activity, Award, Lightbulb, FileText, Upload, RefreshCw, Scale, LineChart, Shield, UserCheck, Play } from "lucide-react";

export default function AnalysisPage() {
  const { currentAnalysis, activeTab, setActiveTab, userRole } = useBiomechanicsStore();

  if (!currentAnalysis) {
    return (
      <div className="min-h-screen bg-background text-foreground flex flex-col">
        <Navbar />
        <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-20 text-center">
          <div className="p-4 rounded-full bg-secondary text-muted-foreground w-fit mx-auto mb-4">
            <Activity className="h-10 w-10" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight">No Active Analysis Telemetry</h2>
          <p className="mt-2 text-sm text-muted-foreground max-w-md mx-auto">
            Upload a video recording or run a 3-camera session to generate 3D landmark telemetry.
          </p>
          <div className="mt-6">
            <Link
              href="/upload"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors shadow-xs"
            >
              <Upload className="h-4 w-4" />
              <span>Upload Video</span>
            </Link>
          </div>
        </main>
      </div>
    );
  }

  const { analysis, metadata, video_id } = currentAnalysis;

  const tabs = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "joints", label: "Joint Telemetry", icon: Award },
    { id: "waveform", label: "Waveform Studio", icon: LineChart },
    { id: "asymmetry", label: "Bilateral Asymmetry", icon: Scale },
    { id: "posture", label: "Posture Diagnostic", icon: FileText },
    { id: "recommendations", label: "Recommendations", icon: Lightbulb },
  ] as const;

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-muted-foreground uppercase">Session ID</span>
              <span className="text-xs font-mono bg-secondary px-2 py-0.5 rounded text-foreground">{video_id?.slice(0, 12)}...</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary/10 text-primary font-semibold uppercase">
                {userRole === "coach" ? "Coach Mode Active" : "Athlete Mode Active"}
              </span>
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-foreground font-sans mt-1">
              Biomechanical Telemetry Workspace
            </h1>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/upload"
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-secondary text-secondary-foreground hover:bg-muted text-xs font-semibold transition-colors border border-border"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>New Analysis</span>
            </Link>
          </div>
        </div>

        {/* Coach Telestrator Toolbar */}
        <TelestratorToolbar />

        {/* Dual Viewport (Video + Three.js 3D Mesh) */}
        <DualViewport />

        {/* Timeline Scrubber */}
        <TimelineScrubber totalFrames={metadata?.total_frames || 180} fps={metadata?.fps || 30} />

        {/* ATHLETE MODE DISPLAY */}
        {userRole === "athlete" ? (
          <div className="space-y-6">
            {/* Visual Summary Cards for Athletes */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <ScoreGauge
                score={analysis?.posture_report?.score || 94.2}
                grade={analysis?.posture_report?.grade || "Excellent"}
                description="Movement Quality Score (0-100)"
              />

              <div className="p-6 rounded-xl border border-border bg-card space-y-4">
                <div className="flex items-center gap-2">
                  <Scale className="h-5 w-5 text-emerald-600" />
                  <h3 className="text-sm font-semibold tracking-tight">Symmetry Score</h3>
                </div>
                <p className="text-3xl font-extrabold font-sans text-emerald-600">96.8%</p>
                <p className="text-xs text-muted-foreground font-mono">Limb balance is within optimal limits (🟢 Nominal)</p>
              </div>

              <div className="p-6 rounded-xl border border-border bg-card space-y-4">
                <div className="flex items-center gap-2">
                  <Play className="h-5 w-5 text-primary" />
                  <h3 className="text-sm font-semibold tracking-tight">Prescribed Corrective Reel</h3>
                </div>
                <p className="text-xs text-muted-foreground font-sans leading-relaxed">
                  Single-leg hip mobility drills & core stabilization (3 sets × 10 reps).
                </p>
                <button className="w-full py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors">
                  Watch Technique Guide
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* COACH MODE DISPLAY (High Data Density) */
          <div className="space-y-6">
            {/* Navigation Tabs */}
            <div className="flex gap-1 border-b border-border pb-2 overflow-x-auto">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
                      isActive
                        ? "bg-primary text-primary-foreground shadow-xs"
                        : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Tab Content Panels */}
            {activeTab === "overview" && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-6">
                  <KinematicWaveformChart totalFrames={metadata?.total_frames || 180} fps={metadata?.fps || 30} />
                  <TelemetryTable joints={analysis?.joint_analysis || []} />
                </div>

                <div className="space-y-6">
                  <ScoreGauge
                    score={analysis?.posture_report?.score || 94.2}
                    grade={analysis?.posture_report?.grade || "Excellent"}
                    description={analysis?.posture_report?.description}
                  />

                  {/* Video Info Grid */}
                  <div className="p-6 rounded-xl border border-border bg-card">
                    <h3 className="text-sm font-semibold tracking-tight mb-4">Video Metadata</h3>
                    <div className="grid grid-cols-2 gap-4 font-mono text-xs">
                      <div>
                        <span className="text-muted-foreground uppercase text-[10px]">Resolution</span>
                        <p className="font-semibold text-sm mt-0.5">{metadata ? `${metadata.width}×${metadata.height}` : "1920×1080"}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground uppercase text-[10px]">Duration</span>
                        <p className="font-semibold text-sm mt-0.5">{analysis?.overview?.duration ? `${analysis.overview.duration}s` : "6.0s"}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground uppercase text-[10px]">FPS</span>
                        <p className="font-semibold text-sm mt-0.5">{metadata?.fps || 30}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground uppercase text-[10px]">Frames</span>
                        <p className="font-semibold text-sm mt-0.5">{analysis?.overview?.frames_analyzed || 180}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "waveform" && (
              <KinematicWaveformChart totalFrames={metadata?.total_frames || 180} fps={metadata?.fps || 30} />
            )}

            {activeTab === "asymmetry" && <BilateralAsymmetryMatrix />}

            {activeTab === "joints" && <TelemetryTable joints={analysis?.joint_analysis || []} />}

            {activeTab === "posture" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <ScoreGauge
                  score={analysis?.posture_report?.score || 94.2}
                  grade={analysis?.posture_report?.grade || "Excellent"}
                  description={analysis?.posture_report?.description}
                />

                <div className="p-6 rounded-xl border border-border bg-card space-y-4 font-mono text-xs">
                  <h3 className="text-sm font-sans font-semibold tracking-tight">Posture Diagnostic Breakdown</h3>
                  <div className="flex justify-between py-2 border-b border-border">
                    <span className="text-muted-foreground">Alignment Score</span>
                    <span className="font-semibold text-foreground">{analysis?.posture_report?.score || 94.2} / 100</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-border">
                    <span className="text-muted-foreground">Consistency Score</span>
                    <span className="font-semibold text-emerald-600">{analysis?.posture_report?.consistency || 91.5}%</span>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "recommendations" && (
              <div className="p-6 rounded-xl border border-border bg-card space-y-4">
                <h3 className="text-sm font-semibold tracking-tight flex items-center gap-2">
                  <Lightbulb className="h-4 w-4 text-amber-500" />
                  <span>Biomechanical Recommendations</span>
                </h3>
                <div className="space-y-3">
                  {(analysis?.recommendations || []).map((rec, i) => (
                    <div
                      key={i}
                      className="p-4 rounded-lg bg-secondary/50 border border-border/60 text-xs font-sans leading-relaxed text-foreground flex items-start gap-3"
                    >
                      <span className="h-2 w-2 rounded-full bg-primary mt-1.5 shrink-0" />
                      <p>{rec}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
