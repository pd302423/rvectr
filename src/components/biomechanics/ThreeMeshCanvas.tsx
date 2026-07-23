"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { useBiomechanicsStore } from "@/lib/store";
import { Box, RefreshCw, Eye } from "lucide-react";

interface ThreeMeshCanvasProps {
  width?: string;
  height?: string;
}

// MediaPipe 33 landmark connections for 3D skeleton rendering
const SKELETON_CONNECTIONS: [number, number][] = [
  // Head
  [0, 1], [1, 2], [2, 3], [3, 7], [0, 4], [4, 5], [5, 6], [6, 8], [9, 10],
  // Torso
  [11, 12], [11, 23], [12, 24], [23, 24],
  // Left Arm
  [11, 13], [13, 15], [15, 17], [15, 19], [15, 21], [17, 19],
  // Right Arm
  [12, 14], [14, 16], [16, 18], [16, 20], [16, 22], [18, 20],
  // Left Leg
  [23, 25], [25, 27], [27, 29], [29, 31], [27, 31],
  // Right Leg
  [24, 26], [26, 28], [28, 30], [30, 32], [28, 32],
];

export function ThreeMeshCanvas({ height = "420px" }: ThreeMeshCanvasProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const { currentAnalysis, activeFrame } = useBiomechanicsStore();

  useEffect(() => {
    if (!mountRef.current) return;
    const container = mountRef.current;
    const width = container.clientWidth || 500;
    const h = container.clientHeight || 420;

    // Scene, Camera, Renderer setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a); // Deep slate dark blue

    const camera = new THREE.PerspectiveCamera(45, width / h, 0.1, 1000);
    camera.position.set(0, 1.2, 3);
    camera.lookAt(0, 1, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;

    container.appendChild(renderer.domElement);

    // Grid Helper
    const gridHelper = new THREE.GridHelper(10, 20, 0x3b82f6, 0x1e293b);
    gridHelper.position.y = -0.5;
    scene.add(gridHelper);

    // Ambient & Directional Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x60a5fa, 1.5);
    dirLight.position.set(5, 10, 7);
    scene.add(dirLight);

    // Group for Skeleton
    const skeletonGroup = new THREE.Group();
    scene.add(skeletonGroup);

    // Joint Spheres & Line Meshes
    const jointSpheres: THREE.Mesh[] = [];
    const jointMaterial = new THREE.MeshStandardMaterial({
      color: 0x38bdf8, // Sky blue
      roughness: 0.3,
      metalness: 0.5,
    });
    const jointGeometry = new THREE.SphereGeometry(0.035, 16, 16);

    for (let i = 0; i < 33; i++) {
      const sphere = new THREE.Mesh(jointGeometry, jointMaterial);
      sphere.position.set((Math.random() - 0.5) * 0.5, Math.random() * 1.5, 0);
      skeletonGroup.add(sphere);
      jointSpheres.push(sphere);
    }

    // Bone Lines
    const lineMaterial = new THREE.LineBasicMaterial({ color: 0x818cf8, linewidth: 2 });
    const lineGeometries: THREE.BufferGeometry[] = [];
    const boneLines: THREE.Line[] = [];

    SKELETON_CONNECTIONS.forEach(() => {
      const geom = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(0, 0, 0),
      ]);
      const line = new THREE.Line(geom, lineMaterial);
      skeletonGroup.add(line);
      lineGeometries.push(geom);
      boneLines.push(line);
    });

    // Simple Mouse Drag Orbit Controls implementation
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };

    const onMouseDown = (e: MouseEvent) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaX = e.clientX - previousMousePosition.x;
      const deltaY = e.clientY - previousMousePosition.y;

      skeletonGroup.rotation.y += deltaX * 0.01;
      skeletonGroup.rotation.x += deltaY * 0.01;

      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    container.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);

    // Animation Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    // Store references for landmark updates
    (container as any).__updateSkeleton = (landmarks: Record<string, { x: number; y: number; z: number }>) => {
      if (!landmarks) return;
      const landmarkKeys = Object.keys(landmarks);

      landmarkKeys.forEach((key, idx) => {
        if (idx < jointSpheres.length) {
          const pt = landmarks[key];
          // Map MediaPipe normalized coords (0-1) to 3D Scene space
          const x = (pt.x - 0.5) * 2;
          const y = (0.8 - pt.y) * 2;
          const z = pt.z ? pt.z * -2 : 0;
          jointSpheres[idx].position.set(x, y, z);
        }
      });

      // Update bone connection lines
      SKELETON_CONNECTIONS.forEach(([idxA, idxB], lineIdx) => {
        if (idxA < jointSpheres.length && idxB < jointSpheres.length) {
          const posA = jointSpheres[idxA].position;
          const posB = jointSpheres[idxB].position;
          const geom = lineGeometries[lineIdx];
          geom.setFromPoints([posA, posB]);
        }
      });
    };

    // Clean up
    return () => {
      cancelAnimationFrame(animationFrameId);
      container.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  // Update skeleton positions whenever activeFrame changes
  useEffect(() => {
    if (!mountRef.current || !currentAnalysis?.frame_analyses) return;
    const frames = currentAnalysis.frame_analyses;
    const targetFrame = frames[activeFrame] || frames[0];
    if (targetFrame && targetFrame.landmarks && (mountRef.current as any).__updateSkeleton) {
      (mountRef.current as any).__updateSkeleton(targetFrame.landmarks);
    }
  }, [activeFrame, currentAnalysis]);

  return (
    <div className="relative rounded-xl border border-border bg-slate-950 overflow-hidden shadow-md">
      {/* 3D Control Header Overlay */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700/60 backdrop-blur-md text-xs font-mono text-slate-200">
        <Box className="h-3.5 w-3.5 text-sky-400" />
        <span>3D WebGL SMPL Mesh View</span>
      </div>

      <div className="absolute top-3 right-3 z-10 flex items-center gap-2 text-[10px] font-mono text-slate-400 bg-slate-900/60 px-2 py-1 rounded border border-slate-800">
        <Eye className="h-3 w-3 text-indigo-400" />
        <span>Drag to rotate 360°</span>
      </div>

      {/* Three.js Mounting Container */}
      <div ref={mountRef} style={{ height }} className="w-full cursor-grab active:cursor-grabbing" />
    </div>
  );
}
