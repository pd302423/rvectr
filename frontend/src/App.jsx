import React, { useState, useRef, useEffect, Suspense, useMemo } from 'react';
import * as THREE from 'three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from 'recharts';
import { Camera, Activity, Ruler, Target, Database, AlertCircle, Box, Play, Pause, ChevronLeft, ChevronRight, Maximize2, X, MessageSquare, Layers, Eye, Settings } from 'lucide-react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Environment, Center, Html } from '@react-three/drei';
import squatKinematicsData from './data.json';
import runningKinematicsData from './running_data.json';
import './index.css';

const Num = ({ children, className = "" }) => (
  <span className={`font-mono ${className}`}>{children}</span>
);

const JOINTS = [
  { id: 'left_knee', label: 'L_KNEE', name: 'Left Knee', angleKey: 'left_knee_angle', velKey: 'left_knee_angular_vel', pos: [-0.08, -0.22, 0.05] },
  { id: 'right_knee', label: 'R_KNEE', name: 'Right Knee', angleKey: 'right_knee_angle', velKey: 'right_knee_angular_vel', pos: [0.08, -0.22, 0.05] },
  { id: 'left_hip', label: 'L_HIP', name: 'Left Hip', angleKey: 'left_hip_angle', velKey: 'left_hip_angular_vel', pos: [-0.06, 0.02, 0.0] },
  { id: 'right_hip', label: 'R_HIP', name: 'Right Hip', angleKey: 'right_hip_angle', velKey: 'right_hip_angular_vel', pos: [0.06, 0.02, 0.0] },
  { id: 'left_ankle', label: 'L_ANKLE', name: 'Left Ankle', angleKey: 'left_ankle_angle', velKey: 'left_ankle_angular_vel', pos: [-0.09, -0.48, 0.05] },
  { id: 'right_ankle', label: 'R_ANKLE', name: 'Right Ankle', angleKey: 'right_ankle_angle', velKey: 'right_ankle_angular_vel', pos: [0.09, -0.48, 0.05] },
  { id: 'left_elbow', label: 'L_ELBOW', name: 'Left Elbow', angleKey: 'left_elbow_angle', velKey: 'left_elbow_angular_vel', pos: [-0.20, 0.18, 0.05] },
  { id: 'right_elbow', label: 'R_ELBOW', name: 'Right Elbow', angleKey: 'right_elbow_angle', velKey: 'right_elbow_angular_vel', pos: [0.20, 0.18, 0.05] },
  { id: 'torso', label: 'TORSO', name: 'Spine / Torso', angleKey: 'torso_lean', velKey: 'velocity', pos: [0.0, 0.28, 0.0] },
];

const meshCache = {};

function getMeshMaterial(style) {
  switch (style) {
    case 'smooth_metal':
      return new THREE.MeshStandardMaterial({
        color: '#cbd5e1',
        wireframe: false,
        flatShading: false,
        roughness: 0.08,
        metalness: 0.95,
        envMapIntensity: 2.0
      });
    case 'solid':
      return new THREE.MeshStandardMaterial({
        color: '#e2e8f0',
        wireframe: false,
        flatShading: false,
        roughness: 0.35,
        metalness: 0.1
      });
    case 'metallic':
      return new THREE.MeshStandardMaterial({
        color: '#94a3b8',
        wireframe: false,
        flatShading: false,
        roughness: 0.25,
        metalness: 0.75
      });
    case 'neon':
      return new THREE.MeshStandardMaterial({
        color: '#38bdf8',
        wireframe: true,
        transparent: true,
        opacity: 0.65,
        emissive: '#0284c7',
        emissiveIntensity: 0.5
      });
    case 'translucent':
    default:
      return new THREE.MeshStandardMaterial({
        color: '#ffffff',
        wireframe: true,
        transparent: true,
        opacity: 0.25,
        roughness: 0.5
      });
  }
}

