"use client";

import { Navbar } from "@/components/layout/Navbar";
import { ThreeMeshCanvas } from "@/components/biomechanics/ThreeMeshCanvas";
import { MultiCamGrid } from "@/components/biomechanics/MultiCamGrid";
import { Cpu, Award, Zap, ShieldCheck, Box, Activity, Camera, Sliders, CheckCircle2, AlertTriangle } from "lucide-react";

export default function DemoPage() {
  return (
    <div className="min-h-screen bg-[#000000] text-[#ffffff] font-sans flex flex-col selection:bg-[#ffffff] selection:text-[#000000]">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 space-y-8">

        {/*
          Provenance banner. The mesh rendered on this page is a hand-authored
          animation, not capture output — see backend/README.md. An earlier
          version of this page credited it to a real capture backend by name (ci-allow) and
          claimed sub-centimetre accuracy (ci-allow). Do not reintroduce either; CI fails
          the build if those patterns come back.
        */}
        <div className="p-4 border border-[#ffffff] bg-[#0a0a0a] flex items-start gap-3 font-mono">
          <AlertTriangle className="h-4 w-4 text-[#ffffff] mt-0.5 shrink-0" />
          <div className="space-y-1">
            <div className="text-xs font-bold uppercase tracking-widest text-[#ffffff]">
              Synthetic asset — not a measurement
            </div>
            <p className="text-[11px] text-[#a3a3a3] leading-relaxed max-w-3xl">
              The 3D mesh below is a hand-authored squat animation generated from
              scripted joint angles. It is <span className="text-[#ffffff]">not</span> the
              output of multi-view triangulation, and bears no relationship to the
              camera footage beyond its frame count. Multi-view SMPL fitting is
              specified but <span className="text-[#ffffff]">not implemented</span>. No
              accuracy claim on this page has been validated against any reference
              standard.
            </p>
          </div>
        </div>

        {/* Banner - Monochromatic Professional Header */}
        <div className="p-6 border border-[#262626] bg-[#0a0a0a] flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1 font-mono">
            <div className="flex items-center gap-2">
              <Award className="h-4 w-4 text-[#ffffff]" />
              <span className="text-xs uppercase tracking-widest text-[#a3a3a3] font-bold">
                Markerless Motion Capture & Biomechanics Research Prototype
              </span>
            </div>
            <h1 className="text-xl font-bold tracking-widest text-[#ffffff] uppercase font-sans mt-1">
              Multi-View 3D Motion Capture & Parametric SMPL/SMPL-X Surface Reconstruction
            </h1>
            <p className="text-xs text-[#a3a3a3] font-mono max-w-3xl leading-relaxed mt-1">
              A research pipeline intended to turn multi-view smartphone video into
              6,890-vertex SMPL/SMPL-X surface meshes and kinematic telemetry. The
              stages below are marked with what is built and what is not.
            </p>
          </div>

          <div className="flex items-center gap-2 font-mono text-xs text-[#ffffff] bg-[#000000] px-3 py-2 border border-[#262626] w-fit">
            <Zap className="h-4 w-4" />
            <span>Dual-Cam Audio-Clap Synced</span>
          </div>
        </div>

        {/* ──────── INTERACTIVE 3D MESH VIEWPORT SHOWCASE ──────── */}
        <section className="space-y-4 font-mono">
          <div className="flex items-center justify-between border-b border-[#262626] pb-2">
            <div className="flex items-center gap-2">
              <Box className="h-4 w-4 text-[#ffffff]" />
              <h2 className="text-sm font-bold tracking-widest uppercase text-[#ffffff]">
                Interactive 3D WebGL Studio Mesh Output
              </h2>
            </div>
            <span className="text-xs text-[#a3a3a3]">
              Synthetic asset: <code className="text-[#ffffff] bg-[#121212] px-2 py-0.5 border border-[#262626]">public/squat_3d_mesh.glb</code>
            </span>
          </div>

          {/* Interactive 3D WebGL Canvas Component */}
          <ThreeMeshCanvas height="540px" glbUrl="/squat_3d_mesh.glb" />
        </section>

        {/* ──────── PROJECT SCOPE & SYSTEM ARCHITECTURE ──────── */}
        <section className="space-y-4 font-mono">
          <div className="flex items-center gap-2 border-b border-[#262626] pb-2">
            <Cpu className="h-4 w-4 text-[#ffffff]" />
            <h2 className="text-sm font-bold tracking-widest uppercase text-[#ffffff]">
              Project Scope & Technical Architecture
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* Scope 1 */}
            <div className="p-5 border border-[#262626] bg-[#0a0a0a] space-y-2">
              <div className="flex items-center gap-2 text-[#ffffff] font-bold text-xs uppercase tracking-widest">
                <Camera className="h-4 w-4 text-[#ffffff]" />
                <span>1. Multi-View Camera Calibration</span>
                <span className="ml-auto text-[10px] text-[#ffffff] border border-[#262626] px-1.5 py-0.5">BUILT</span>
              </div>
              <p className="text-xs text-[#a3a3a3] leading-relaxed">
                Uses synchronized video feeds (<span className="text-[#ffffff]">CE 3</span> + <span className="text-[#ffffff]">Nord</span>) with OpenCV chessboard calibration. Computes lens intrinsic matrices <code className="text-[#ffffff]">K_01, K_02</code> and extrinsic rotation/translation parameters <code className="text-[#ffffff]">[R|T]</code>, then extracts per-frame 2D keypoints from both views.
              </p>
            </div>

            {/* Scope 2 */}
            <div className="p-5 border border-[#262626] bg-[#0a0a0a] space-y-2">
              <div className="flex items-center gap-2 text-[#ffffff] font-bold text-xs uppercase tracking-widest">
                <Box className="h-4 w-4 text-[#ffffff]" />
                <span>2. SMPL/SMPL-X Parametric Fitting</span>
                <span className="ml-auto text-[10px] text-[#ffffff] border border-[#ffffff] px-1.5 py-0.5">NOT BUILT</span>
              </div>
              <p className="text-xs text-[#a3a3a3] leading-relaxed">
                Intended to triangulate the stage-1 keypoints and fit 72-parameter axis-angle joint rotations onto the 6,890-vertex SMPL body model. <span className="text-[#ffffff]">This stage does not exist.</span> The current script discards the stage-1 keypoints and substitutes a scripted animation, so every mesh downstream is authored rather than recovered.
              </p>
            </div>

            {/* Scope 3 */}
            <div className="p-5 border border-[#262626] bg-[#0a0a0a] space-y-2">
              <div className="flex items-center gap-2 text-[#ffffff] font-bold text-xs uppercase tracking-widest">
                <Sliders className="h-4 w-4 text-[#ffffff]" />
                <span>3. Temporal Trajectory Smoothing</span>
                <span className="ml-auto text-[10px] text-[#ffffff] border border-[#262626] px-1.5 py-0.5">BUILT</span>
              </div>
              <p className="text-xs text-[#a3a3a3] leading-relaxed">
                Applies a Savitzky–Golay filter across per-vertex trajectories over the 291-frame sequence to suppress frame-to-frame jitter. Smoothing attenuates the high-frequency content of the signal, so it also biases peak angular velocity downward — the quantity this project intends to study.
              </p>
            </div>

            {/* Scope 4 */}
            <div className="p-5 border border-[#262626] bg-[#0a0a0a] space-y-2">
              <div className="flex items-center gap-2 text-[#ffffff] font-bold text-xs uppercase tracking-widest">
                <Activity className="h-4 w-4 text-[#ffffff]" />
                <span>4. Biomechanical Form Telemetry</span>
                <span className="ml-auto text-[10px] text-[#ffffff] border border-[#262626] px-1.5 py-0.5">BUILT</span>
              </div>
              <p className="text-xs text-[#a3a3a3] leading-relaxed">
                Calculates frame-by-frame joint kinematics from a mesh sequence: knee flexion, hip hinge, spinal lean, knee valgus gap and angular velocity. Runs on whatever meshes it is given — it has never been validated against a reference standard, so no accuracy figure is quoted here.
              </p>
            </div>

          </div>
        </section>

        {/* ──────── MULTI-CAM GRID SECTION ──────── */}
        <section className="space-y-4 font-mono">
          <div className="flex items-center justify-between border-b border-[#262626] pb-2">
            <h3 className="text-xs font-bold tracking-widest uppercase text-[#ffffff]">
              Synchronized Multi-View Optical Camera Feeds
            </h3>
            <span className="text-xs text-[#a3a3a3]">CE 3 (Cam 01) & Nord (Cam 02)</span>
          </div>

          {/* 3-Camera Grid Component */}
          <MultiCamGrid />
        </section>

        {/* Innovation Key Highlights */}
        <div className="p-6 border border-[#262626] bg-[#0a0a0a] space-y-3 font-mono">
          <h3 className="text-xs font-bold uppercase tracking-widest flex items-center gap-2 text-[#ffffff]">
            <ShieldCheck className="h-4 w-4 text-[#ffffff]" />
            <span>Design Goals</span>
          </h3>
          <p className="text-[11px] text-[#a3a3a3] leading-relaxed">
            What the pipeline is aiming at. Two of the three are intent, not
            results — labelled accordingly.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-3 border border-[#262626] bg-[#000000]">
              <span className="font-bold text-[#ffffff] flex items-center gap-1.5 uppercase">
                <AlertTriangle className="h-3.5 w-3.5 text-[#ffffff]" /> Limb Occlusion — Goal
              </span>
              <p className="mt-1 text-[#a3a3a3] text-[11px] leading-relaxed">
                Multi-view triangulation should recover joints that a single occluded view cannot. Requires stage 2, which is not built, so this is untested.
              </p>
            </div>
            <div className="p-3 border border-[#262626] bg-[#000000]">
              <span className="font-bold text-[#ffffff] flex items-center gap-1.5 uppercase">
                <AlertTriangle className="h-3.5 w-3.5 text-[#ffffff]" /> Low-Cost MoCap — Goal
              </span>
              <p className="mt-1 text-[#a3a3a3] text-[11px] leading-relaxed">
                Consumer phone cameras in place of a laboratory marker array. Whether the accuracy is adequate for any given measurement is exactly the open question — it has not been established.
              </p>
            </div>
            <div className="p-3 border border-[#262626] bg-[#000000]">
              <span className="font-bold text-[#ffffff] flex items-center gap-1.5 uppercase">
                <CheckCircle2 className="h-3.5 w-3.5 text-[#ffffff]" /> WebGL &amp; Blender Export — Built
              </span>
              <p className="mt-1 text-[#a3a3a3] text-[11px] leading-relaxed">
                Bakes mesh sequences into <code>.blend</code> project files and exports web-playable <code>.glb</code> assets for browser playback.
              </p>
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
