import React, { useState, useRef, useEffect, Suspense, useMemo } from 'react';
import * as THREE from 'three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from 'recharts';
import { Camera, Activity, Ruler, Target, Database, AlertCircle, Box, Play, Pause, ChevronLeft, ChevronRight, Maximize2, X } from 'lucide-react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Environment, Center } from '@react-three/drei';
import kinematicsData from './data.json';
import './index.css';

const Num = ({ children, className = "" }) => (
  <span className={`font-mono ${className}`}>{children}</span>
);

const meshCache = {};

function AnimatedModel({ frame }) {
  const [currentMesh, setCurrentMesh] = useState(null);

  useEffect(() => {
    const loader = new OBJLoader();
    const material = new THREE.MeshBasicMaterial({ 
      color: '#ffffff', 
      wireframe: true,
      transparent: true,
      opacity: 0.2
    });

    for(let i=1; i<=161; i++) {
      const frameStr = String(i).padStart(4, '0');
      loader.load(`/meshes/frame_${frameStr}_0.obj`, (obj) => {
        obj.traverse((child) => {
          if (child.isMesh) child.material = material;
        });
        meshCache[i] = obj;
        if (i === frame + 1) setCurrentMesh(obj);
      });
    }
  }, []);

  useEffect(() => {
    if (meshCache[frame + 1]) {
      setCurrentMesh(meshCache[frame + 1]);
    }
  }, [frame]);

  if (!currentMesh) return null;
  return <primitive object={currentMesh} />;
}