function AnimatedModel({ frame, currentData, selectedJoint, setSelectedJoint, hoveredJoint, setHoveredJoint, meshStyle = 'translucent', exerciseMode = 'running' }) {
  const [currentMesh, setCurrentMesh] = useState(null);

  useEffect(() => {
    const loader = new OBJLoader();
    const folder = exerciseMode === 'running' ? '/running_meshes' : '/meshes';
    const totalFrames = exerciseMode === 'running' ? 90 : 161;

    for(let i=1; i<=totalFrames; i++) {
      const frameStr = String(i).padStart(4, '0');
      const cacheKey = `${exerciseMode}_${i}`;
      loader.load(`${folder}/frame_${frameStr}_0.obj`, (obj) => {
        meshCache[cacheKey] = obj;
        if (i === frame + 1) setCurrentMesh(obj);
      });
    }
  }, [exerciseMode]);

  useEffect(() => {
    const cacheKey = `${exerciseMode}_${frame + 1}`;
    if (meshCache[cacheKey]) {
      setCurrentMesh(meshCache[cacheKey]);
    }
  }, [frame, exerciseMode]);

  useEffect(() => {
    const mat = getMeshMaterial(meshStyle);
    const applySmoothMat = (obj) => {
      if (!obj) return;
      obj.traverse((child) => {
        if (child.isMesh) {
          child.geometry.computeVertexNormals(); // Compute smooth vertex normals
          child.material = mat;
        }
      });
    };

    Object.values(meshCache).forEach(applySmoothMat);
    if (currentMesh) applySmoothMat(currentMesh);
  }, [meshStyle, currentMesh]);

  if (!currentMesh) return null;
  return (
    <group>
      <primitive object={currentMesh} />
    </group>
  );
}

