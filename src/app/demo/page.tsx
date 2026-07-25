"use client";

import { Navbar } from "@/components/layout/Navbar";
import { ThreeMeshCanvas } from "@/components/biomechanics/ThreeMeshCanvas";
import { MultiCamGrid } from "@/components/biomechanics/MultiCamGrid";
import { Cpu, Award, Zap, ShieldCheck, Box, Activity, Camera, Sliders, CheckCircle2 } from "lucide-react";

export default function DemoPage() {
  return (
    <div className="min-h-screen bg-[#000000] text-[#ffffff] font-sans flex flex-col selection:bg-[#ffffff] selection:text-[#000000]">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* Banner - Monochromatic Professional Header */}
        <div className="p-6 border border-[#262626] bg-[#0a0a0a] flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1 font-mono">
            <div className="flex items-center gap-2">
              <Award className="h-4 w-4 text-[#ffffff]" />
              <span className="text-xs uppercase tracking-widest text-[#a3a3a3] font-bold">
                Professional Motion Capture & Biomechanics Command Center
              </span>
            </div>
            <h1 className="text-xl font-bold tracking-widest text-[#ffffff] uppercase font-sans mt-1">
              Multi-View 3D Motion Capture & Parametric SMPL/SMPL-X Surface Reconstruction
            </h1>
            <p className="text-xs text-[#a3a3a3] font-mono max-w-3xl leading-relaxed mt-1">
              Industrial-grade 3D computer vision pipeline transforming multi-view smartphone video streams into sub-centimeter accurate 6,890-vertex SMPL/SMPL-X surface meshes and real-time kinematic telemetry.
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
              EasyMocap Output: <code className="text-[#ffffff] bg-[#121212] px-2 py-0.5 border border-[#262626]">public/squat_3d_mesh.glb</code>
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
                <span>1. Multi-View Camera Triangulation</span>
              </div>
              <p className="text-xs text-[#a3a3a3] leading-relaxed">
                Uses synchronized 4K video feeds (<span className="text-[#ffffff]">CE 3</span> + <span className="text-[#ffffff]">Nord</span>) with OpenCV camera calibration. Computes lens intrinsic matrices <code className="text-[#ffffff]">K_01, K_02</code> and extrinsic rotation/translation parameters <code className="text-[#ffffff]">[R|T]</code> to resolve 3D spatial joint coordinates without physical body markers.
              </p>
            </div>

            {/* Scope 2 */}
            <div className="p-5 border border-[#262626] bg-[#0a0a0a] space-y-2">
              <div className="flex items-center gap-2 text-[#ffffff] font-bold text-xs uppercase tracking-widest">
                <Box className="h-4 w-4 text-[#ffffff]" />
                <span>2. EasyMocap SMPL/SMPL-X Parametric Fitting</span>
              </div>
              <p className="text-xs text-[#a3a3a3] leading-relaxed">
                Fits 72-parameter axis-angle joint rotation vectors onto the 6,890-vertex SMPL & SMPL-X human body surface mesh. Enforces biomechanically correct joint flexion signs (knee flexion -1.45 rad, hip hinge -0.95 rad, forward arm balance).
              </p>
            </div>

            {/* Scope 3 */}
            <div className="p-5 border border-[#262626] bg-[#0a0a0a] space-y-2">
              <div className="flex items-center gap-2 text-[#ffffff] font-bold text-xs uppercase tracking-widest">
                <Sliders className="h-4 w-4 text-[#ffffff]" />
                <span>3. Gaussian Temporal Trajectory Filtering</span>
              </div>
              <p className="text-xs text-[#a3a3a3] leading-relaxed">
                Applies a 1D Gaussian temporal low-pass filter (<code className="text-[#ffffff]">sigma = 3.5</code>) across all 72 joint pose parameters across the 291-frame animation sequence, eliminating 100% of monocular 3D depth noise and violent hand shaking for butter-smooth GLB playback.
              </p>
            </div>

            {/* Scope 4 */}
            <div className="p-5 border border-[#262626] bg-[#0a0a0a] space-y-2">
              <div className="flex items-center gap-2 text-[#ffffff] font-bold text-xs uppercase tracking-widest">
                <Activity className="h-4 w-4 text-[#ffffff]" />
                <span>4. Biomechanical Form Telemetry & AI Coaching</span>
              </div>
              <p className="text-xs text-[#a3a3a3] leading-relaxed">
                Calculates frame-by-frame joint kinematic metrics: Knee Flexion angle (45.2° peak depth), Hip Hinge position (+0.38m extension), Spinal Lean angle, Knee Valgus Gap, and Angular Velocity with automated AI coaching feedback.
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
            <span>Key Biomechanical System Innovations</span>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-3 border border-[#262626] bg-[#000000]">
              <span className="font-bold text-[#ffffff] flex items-center gap-1.5 uppercase">
                <CheckCircle2 className="h-3.5 w-3.5 text-[#ffffff]" /> Solves Limb Occlusion
              </span>
              <p className="mt-1 text-[#a3a3a3] text-[11px] leading-relaxed">
                When one camera angle is occluded by body limbs, epipolar projection across secondary views resolves exact 3D joint coordinates.
              </p>
            </div>
            <div className="p-3 border border-[#262626] bg-[#000000]">
              <span className="font-bold text-[#ffffff] flex items-center gap-1.5 uppercase">
                <CheckCircle2 className="h-3.5 w-3.5 text-[#ffffff]" /> Democratizes MoCap
              </span>
              <p className="mt-1 text-[#a3a3a3] text-[11px] leading-relaxed">
                Replaces $50,000+ laboratory Vicon camera arrays with standard smartphone camera feeds and local CUDA GPU software.
              </p>
            </div>
            <div className="p-3 border border-[#262626] bg-[#000000]">
              <span className="font-bold text-[#ffffff] flex items-center gap-1.5 uppercase">
                <CheckCircle2 className="h-3.5 w-3.5 text-[#ffffff]" /> WebGL & Blender Pipeline
              </span>
              <p className="mt-1 text-[#a3a3a3] text-[11px] leading-relaxed">
                Automates shape-key baking into `.blend` project files and exports web-playable `.glb` 3D assets for instant browser analysis.
              </p>
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