export default function App() {
  const [currentFrame, setCurrentFrame] = useState(0);
  const [videoSrc, setVideoSrc] = useState("/video.mp4");
  const [viewMode, setViewMode] = useState("video"); 
  const [isPlaying3D, setIsPlaying3D] = useState(false);
  const [fps, setFps] = useState(30);
  const [maximizedGraph, setMaximizedGraph] = useState(null); // 'knee' or 'spine'
  const [activePipelineStep, setActivePipelineStep] = useState('Telemetry');
  const videoRef = useRef(null);

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
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-[#ffffff] animate-pulse" />
            <span className="text-[#ffffff] text-[10px] uppercase tracking-widest font-mono">Live</span>
          </div>
        </div>
      </header>

      {/* ──────── MAIN WORKSPACE ──────── */}
      <div className="flex-1 flex gap-4 overflow-hidden">
        
        {/* LEFT PANEL: Architecture & Maps */}
        <aside className="w-[300px] flex flex-col gap-4 shrink-0">
          
          <div className="flex-1 border border-[#333333] flex flex-col bg-[#000000]">
            <div className="border-b border-[#333333] p-2 bg-[#111111]">
              <span className="text-[9px] uppercase tracking-widest text-[#a3a3a3]">Spatial Map</span>
            </div>
            <div className="flex-1 relative bg-[linear-gradient(#111111_1px,transparent_1px),linear-gradient(90deg,#111111_1px,transparent_1px)] bg-[size:20px_20px]">
              
              <div className="absolute top-[40%] left-1/2 -translate-x-1/2 -translate-y-1/2">
                <div className="w-8 h-8 rounded-full border border-[#ffffff] flex items-center justify-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-[#ffffff] animate-pulse" />
                </div>
              </div>

              <div className="absolute top-[calc(40%+24px)] left-1/2 -translate-x-1/2 flex flex-col items-center">
                <span className="text-[9px] uppercase tracking-widest font-bold bg-[#000000] px-1">Subj</span>
                <div className="mt-4 flex flex-col items-center bg-[#000000] p-1">
                  <Camera size={12} />
                  <span className="text-[8px] uppercase tracking-widest mt-1">01_F</span>
                </div>
                <div className="w-[1px] h-8 bg-[#ffffff]/30 mt-1" />
              </div>

              <div className="absolute top-[10%] left-[10%] flex flex-col items-center text-[#a3a3a3]">
                <Camera size={12} />
                <span className="text-[8px] uppercase tracking-widest mt-1">02_L</span>
                <div className="w-[1px] h-12 border-l border-dashed border-[#a3a3a3]/30 mt-1" />
              </div>

              <div className="absolute top-[10%] right-[10%] flex flex-col items-center text-[#a3a3a3]">
                <Camera size={12} />
                <span className="text-[8px] uppercase tracking-widest mt-1">03_R</span>
                <div className="w-[1px] h-12 border-l border-dashed border-[#a3a3a3]/30 mt-1" />
              </div>
            </div>
          </div>

          <div className="h-[250px] border border-[#333333] flex flex-col bg-[#000000]">
            <div className="border-b border-[#333333] p-2 bg-[#111111]">
              <span className="text-[9px] uppercase tracking-widest text-[#a3a3a3]">Pipeline Status</span>
            </div>
            <div className="flex-1 flex flex-col justify-center px-6 gap-6 relative">
              <div className="absolute left-9 top-8 bottom-8 w-[1px] bg-[#333333]" />
              {[
                { icon: Camera, title: 'Capture Sync' },
                { icon: Target, title: 'Spatial Keypoints' },
                { icon: Database, title: 'Mesh Regression' },
                { icon: Activity, title: 'Telemetry' }
              ].map((step, idx) => {
                const isActive = activePipelineStep === step.title;
                return (
                  <button 
                    key={idx} 
                    onClick={() => setActivePipelineStep(step.title)}
                    className="flex items-center gap-4 relative z-10 w-full text-left group"
                  >
                    <div className={`w-6 h-6 rounded border flex items-center justify-center bg-[#000000] transition-colors ${isActive ? 'border-[#ffffff] text-[#ffffff]' : 'border-[#333333] text-[#a3a3a3] group-hover:border-[#ffffff] group-hover:text-[#ffffff]'}`}>
                      <step.icon size={10} />
                    </div>
                    <span className={`text-[10px] uppercase tracking-widest transition-colors ${isActive ? 'text-[#ffffff] font-bold' : 'text-[#a3a3a3] group-hover:text-[#ffffff]'}`}>{step.title}</span>
                  </button>
                );
              })}
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
                <Canvas camera={{ position: [0, 1, 5], fov: 45 }}>
                  <ambientLight intensity={1.5} />
                  <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={2} />
                  <pointLight position={[-10, -10, -10]} intensity={1} />
                  <Suspense fallback={null}>
                    <Center scale={2.5}>
                      <AnimatedModel frame={currentFrame} />
                    </Center>
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
            <div className="absolute inset-0 pointer-events-none border border-[#333333] m-8 mt-12 bg-[linear-gradient(#333333_1px,transparent_1px),linear-gradient(90deg,#333333_1px,transparent_1px)] bg-[size:50px_50px] opacity-10" />
          </div>
        </main>

        {/* RIGHT PANEL: Streaming Data & Mini Graphs */}
        <aside className="w-[350px] flex flex-col gap-4 shrink-0">
          
          <div className="h-[250px] border border-[#333333] flex flex-col bg-[#000000]">
            <div className="border-b border-[#333333] p-2 bg-[#111111] flex justify-between items-center">
              <span className="text-[9px] uppercase tracking-widest text-[#a3a3a3]">Kinematic Readout</span>
              <Activity size={12} className="text-[#ffffff]" />
            </div>
            <div className="flex-1 overflow-y-auto p-3 text-[10px] flex flex-col gap-1 font-mono">
              <div className="flex justify-between border-b border-[#333333] py-1"><span className="text-[#a3a3a3]">L_KNEE</span><span>{currentData.left_knee_angle.toFixed(2)}</span></div>
              <div className="flex justify-between border-b border-[#333333] py-1"><span className="text-[#a3a3a3]">R_KNEE</span><span>{currentData.right_knee_angle.toFixed(2)}</span></div>
              <div className="flex justify-between border-b border-[#333333] py-1"><span className="text-[#a3a3a3]">L_HIP</span><span>{currentData.left_hip_angle.toFixed(2)}</span></div>
              <div className="flex justify-between border-b border-[#333333] py-1"><span className="text-[#a3a3a3]">R_HIP</span><span>{currentData.right_hip_angle.toFixed(2)}</span></div>
              <div className="flex justify-between border-b border-[#333333] py-1"><span className="text-[#a3a3a3]">L_ANKLE</span><span>{currentData.left_ankle_angle.toFixed(2)}</span></div>
              <div className="flex justify-between border-b border-[#333333] py-1"><span className="text-[#a3a3a3]">R_ANKLE</span><span>{currentData.right_ankle_angle.toFixed(2)}</span></div>
              <div className="flex justify-between border-b border-[#333333] py-1"><span className="text-[#a3a3a3]">TORSO</span><span className={isFormDegraded ? 'bg-[#ffffff] text-[#000000] px-1' : ''}>{currentData.torso_lean.toFixed(2)}</span></div>
              <div className="flex justify-between border-b border-[#333333] py-1"><span className="text-[#a3a3a3]">VELOCITY</span><span>{currentData.velocity.toFixed(3)}</span></div>
            </div>
          </div>

          <div className="flex-1 border border-[#333333] flex flex-col bg-[#000000] group relative">
            <div className="border-b border-[#333333] p-2 bg-[#111111] flex justify-between items-center">
              <span className="text-[9px] uppercase tracking-widest text-[#a3a3a3]">Knee Trajectory</span>
              <button onClick={() => setMaximizedGraph('knee')} className="opacity-0 group-hover:opacity-100 transition-opacity text-[#ffffff]">
                <Maximize2 size={12} />
              </button>
            </div>
            <div className="flex-1 p-2 pt-4 cursor-crosshair">
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

          <div className="flex-1 border border-[#333333] flex flex-col bg-[#000000] group relative">
            <div className="border-b border-[#333333] p-2 bg-[#111111] flex justify-between items-center">
              <span className="text-[9px] uppercase tracking-widest text-[#a3a3a3]">Spinal Trajectory</span>
              <button onClick={() => setMaximizedGraph('spine')} className="opacity-0 group-hover:opacity-100 transition-opacity text-[#ffffff]">
                <Maximize2 size={12} />
              </button>
            </div>
            <div className="flex-1 p-2 pt-4 cursor-crosshair">
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

    </div>
  );
}