export default function App() {
  const [exerciseMode, setExerciseMode] = useState('squat'); // 'running' | 'squat'
  const kinematicsData = exerciseMode === 'running' ? runningKinematicsData : squatKinematicsData;

  const [currentFrame, setCurrentFrame] = useState(0);
  const [videoSrc, setVideoSrc] = useState("/video.mp4");
  const [viewMode, setViewMode] = useState("3d"); 
  const [isPlaying3D, setIsPlaying3D] = useState(false);
  const [fps, setFps] = useState(30);
  const [maximizedGraph, setMaximizedGraph] = useState(null); // 'knee' or 'spine'
  const [activePipelineStep, setActivePipelineStep] = useState('Telemetry');
  const [showArchitecture, setShowArchitecture] = useState(false);
  const [selectedJoint, setSelectedJoint] = useState(null);
  const [hoveredJoint, setHoveredJoint] = useState(null);
  const [meshStyle, setMeshStyle] = useState('smooth_metal'); // 'translucent' | 'solid' | 'smooth_metal' | 'metallic' | 'neon'
  const [floorStyle, setFloorStyle] = useState('reflective'); // 'reflective' | 'solid' | 'grid_only' | 'neon'
  const [showGrid, setShowGrid] = useState(true);
  const [showMaterialMenu, setShowMaterialMenu] = useState(false);
  const videoRef = useRef(null);

  useEffect(() => {
    if (videoRef.current && viewMode === 'video') {
      const targetTime = currentFrame / 30.0;
      if (Math.abs(videoRef.current.currentTime - targetTime) > 0.04) {
        videoRef.current.currentTime = targetTime;
      }
    }
  }, [currentFrame, viewMode]);

  useEffect(() => {
    let interval;
    if (isPlaying3D && viewMode === '3d') {
      const delay = Math.floor(1000 / fps);
      interval = setInterval(() => {
        setCurrentFrame(prev => (prev >= kinematicsData.length - 1 ? 0 : prev + 1));
      }, delay);
    }
    return () => clearInterval(interval);
  }, [isPlaying3D, viewMode, fps]);

  const handleGraphHover = (state) => {
    if (state && state.activeTooltipIndex !== undefined) {
      setCurrentFrame(state.activeTooltipIndex);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const frame = Math.floor(videoRef.current.currentTime * 30);
      setCurrentFrame(Math.min(frame, kinematicsData.length - 1));
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setVideoSrc(url);
      setCurrentFrame(0);
      if (videoRef.current) {
        videoRef.current.load();
      }
    }
  };

  const currentData = kinematicsData[currentFrame] || kinematicsData[0];
  const isFormDegraded = currentData.torso_lean > 45;
  const activeJointObj = JOINTS.find(j => j.id === (selectedJoint || hoveredJoint));

  return (
    <div className="h-screen w-screen bg-[#000000] text-[#ffffff] font-sans overflow-hidden flex flex-col p-4 gap-4 selection:bg-[#ffffff] selection:text-[#000000]">
      
      {/* ──────── TOP STRIP ──────── */}
      <header className="h-12 flex justify-between items-center border border-[#333333] px-4 shrink-0 bg-[#000000]">
        <div className="flex items-center gap-6">
          <h1 className="text-sm font-bold tracking-widest uppercase">rvector_OS</h1>
          <div className="h-4 w-[1px] bg-[#333333]" />
          <span className="text-[10px] uppercase tracking-widest text-[#a3a3a3]">Session: SUBJ_1945</span>
        </div>
        
        <div className="flex items-center gap-4">
          <label className="text-[10px] uppercase tracking-widest font-mono border border-[#333333] px-4 py-1 hover:bg-[#ffffff] hover:text-[#000000] transition-colors cursor-pointer">
            <input type="file" accept="video/mp4,video/mov,video/*" className="hidden" onChange={handleFileUpload} />
            Mount Feed
          </label>
          <div className="flex items-center gap-6">
            <button 
              onClick={() => setShowArchitecture(true)}
              className="text-[#a3a3a3] hover:text-[#ffffff] text-[9px] uppercase tracking-widest transition-colors font-bold border border-[#333333] hover:border-[#ffffff] px-3 py-1"
            >
              How it Works
            </button>
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-[#ffffff] animate-pulse" />
              <span className="text-[#ffffff] text-[10px] uppercase tracking-widest font-mono">Live</span>
            </div>
          </div>
        </div>
      </header>

      {/* ──────── MAIN WORKSPACE ──────── */}
      <div className="flex-1 flex gap-4 overflow-hidden">
        
        {/* LEFT PANEL: Streaming Data & Mini Graphs */}
        <aside className="w-[350px] flex flex-col gap-4 shrink-0">
          
          <div className="h-[260px] border border-[#333333] flex flex-col bg-[#000000]">
            <div className="border-b border-[#333333] p-2 bg-[#111111] flex justify-between items-center">
              <span className="text-[9px] uppercase tracking-widest text-[#a3a3a3]">Kinematic Readout</span>
              <Activity size={12} className="text-[#ffffff]" />
            </div>
            <div className="flex-1 overflow-y-auto p-3 text-[10px] flex flex-col gap-1 font-mono">
              {JOINTS.map((joint) => {
                const isSel = selectedJoint === joint.id;
                const isHov = hoveredJoint === joint.id;
                const angleVal = currentData[joint.angleKey];
                const velVal = currentData[joint.velKey];

                return (
                  <div
                    key={joint.id}
                    onClick={() => setSelectedJoint(isSel ? null : joint.id)}
                    onMouseEnter={() => setHoveredJoint(joint.id)}
                    onMouseLeave={() => setHoveredJoint(null)}
                    className={`flex justify-between items-center border-b border-[#333333] py-1 px-1 cursor-pointer transition-colors ${
                      isSel ? 'bg-[#38bdf8]/20 border-[#38bdf8] text-[#38bdf8] font-bold' : isHov ? 'bg-[#111111] text-[#ffffff]' : ''
                    }`}
                  >
                    <span className={isSel ? 'text-[#38bdf8]' : 'text-[#a3a3a3]'}>{joint.label}</span>
                    <div className="flex items-center gap-3">
                      <span>{angleVal !== undefined ? angleVal.toFixed(1) : 'N/A'}°</span>
                      <span className={`text-[8px] ${velVal > 0 ? 'text-[#4ade80]' : velVal < 0 ? 'text-[#f87171]' : 'text-[#a3a3a3]'}`}>
                        {velVal !== undefined ? (velVal > 0 ? `+${velVal.toFixed(1)}` : velVal.toFixed(1)) : 'N/A'}
                      </span>
                    </div>
                  </div>
                );
              })}
              <div className="flex justify-between border-b border-[#333333] py-1 px-1"><span className="text-[#a3a3a3]">VELOCITY</span><span>{currentData.velocity.toFixed(3)} m/s</span></div>
            </div>
          </div>

          <div className="flex-1 border border-[#333333] flex flex-col bg-[#000000] relative">
            <div className="border-b border-[#333333] p-2 bg-[#111111] flex justify-between items-center">
              <span className="text-[9px] uppercase tracking-widest text-[#a3a3a3]">Knee Trajectory</span>
              <button onClick={() => setMaximizedGraph('knee')} className="text-[#a3a3a3] hover:text-[#ffffff] flex items-center gap-1 transition-colors">
                <span className="text-[8px] uppercase font-bold tracking-widest">Expand</span>
                <Maximize2 size={10} />
              </button>
            </div>
            
            <div className="absolute top-10 right-4 text-[8px] uppercase font-mono text-right pointer-events-none z-10">
              <div className="text-[#ffffff] flex items-center justify-end gap-1"><div className="w-2 h-0.5 bg-[#ffffff]" /> Left Knee</div>
              <div className="text-[#a3a3a3] flex items-center justify-end gap-1 mt-0.5"><div className="w-2 h-0.5 border-t border-dashed border-[#a3a3a3]" /> Right Knee</div>
            </div>

            <div className="flex-1 p-2 pt-4 cursor-crosshair relative">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={kinematicsData} margin={{ top: 0, right: 5, bottom: 0, left: -25 }} onMouseMove={handleGraphHover}>
                  <XAxis dataKey="frame" hide />
                  <YAxis domain={[40, 180]} stroke="#333333" tick={{fontSize: 9, fontFamily: 'IBM Plex Mono', fill: '#a3a3a3'}} tickLine={false} axisLine={false} />
                  <ReferenceLine x={currentFrame + 1} stroke="#ffffff" strokeWidth={1} />
                  <Line type="step" dataKey="left_knee_angle" stroke="#ffffff" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                  <Line type="step" dataKey="right_knee_angle" stroke="#a3a3a3" strokeWidth={1} strokeDasharray="3 3" dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="flex-1 border border-[#333333] flex flex-col bg-[#000000] relative">
            <div className="border-b border-[#333333] p-2 bg-[#111111] flex justify-between items-center">
              <span className="text-[9px] uppercase tracking-widest text-[#a3a3a3]">Spinal Trajectory</span>
              <button onClick={() => setMaximizedGraph('spine')} className="text-[#a3a3a3] hover:text-[#ffffff] flex items-center gap-1 transition-colors">
                <span className="text-[8px] uppercase font-bold tracking-widest">Expand</span>
                <Maximize2 size={10} />
              </button>
            </div>
            <div className="flex-1 p-2 pt-4 cursor-crosshair relative">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={kinematicsData} margin={{ top: 0, right: 5, bottom: 0, left: -25 }} onMouseMove={handleGraphHover}>
                  <XAxis dataKey="frame" hide />
                  <YAxis domain={[0, 90]} stroke="#333333" tick={{fontSize: 9, fontFamily: 'IBM Plex Mono', fill: '#a3a3a3'}} tickLine={false} axisLine={false} />
                  <ReferenceLine x={currentFrame + 1} stroke="#ffffff" strokeWidth={1} />
                  <Line type="step" dataKey="torso_lean" stroke="#ffffff" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

        </aside>

        {/* CENTER PANEL: Massive Scaled Video or 3D Viewer */}
        <main className="flex-1 border border-[#333333] flex flex-col bg-[#000000] relative">
          <div className="border-b border-[#333333] p-2 flex justify-between items-center bg-[#111111] absolute top-0 w-full z-20">
            <div className="flex items-center gap-4">
              <button 
                onClick={() => setViewMode("video")}
                className={`text-[9px] uppercase tracking-widest transition-colors ${viewMode === 'video' ? 'text-[#ffffff] font-bold' : 'text-[#a3a3a3] hover:text-[#ffffff]'}`}
              >
                Optical Feed
              </button>
              <button 
                onClick={() => setViewMode("3d")}
                className={`text-[9px] uppercase tracking-widest flex items-center gap-1 transition-colors ${viewMode === '3d' ? 'text-[#ffffff] font-bold' : 'text-[#a3a3a3] hover:text-[#ffffff]'}`}
              >
                <Box size={10} /> Spatial Mesh
              </button>
            </div>

            {/* Quick 3D Joint Selection Node Toolbar & View Menu */}
            {viewMode === "3d" && (
              <div className="flex items-center gap-3 font-mono text-[8px]">
                <div className="flex items-center gap-1">
                  <span className="text-[#a3a3a3] uppercase mr-1">3D Node:</span>
                  {JOINTS.map(j => (
                    <button
                      key={j.id}
                      onClick={() => setSelectedJoint(selectedJoint === j.id ? null : j.id)}
                      className={`px-1.5 py-0.5 border uppercase transition-colors ${
                        selectedJoint === j.id 
                          ? 'border-[#38bdf8] bg-[#38bdf8] text-[#000000] font-bold' 
                          : 'border-[#333333] text-[#a3a3a3] hover:border-[#ffffff] hover:text-[#ffffff]'
                      }`}
                    >
                      {j.label}
                    </button>
                  ))}
                </div>

                {/* Viewport Material Config Menu Dropdown */}
                <div className="relative">
                  <button
                    onClick={() => setShowMaterialMenu(!showMaterialMenu)}
                    className="text-[9px] uppercase tracking-widest flex items-center gap-1 font-mono border border-[#333333] hover:border-[#ffffff] px-2 py-0.5 bg-[#000000] text-[#ffffff] transition-colors"
                  >
                    <Layers size={10} /> View Menu
                  </button>

                  {showMaterialMenu && (
                    <div className="absolute right-0 top-7 z-40 bg-[#0a0a0a]/95 border border-[#262626] p-3 rounded-md font-mono text-[9px] w-60 flex flex-col gap-3 shadow-[0_10px_30px_rgba(0,0,0,0.8)] backdrop-blur-xl">
                      <div className="flex justify-between items-center border-b border-[#262626] pb-1 text-[#ffffff] font-bold uppercase tracking-widest">
                        <span>Viewport Settings</span>
                        <button onClick={() => setShowMaterialMenu(false)} className="text-[#a3a3a3] hover:text-[#ffffff]">
                          <X size={12} />
                        </button>
                      </div>

                      {/* Mesh Material Selector */}
                      <div>
                        <span className="text-[#a3a3a3] uppercase block mb-1 text-[8px]">Avatar Mesh Material:</span>
                        <div className="grid grid-cols-2 gap-1">
                          {[
                            { id: 'translucent', label: 'Translucent' },
                            { id: 'solid', label: 'Solid Matte' },
                            { id: 'smooth_metal', label: 'Smooth Metal' },
                            { id: 'metallic', label: 'Metallic' },
                            { id: 'neon', label: 'Cyber Neon' }
                          ].map(m => (
                            <button
                              key={m.id}
                              onClick={() => setMeshStyle(m.id)}
                              className={`p-1 border text-[8px] uppercase transition-colors text-center rounded-sm ${
                                meshStyle === m.id ? 'border-[#38bdf8] bg-[#38bdf8]/20 text-[#38bdf8] font-bold' : 'border-[#262626] text-[#a3a3a3] hover:border-[#ffffff] hover:text-[#ffffff]'
                              }`}
                            >
                              {m.label}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Floor Material Selector */}
                      <div>
                        <span className="text-[#a3a3a3] uppercase block mb-1 text-[8px]">Floor Ground Style:</span>
                        <div className="grid grid-cols-2 gap-1">
                          {[
                            { id: 'reflective', label: 'Reflective' },
                            { id: 'solid', label: 'Solid Floor' },
                            { id: 'grid_only', label: 'Grid Only' },
                            { id: 'neon', label: 'Cyber Grid' }
                          ].map(f => (
                            <button
                              key={f.id}
                              onClick={() => setFloorStyle(f.id)}
                              className={`p-1 border text-[8px] uppercase transition-colors text-center rounded-sm ${
                                floorStyle === f.id ? 'border-[#38bdf8] bg-[#38bdf8]/20 text-[#38bdf8] font-bold' : 'border-[#262626] text-[#a3a3a3] hover:border-[#ffffff] hover:text-[#ffffff]'
                              }`}
                            >
                              {f.label}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Grid Lines Toggle */}
                      <div className="flex justify-between items-center border-t border-[#262626] pt-2">
                        <span className="text-[#a3a3a3] uppercase text-[8px]">Show Floor Grid:</span>
                        <button
                          onClick={() => setShowGrid(!showGrid)}
                          className={`px-2 py-0.5 border text-[8px] uppercase font-bold transition-colors rounded-sm ${
                            showGrid ? 'border-[#4ade80] bg-[#4ade80]/20 text-[#4ade80]' : 'border-[#262626] text-[#a3a3a3]'
                          }`}
                        >
                          {showGrid ? 'ON' : 'OFF'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {viewMode === "video" && (
              <span className="text-[10px] uppercase font-mono text-[#ffffff]">FR_<Num>{String(currentFrame + 1).padStart(3, '0')}</Num></span>
            )}
          </div>
          
          <div className="flex-1 w-full h-full p-8 pt-12 relative flex items-center justify-center">
            
            {viewMode === "video" ? (
              <>
                <video 
                  ref={videoRef}
                  src={videoSrc}
                  controls
                  onTimeUpdate={handleTimeUpdate}
                  className="w-full h-full object-contain mix-blend-lighten opacity-90"
                />
                
                {/* HUD OVERLAYS PINNED TO CORNERS */}
                <div className="absolute top-16 left-12 border-l-2 border-[#ffffff] pl-3 pointer-events-none">
                  <p className="text-[9px] uppercase tracking-widest text-[#a3a3a3]">Spinal Flexion</p>
                  <p className="text-2xl font-mono mt-1">{currentData.torso_lean.toFixed(1)}°</p>
                  {isFormDegraded && <p className="text-[9px] font-bold uppercase mt-1 bg-[#ffffff] text-[#000000] px-1 inline-block animate-pulse">Shear Warn</p>}
                </div>

                <div className="absolute top-16 right-12 border-l-2 border-[#ffffff] pl-3 text-right border-r-2 border-l-0 pr-3 pointer-events-none">
                  <p className="text-[9px] uppercase tracking-widest text-[#a3a3a3]">Hip (L/R)</p>
                  <p className="text-xl font-mono mt-1">{currentData.left_hip_angle.toFixed(1)}° / <span className="text-[#a3a3a3]">{currentData.right_hip_angle.toFixed(1)}°</span></p>
                </div>

                <div className="absolute bottom-12 left-12 border-l-2 border-[#ffffff] pl-3 pointer-events-none">
                  <p className="text-[9px] uppercase tracking-widest text-[#a3a3a3]">Knee (L/R)</p>
                  <p className="text-xl font-mono mt-1">{currentData.left_knee_angle.toFixed(1)}° / <span className="text-[#a3a3a3]">{currentData.right_knee_angle.toFixed(1)}°</span></p>
                  <p className="text-[9px] uppercase tracking-widest text-[#a3a3a3] mt-2">Valgus</p>
                  <p className="text-sm font-mono mt-0.5">{currentData.knee_distance.toFixed(3)}m</p>
                </div>

                <div className="absolute bottom-12 right-12 border-r-2 border-[#ffffff] pr-3 text-right pointer-events-none">
                  <p className="text-[9px] uppercase tracking-widest text-[#a3a3a3]">Ankle (L/R)</p>
                  <p className="text-xl font-mono mt-1">{currentData.left_ankle_angle.toFixed(1)}° / <span className="text-[#a3a3a3]">{currentData.right_ankle_angle.toFixed(1)}°</span></p>
                  <p className="text-[9px] uppercase tracking-widest text-[#a3a3a3] mt-2">Velocity</p>
                  <p className="text-sm font-mono mt-0.5">{currentData.velocity.toFixed(3)}m/s</p>
                </div>
              </>
            ) : (
              <div className="w-full h-full cursor-grab active:cursor-grabbing relative">

                <Canvas camera={{ position: [0, 0, 3.8], fov: 50 }}>
                  <ambientLight intensity={1.5} />
                  <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={2} />
                  <pointLight position={[-10, -10, -10]} intensity={1} />
                  <Suspense fallback={null}>
                    <Center position={[0, 0, 0]}>
                      <group scale={1.8}>
                        <AnimatedModel 
                          frame={currentFrame} 
                          currentData={currentData} 
                          selectedJoint={selectedJoint}
                          setSelectedJoint={setSelectedJoint}
                          hoveredJoint={hoveredJoint}
                          setHoveredJoint={setHoveredJoint}
                          meshStyle={meshStyle}
                          exerciseMode={exerciseMode}
                        />
                      </group>
                    </Center>

                    {/* Dynamic 3D Ground Plane & Grid Helper */}
                    {showGrid && (
                      <gridHelper 
                        args={[
                          20, 
                          20, 
                          floorStyle === 'neon' ? '#38bdf8' : floorStyle === 'grid_only' ? '#38bdf8' : '#ffffff', 
                          floorStyle === 'neon' ? '#0284c7' : floorStyle === 'grid_only' ? '#1e293b' : '#333333'
                        ]} 
                        position={[0, -1.02, 0]} 
                      />
                    )}

                    {floorStyle !== 'grid_only' && (
                      <mesh position={[0, -1.025, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <planeGeometry args={[20, 20]} />
                        <meshStandardMaterial 
                          color={floorStyle === 'solid' ? '#1e293b' : floorStyle === 'neon' ? '#030712' : '#050505'} 
                          roughness={floorStyle === 'solid' ? 0.9 : floorStyle === 'neon' ? 0.4 : 0.8} 
                          metalness={floorStyle === 'solid' ? 0.0 : floorStyle === 'neon' ? 0.6 : 0.2} 
                        />
                      </mesh>
                    )}

                    <Environment preset="city" />
                  </Suspense>
                  <OrbitControls enablePan={true} enableZoom={true} enableRotate={true} />
                </Canvas>
                
                {/* 3D Playback Controls */}
                <div className="absolute bottom-12 left-12 right-12 flex items-center gap-4 bg-[#000000] border border-[#333333] p-3 pointer-events-auto">
                  
                  <div className="flex gap-1">
                    <button 
                      onClick={() => { setIsPlaying3D(false); setCurrentFrame(p => Math.max(0, p - 1)); }}
                      className="flex items-center justify-center w-8 h-8 border border-[#333333] text-[#ffffff] hover:bg-[#ffffff] hover:text-[#000000] transition-colors"
                    >
                      <ChevronLeft size={14} />
                    </button>
                    <button 
                      onClick={() => setIsPlaying3D(!isPlaying3D)}
                      className="flex items-center justify-center w-8 h-8 border border-[#333333] text-[#ffffff] hover:bg-[#ffffff] hover:text-[#000000] transition-colors"
                    >
                      {isPlaying3D ? <Pause size={14} /> : <Play size={14} className="ml-0.5" />}
                    </button>
                    <button 
                      onClick={() => { setIsPlaying3D(false); setCurrentFrame(p => Math.min(kinematicsData.length - 1, p + 1)); }}
                      className="flex items-center justify-center w-8 h-8 border border-[#333333] text-[#ffffff] hover:bg-[#ffffff] hover:text-[#000000] transition-colors"
                    >
                      <ChevronRight size={14} />
                    </button>
                  </div>
                  
                  <input 
                    type="range" 
                    min={0} 
                    max={kinematicsData.length - 1} 
                    value={currentFrame}
                    onChange={(e) => { setCurrentFrame(Number(e.target.value)); setIsPlaying3D(false); }}
                    className="flex-1 accent-[#ffffff] h-1 bg-[#333333] appearance-none cursor-pointer mx-2"
                  />
                  
                  <button 
                    onClick={() => setFps(f => f === 30 ? 60 : f === 60 ? 15 : 30)}
                    className="text-[9px] font-mono border border-[#333333] px-2 py-1 w-12 hover:bg-[#ffffff] hover:text-[#000000] transition-colors text-center"
                  >
                    {fps}FPS
                  </button>

                  <span className="text-[10px] font-mono text-[#ffffff] w-16 text-right">
                    {currentFrame + 1} / {kinematicsData.length}
                  </span>
                </div>
              </div>
            )}
            
            {/* Grid overlay over the container */}
            <div className="absolute inset-0 pointer-events-none border border-[#333333] m-8 mt-12 bg-[linear-gradient(#333333_1px,transparent_1px),gradient(90deg,#333333_1px,transparent_1px)] bg-[size:50px_50px] opacity-10" />
          </div>
        </main>

        {/* RIGHT PANEL: AI Chatbot Window */}
        <aside className="w-[350px] flex flex-col gap-4 shrink-0">
          <div className="flex-1 border border-[#333333] flex flex-col bg-[#000000]">
            <div className="border-b border-[#333333] p-2 bg-[#111111] flex justify-between items-center">
              <span className="text-[9px] uppercase tracking-widest text-[#a3a3a3] flex items-center gap-2">
                <MessageSquare size={12} /> AI COACH
              </span>
              <div className="w-1.5 h-1.5 rounded-full bg-[#ffffff] animate-pulse" />
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
              <div className="bg-[#111111] border border-[#333333] p-3 text-[10px] font-mono text-[#a3a3a3]">
                <span className="text-[#ffffff] font-bold">SYSTEM:</span> Frame {currentFrame + 1} analysis complete.
              </div>
              
              {isFormDegraded ? (
                <div className="bg-[#ffffff] border border-[#ffffff] p-3 text-[10px] font-mono text-[#000000] shadow-[0_0_15px_rgba(255,255,255,0.2)] animate-pulse">
                  <span className="font-bold">AI COACH:</span> Critical Warning! Your torso lean has exceeded the safe threshold ({currentData.torso_lean.toFixed(1)}°). This puts dangerous shear force on your lower back. Keep your chest up!
                </div>
              ) : (
                <div className="bg-[#111111] border border-[#333333] p-3 text-[10px] font-mono text-[#a3a3a3]">
                  <span className="text-[#ffffff] font-bold">AI COACH:</span> Form looks solid. Spine and knee valgus are within safe physiological limits.
                </div>
              )}
              
              {currentData.knee_distance < 0.2 && (
                <div className="bg-[#ffffff] border border-[#ffffff] p-3 text-[10px] font-mono text-[#000000] shadow-[0_0_15px_rgba(255,255,255,0.2)] animate-pulse">
                  <span className="font-bold">AI COACH:</span> Knee Valgus detected! Push your knees outward. Valgus collapse greatly increases ACL injury risk.
                </div>
              )}
            </div>
            
            <div className="border-t border-[#333333] p-2 bg-[#111111]">
              <div className="flex items-center gap-2">
                <input 
                  type="text" 
                  placeholder="Ask AI Coach about this frame..." 
                  className="flex-1 bg-[#000000] border border-[#333333] text-[#ffffff] text-[10px] font-mono p-2 focus:outline-none focus:border-[#ffffff] placeholder:text-[#333333]"
                />
                <button className="bg-[#ffffff] text-[#000000] p-2 px-4 text-[10px] font-bold uppercase tracking-widest hover:bg-[#a3a3a3] transition-colors">
                  SEND
                </button>
              </div>
            </div>
          </div>
        </aside>
      </div>

      {/* ──────── MAXIMIZED GRAPH MODAL ──────── */}
      {maximizedGraph && (
        <div className="fixed inset-0 z-50 bg-[#000000]/90 backdrop-blur-sm flex items-center justify-center p-12">
          <div className="w-full h-full max-w-6xl max-h-[800px] bg-[#000000] border border-[#ffffff] flex flex-col shadow-2xl">
            <div className="flex justify-between items-center p-4 border-b border-[#333333]">
              <span className="text-sm font-bold uppercase tracking-widest text-[#ffffff]">
                {maximizedGraph === 'knee' ? 'Detailed Knee Trajectory Analysis' : 'Detailed Spinal Trajectory Analysis'}
              </span>
              <button onClick={() => setMaximizedGraph(null)} className="text-[#a3a3a3] hover:text-[#ffffff] transition-colors p-2">
                <X size={20} />
              </button>
            </div>
            <div className="flex-1 p-8 cursor-crosshair">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={kinematicsData} onMouseMove={handleGraphHover}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333333" vertical={false} />
                  <XAxis dataKey="frame" stroke="#a3a3a3" tick={{fontSize: 12, fontFamily: 'IBM Plex Mono'}} />
                  <YAxis 
                    domain={maximizedGraph === 'knee' ? [40, 180] : [0, 90]} 
                    stroke="#a3a3a3" 
                    tick={{fontSize: 12, fontFamily: 'IBM Plex Mono'}} 
                    tickLine={false} 
                    axisLine={false} 
                  />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#000000', border: '1px solid #333333', borderRadius: 0 }}
                    itemStyle={{ fontFamily: 'IBM Plex Mono', fontSize: '14px', color: '#ffffff' }}
                    labelStyle={{ fontFamily: 'Inter', fontSize: '12px', color: '#a3a3a3', marginBottom: '8px' }}
                    formatter={(value) => [<Num>{value}</Num>, undefined]}
                    labelFormatter={(label) => `FRAME ${label}`}
                  />
                  <ReferenceLine x={currentFrame + 1} stroke="#ffffff" strokeWidth={1} />
                  
                  {maximizedGraph === 'knee' ? (
                    <>
                      <Line type="step" dataKey="left_knee_angle" name="L_KNEE" stroke="#ffffff" strokeWidth={3} dot={false} isAnimationActive={false} />
                      <Line type="step" dataKey="right_knee_angle" name="R_KNEE" stroke="#a3a3a3" strokeWidth={2} strokeDasharray="5 5" dot={false} isAnimationActive={false} />
                    </>
                  ) : (
                    <Line type="step" dataKey="torso_lean" name="SPINE_LEAN" stroke="#ffffff" strokeWidth={3} dot={false} isAnimationActive={false} />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* ──────── ARCHITECTURE MODAL ──────── */}
      {showArchitecture && (
        <div className="fixed inset-0 z-50 bg-[#000000]/90 backdrop-blur-sm flex items-center justify-center p-12">
          <div className="w-full max-w-4xl bg-[#000000] border border-[#ffffff] flex flex-col shadow-2xl">
            <div className="flex justify-between items-center p-4 border-b border-[#333333]">
              <span className="text-sm font-bold uppercase tracking-widest text-[#ffffff] flex items-center gap-2">
                <Database size={16} /> System Architecture
              </span>
              <button onClick={() => setShowArchitecture(false)} className="text-[#a3a3a3] hover:text-[#ffffff] transition-colors p-2">
                <X size={20} />
              </button>
            </div>
            <div className="p-8 font-mono text-sm text-[#a3a3a3] leading-relaxed overflow-y-auto max-h-[70vh]">
              <p className="text-[#ffffff] font-bold mb-4 uppercase tracking-widest">Pipeline Overview</p>
              <p>This system uses state-of-the-art computer vision to extract 3D kinematic data directly from a raw 2D video feed.</p>
              
              <div className="my-8 border-l-2 border-[#333333] pl-6 flex flex-col gap-8">
                <div>
                  <p className="text-[#ffffff] font-bold mb-2 uppercase tracking-widest flex items-center gap-2"><Target size={14} /> 1. Optical Processing</p>
                  <p>Raw video is fed into <span className="text-[#ffffff] font-bold">4D-Humans</span> to reconstruct SMPL 3D human meshes for every single frame.</p>
                </div>
                
                <div>
                  <p className="text-[#ffffff] font-bold mb-2 uppercase tracking-widest flex items-center gap-2"><Box size={14} /> 2. Mesh Extraction</p>
                  <p>We execute a custom Blender python script in headless mode to bake the mathematical SMPL parameters into 161 individual `.obj` files, one for each frame.</p>
                </div>
                
                <div>
                  <p className="text-[#ffffff] font-bold mb-2 uppercase tracking-widest flex items-center gap-2"><Activity size={14} /> 3. Real-time Streaming</p>
                  <p>The frontend React application loads these `.obj` files directly into the browser's GPU using WebGL via <span className="text-[#ffffff] font-bold">@react-three/fiber</span>, mapping the physical 3D mesh strictly to the calculated telemetry in real-time.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
