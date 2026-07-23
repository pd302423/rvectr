"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import {
  getElbowAngle,
  getHipAngle,
  getKneeAngle,
  getShoulderAngle,
  Landmark,
} from "@/lib/cv/angles";
import {
  extractSquatFrame,
  gradeSquatRep,
  calculateTorsoLean,
  type SquatFrameData,
  type SquatRepScore,
} from "@/lib/cv/grade-squat";
import {
  createRepCounter,
  updateRepCounter,
  type RepCounterState,
  type RepPhase,
} from "@/lib/cv/rep-counter";

// Bone connections in MediaPipe Pose
const POSE_CONNECTIONS = [
  // Nose to eyes/ears
  [0, 1], [1, 2], [2, 3], [3, 7],
  [0, 4], [4, 5], [5, 6], [6, 8],
  [9, 10],
  // Shoulders & arms
  [11, 12],
  [11, 13], [13, 15],
  [12, 14], [14, 16],
  // Hands/wrists details
  [15, 17], [17, 19], [19, 15], [15, 21],
  [16, 18], [18, 20], [20, 16], [16, 22],
  // Torso
  [11, 23], [12, 24], [23, 24],
  // Legs
  [23, 25], [25, 27],
  [24, 26], [26, 28],
  // Feet details
  [27, 29], [29, 31], [31, 27],
  [28, 30], [30, 32], [32, 28]
];

// ---------- helpers ----------
function scoreColor(score: number): string {
  if (score >= 80) return "text-emerald-700";
  if (score >= 60) return "text-amber-700";
  return "text-red-700";
}

function scoreBg(score: number): string {
  if (score >= 80) return "bg-emerald-50 border-emerald-200";
  if (score >= 60) return "bg-amber-50 border-amber-200";
  return "bg-red-50 border-red-200";
}

function phaseLabel(phase: RepPhase): string {
  switch (phase) {
    case "standing": return "STANDING";
    case "descending": return "DESCENDING";
    case "bottom": return "BOTTOM";
    case "ascending": return "ASCENDING";
  }
}

function phaseColor(phase: RepPhase): string {
  switch (phase) {
    case "standing": return "text-emerald-700";
    case "descending": return "text-amber-700";
    case "bottom": return "text-red-700";
    case "ascending": return "text-amber-700";
  }
}

function faultLabel(fault: string): string {
  switch (fault) {
    case "insufficient_depth": return "Insufficient depth";
    case "knee_cave": return "Knee cave";
    case "excessive_forward_lean": return "Excessive forward lean";
    case "heel_rise": return "Heel rise detected";
    case "asymmetry": return "Left/right asymmetry";
    default: return fault;
  }
}

export default function SquatTestPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number | null>(null);
  const poseLandmarkerRef = useRef<any>(null);

  // States
  const [modelState, setModelState] = useState<"loading" | "ready" | "error">("loading");
  const [cameraState, setCameraState] = useState<"idle" | "requesting" | "active" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isMirrored, setIsMirrored] = useState(true);
  const [fps, setFps] = useState(0);
  const [aspectRatio, setAspectRatio] = useState<number>(16 / 9);

  // Live joint angles
  const [angles, setAngles] = useState({
    leftElbow: 0,
    rightElbow: 0,
    leftHip: 0,
    rightHip: 0,
    leftShoulder: 0,
    rightShoulder: 0,
    leftKnee: 0,
    rightKnee: 0,
  });
  const [torsoLean, setTorsoLean] = useState(0);

  // Rep counter & scoring state
  const repCounterRef = useRef<RepCounterState>(createRepCounter());
  const repFramesRef = useRef<SquatFrameData[]>([]);
  const [repCount, setRepCount] = useState(0);
  const [currentPhase, setCurrentPhase] = useState<RepPhase>("standing");
  const [repScores, setRepScores] = useState<SquatRepScore[]>([]);
  const [liveScore, setLiveScore] = useState<number | null>(null);

  // FPS tracking refs
  const lastFpsUpdateRef = useRef(0);
  const frameCountRef = useRef(0);

  // Initialize MediaPipe Pose Landmarker
  useEffect(() => {
    let active = true;

    async function initMediaPipe() {
      try {
        setModelState("loading");
        const vision = await import("@mediapipe/tasks-vision");
        const filesetResolver = await vision.FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.8/wasm"
        );
        
        if (!active) return;

        const poseLandmarker = await vision.PoseLandmarker.createFromOptions(filesetResolver, {
          baseOptions: {
            modelAssetPath: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task",
            delegate: "GPU",
          },
          runningMode: "VIDEO",
          numPoses: 1,
        });

        if (!active) return;

        poseLandmarkerRef.current = poseLandmarker;
        setModelState("ready");
      } catch (err: any) {
        console.error("Failed to load MediaPipe Pose model:", err);
        if (active) {
          setModelState("error");
          setErrorMsg("Could not load pose detection model. Check network connectivity.");
        }
      }
    }

    initMediaPipe();

    return () => {
      active = false;
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  // Reset scoring
  const resetScoring = useCallback(() => {
    repCounterRef.current = createRepCounter();
    repFramesRef.current = [];
    setRepCount(0);
    setCurrentPhase("standing");
    setRepScores([]);
    setLiveScore(null);
  }, []);

  // Request camera stream
  async function startCamera() {
    if (cameraState === "requesting") return;
    setErrorMsg(null);
    setCameraState("requesting");
    resetScoring();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: "user",
        },
        audio: false,
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          if (videoRef.current) {
            const width = videoRef.current.videoWidth;
            const height = videoRef.current.videoHeight;
            if (width && height) {
              setAspectRatio(width / height);
            }
            videoRef.current.play();
          }
          setCameraState("active");
          startProcessingLoop();
        };
      }
    } catch (err: any) {
      console.error("Camera access error:", err);
      setCameraState("error");
      setErrorMsg(
        err.name === "NotAllowedError"
          ? "Camera permission denied. Please enable camera access in your browser settings."
          : `Failed to open camera: ${err.message}`
      );
    }
  }

  // Stop camera stream
  function stopCamera() {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
      videoRef.current.srcObject = null;
    }

    setCameraState("idle");
    setFps(0);
    
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext("2d");
      ctx?.clearRect(0, 0, canvas.width, canvas.height);
    }
  }

  // Video processing loop
  function startProcessingLoop() {
    let lastVideoTime = -1;

    function processFrame() {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const poseLandmarker = poseLandmarkerRef.current;

      if (!video || !canvas || !poseLandmarker || video.paused) {
        animationFrameRef.current = requestAnimationFrame(processFrame);
        return;
      }

      if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
      }

      const timestamp = performance.now();
      
      // Calculate FPS
      frameCountRef.current++;
      if (timestamp - lastFpsUpdateRef.current >= 1000) {
        setFps(Math.round((frameCountRef.current * 1000) / (timestamp - lastFpsUpdateRef.current)));
        frameCountRef.current = 0;
        lastFpsUpdateRef.current = timestamp;
      }

      if (video.currentTime !== lastVideoTime) {
        lastVideoTime = video.currentTime;
        
        try {
          const results = poseLandmarker.detectForVideo(video, timestamp);
          const ctx = canvas.getContext("2d");
          
          if (ctx && results && results.landmarks && results.landmarks[0]) {
            const landmarks: Landmark[] = results.landmarks[0];
            
            // Calculate joint angles
            const lElbow = getElbowAngle(landmarks, "left");
            const rElbow = getElbowAngle(landmarks, "right");
            const lHip = getHipAngle(landmarks, "left");
            const rHip = getHipAngle(landmarks, "right");
            const lShoulder = getShoulderAngle(landmarks, "left");
            const rShoulder = getShoulderAngle(landmarks, "right");
            const lKnee = getKneeAngle(landmarks, "left");
            const rKnee = getKneeAngle(landmarks, "right");
            const lean = calculateTorsoLean(landmarks);

            setAngles({
              leftElbow: Math.round(lElbow),
              rightElbow: Math.round(rElbow),
              leftHip: Math.round(lHip),
              rightHip: Math.round(rHip),
              leftShoulder: Math.round(lShoulder),
              rightShoulder: Math.round(rShoulder),
              leftKnee: Math.round(lKnee),
              rightKnee: Math.round(rKnee),
            });
            setTorsoLean(Math.round(lean));

            // --- Rep counter update ---
            const avgKnee = (lKnee + rKnee) / 2;
            const { state: newState, repCompleted } = updateRepCounter(
              repCounterRef.current,
              avgKnee,
              timestamp
            );
            repCounterRef.current = newState;
            setCurrentPhase(newState.phase);

            // Collect frames for grading
            const frameData = extractSquatFrame(landmarks);
            repFramesRef.current.push(frameData);

            if (repCompleted) {
              // Grade the completed rep
              const score = gradeSquatRep(repFramesRef.current);
              setRepScores(prev => [...prev, score]);
              setRepCount(newState.repCount);
              setLiveScore(score.total);
              
              // Audio coaching
              if (window.speechSynthesis) {
                if (score.faults.length > 0) {
                  // Announce the most critical fault
                  const utterance = new SpeechSynthesisUtterance(faultLabel(score.faults[0]));
                  utterance.rate = 1.1;
                  window.speechSynthesis.speak(utterance);
                }
              }

              // Reset frame buffer for next rep
              repFramesRef.current = [];
            }

            // Draw Skeleton
            drawPoseOverlay(ctx, landmarks, canvas.width, canvas.height);
          } else if (ctx) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
          }
        } catch (detectErr) {
          console.error("Detection error:", detectErr);
        }
      }

      animationFrameRef.current = requestAnimationFrame(processFrame);
    }

    lastFpsUpdateRef.current = performance.now();
    frameCountRef.current = 0;
    animationFrameRef.current = requestAnimationFrame(processFrame);
  }

  // Draw skeleton connections, joint hubs, and text callouts on canvas
  function drawPoseOverlay(
    ctx: CanvasRenderingContext2D,
    landmarks: Landmark[],
    width: number,
    height: number
  ) {
    ctx.clearRect(0, 0, width, height);

    // 1. Draw connection bones
    ctx.strokeStyle = "rgba(0, 0, 0, 0.35)";
    ctx.lineWidth = 3;
    for (const [startIdx, endIdx] of POSE_CONNECTIONS) {
      const start = landmarks[startIdx];
      const end = landmarks[endIdx];
      
      if (start && end && (start.visibility ?? 0) > 0.5 && (end.visibility ?? 0) > 0.5) {
        ctx.beginPath();
        ctx.moveTo(start.x * width, start.y * height);
        ctx.lineTo(end.x * width, end.y * height);
        ctx.stroke();
      }
    }

    // 2. Draw joint points — highlight squat-critical joints (hips, knees, ankles, heels, toes)
    const squatKeyJoints = [23, 24, 25, 26, 27, 28, 29, 30, 31, 32]; // hips, knees, ankles, heels, toes
    const secondaryJoints = [11, 12]; // shoulders (for torso lean reference)
    
    for (const [idx, lm] of landmarks.entries()) {
      if (lm && (lm.visibility ?? 0) > 0.5) {
        const isSquatKey = squatKeyJoints.includes(idx);
        const isSecondary = secondaryJoints.includes(idx);
        ctx.beginPath();
        ctx.arc(lm.x * width, lm.y * height, isSquatKey ? 7 : isSecondary ? 5 : 3, 0, 2 * Math.PI);
        ctx.fillStyle = isSquatKey
          ? "oklch(0.50 0.16 162)" // emerald for squat-critical
          : isSecondary
          ? "oklch(0.50 0.14 250)" // blue for reference
          : "rgba(0, 0, 0, 0.75)";
        ctx.fill();
        ctx.strokeStyle = "white";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // 3. Draw live angle text callouts on key joints
        if (isSquatKey || isSecondary) {
          ctx.save();
          
          if (isMirrored) {
            ctx.translate(lm.x * width, lm.y * height);
            ctx.scale(-1, 1);
            ctx.translate(-lm.x * width, -lm.y * height);
          }

          let angleText = "";
          if (idx === 23) angleText = `L Hip: ${Math.round(getHipAngle(landmarks, "left"))}°`;
          if (idx === 24) angleText = `R Hip: ${Math.round(getHipAngle(landmarks, "right"))}°`;
          if (idx === 25) angleText = `L Knee: ${Math.round(getKneeAngle(landmarks, "left"))}°`;
          if (idx === 26) angleText = `R Knee: ${Math.round(getKneeAngle(landmarks, "right"))}°`;

          if (angleText) {
            ctx.font = "bold 11px monospace";
            ctx.fillStyle = "oklch(0.13 0 0)";
            ctx.shadowColor = "white";
            ctx.shadowBlur = 4;
            ctx.fillText(angleText, lm.x * width + 10, lm.y * height - 5);
          }
          ctx.restore();
        }
      }
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  // Compute average score
  const avgScore = repScores.length > 0
    ? Math.round(repScores.reduce((sum, s) => sum + s.total, 0) / repScores.length)
    : null;

  return (
    <main className="min-h-screen bg-background px-6 py-10">
      <div className="mx-auto max-w-6xl">
        
        {/* Header */}
        <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-6">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground">
              § Biomechanical visualizer
            </p>
            <h1
              style={{ fontFamily: "var(--font-serif)" }}
              className="mt-3 text-4xl leading-tight tracking-tight"
            >
              Squat Analysis
            </h1>
            <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
              Real-time squat form grading with rep counting, depth analysis, and bilateral symmetry tracking.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="font-mono text-xs text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5 border border-border rounded"
            >
              ← Dashboard
            </Link>
          </div>
        </header>

        {/* Error Notice */}
        {errorMsg && (
          <div className="mb-6 rounded border border-red-200 bg-red-50 p-4">
            <p className="font-mono text-xs text-red-700">{errorMsg}</p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          
          {/* Left Column: Video & Overlay (8 Cols) */}
          <div className="lg:col-span-8 flex flex-col gap-4">
            
            <div 
              style={{ aspectRatio }}
              className="relative w-full rounded border border-border bg-card overflow-hidden shadow-inner flex items-center justify-center"
            >
              
              {/* HTML5 Video element */}
              <video
                ref={videoRef}
                playsInline
                muted
                className={`absolute inset-0 h-full w-full object-cover transition-transform duration-200 ${
                  isMirrored ? "-scale-x-100" : ""
                }`}
              />

              {/* Overlay Canvas */}
              <canvas
                ref={canvasRef}
                className={`absolute inset-0 h-full w-full object-cover pointer-events-none transition-transform duration-200 ${
                  isMirrored ? "-scale-x-100" : ""
                }`}
              />

              {/* Idle screen state */}
              {cameraState === "idle" && (
                <div className="absolute z-10 text-center px-6">
                  <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-muted border border-border">
                    <span className="font-mono text-xs text-muted-foreground">CAM</span>
                  </div>
                  <h3 className="font-medium text-sm text-foreground">Camera feed inactive</h3>
                  <p className="text-xs text-muted-foreground mt-1 max-w-xs mx-auto">
                    Start your camera feed to begin real-time skeleton projection and squat analysis.
                  </p>
                  <button
                    disabled={modelState === "loading"}
                    onClick={startCamera}
                    className="mt-5 inline-flex items-center gap-2 rounded bg-foreground px-5 py-2.5 font-mono text-xs text-background hover:opacity-90 disabled:opacity-50 transition-opacity"
                  >
                    Start Camera Stream
                  </button>
                </div>
              )}

              {/* Requesting camera state */}
              {cameraState === "requesting" && (
                <div className="absolute z-10 text-center">
                  <span className="inline-block h-6 w-6 rounded-full border-2 border-muted border-t-foreground animate-spin mb-3" />
                  <p className="font-mono text-xs text-muted-foreground">Requesting camera device access…</p>
                </div>
              )}

              {/* Model Loading Screen */}
              {modelState === "loading" && cameraState === "active" && (
                <div className="absolute inset-0 bg-background/90 z-10 flex flex-col items-center justify-center text-center px-6">
                  <span className="inline-block h-6 w-6 rounded-full border-2 border-muted border-t-foreground animate-spin mb-3" />
                  <p className="font-mono text-xs text-foreground">Initializing MediaPipe Pose Engine…</p>
                  <p className="font-mono text-[10px] text-muted-foreground mt-1">
                    Loading float16 model assets (float16/1/pose_landmarker_full.task)
                  </p>
                </div>
              )}

              {/* Live score overlay (top-left corner) */}
              {cameraState === "active" && liveScore !== null && (
                <div className="absolute top-4 left-4 z-10">
                  <div className={`rounded border px-4 py-3 ${scoreBg(liveScore)} backdrop-blur-sm`}>
                    <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Last Rep</p>
                    <p className={`font-mono text-3xl font-bold tabular-nums ${scoreColor(liveScore)}`}>
                      {liveScore}
                    </p>
                  </div>
                </div>
              )}

              {/* Rep counter overlay (top-right corner) */}
              {cameraState === "active" && (
                <div className="absolute top-4 right-4 z-10">
                  <div className="rounded border border-border bg-card/90 backdrop-blur-sm px-4 py-3 text-center">
                    <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Reps</p>
                    <p className="font-mono text-3xl font-bold tabular-nums text-foreground">
                      {repCount}
                    </p>
                  </div>
                </div>
              )}

              {/* Phase indicator (bottom-center) */}
              {cameraState === "active" && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10">
                  <div className="rounded-full border border-border bg-card/90 backdrop-blur-sm px-4 py-1.5">
                    <span className={`font-mono text-[10px] font-semibold tracking-wider ${phaseColor(currentPhase)}`}>
                      {phaseLabel(currentPhase)}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Video Control Bar */}
            {cameraState === "active" && (
              <div className="flex flex-wrap items-center justify-between gap-4 border border-border rounded bg-card px-4 py-3">
                <div className="flex items-center gap-3">
                  <button
                    onClick={stopCamera}
                    className="rounded border border-border px-3 py-1.5 font-mono text-[10px] hover:bg-muted transition-colors text-red-700 border-red-200 bg-red-50"
                  >
                    Stop Feed
                  </button>
                  <button
                    onClick={() => setIsMirrored(!isMirrored)}
                    className="rounded border border-border px-3 py-1.5 font-mono text-[10px] hover:bg-muted transition-colors text-muted-foreground"
                  >
                    {isMirrored ? "Disable Mirroring" : "Mirror Video"}
                  </button>
                  <button
                    onClick={resetScoring}
                    className="rounded border border-border px-3 py-1.5 font-mono text-[10px] hover:bg-muted transition-colors text-muted-foreground"
                  >
                    Reset Scores
                  </button>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="font-mono text-[10px] text-muted-foreground uppercase">
                      Live Stream
                    </span>
                  </div>
                  <span className="font-mono text-[10px] text-muted-foreground border-l border-border pl-4">
                    FPS: <span className="text-foreground font-semibold tabular-nums">{fps}</span>
                  </span>
                </div>
              </div>
            )}

            {/* Rep Breakdown Panel */}
            {repScores.length > 0 && (
              <div className="rounded border border-border bg-card p-5">
                <div className="flex items-center justify-between mb-4">
                  <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                    Rep-by-Rep Breakdown
                  </p>
                  {avgScore !== null && (
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] text-muted-foreground">AVG:</span>
                      <span className={`font-mono text-sm font-bold tabular-nums ${scoreColor(avgScore)}`}>
                        {avgScore}
                      </span>
                    </div>
                  )}
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-mono">
                    <thead>
                      <tr className="text-muted-foreground text-[9px] uppercase tracking-wider border-b border-border">
                        <th className="text-left pb-2 pr-3">Rep</th>
                        <th className="text-right pb-2 px-3">Total</th>
                        <th className="text-right pb-2 px-3">Depth</th>
                        <th className="text-right pb-2 px-3">Hip</th>
                        <th className="text-right pb-2 px-3">Torso</th>
                        <th className="text-right pb-2 px-3">Sym.</th>
                        <th className="text-right pb-2 px-3">Min Knee</th>
                        <th className="text-left pb-2 pl-3">Faults</th>
                      </tr>
                    </thead>
                    <tbody className="tabular-nums">
                      {repScores.map((score, i) => (
                        <tr key={i} className="border-t border-border/50">
                          <td className="py-2 pr-3 text-muted-foreground">{i + 1}</td>
                          <td className={`py-2 px-3 text-right font-semibold ${scoreColor(score.total)}`}>
                            {score.total}
                          </td>
                          <td className="py-2 px-3 text-right text-foreground">{score.depthScore}/25</td>
                          <td className="py-2 px-3 text-right text-foreground">{score.hipKneeScore}/25</td>
                          <td className="py-2 px-3 text-right text-foreground">{score.torsoScore}/25</td>
                          <td className="py-2 px-3 text-right text-foreground">{score.symmetryScore}/25</td>
                          <td className="py-2 px-3 text-right text-foreground">{Math.round(score.minKneeAngle)}°</td>
                          <td className="py-2 pl-3 text-left text-red-700">
                            {score.faults.length === 0
                              ? <span className="text-emerald-700">—</span>
                              : score.faults.map(f => faultLabel(f)).join(", ")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

          </div>

          {/* Right Column: Biomechanics Telemetry (4 Cols) */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            
            {/* System Status */}
            <div className="rounded border border-border bg-card p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-4">
                System Status
              </p>
              <div className="space-y-3 font-mono text-[11px]">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Detection Engine:</span>
                  <span className={modelState === "ready" ? "text-emerald-700" : modelState === "loading" ? "text-amber-700" : "text-red-700"}>
                    {modelState === "ready" ? "ACTIVE" : modelState === "loading" ? "INITIALIZING" : "ERROR"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Device Camera:</span>
                  <span className={cameraState === "active" ? "text-emerald-700" : "text-muted-foreground"}>
                    {cameraState === "active" ? "CAPTURING" : cameraState.toUpperCase()}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Rep Phase:</span>
                  <span className={phaseColor(currentPhase)}>
                    {phaseLabel(currentPhase)}
                  </span>
                </div>
                <div className="flex items-center justify-between border-t border-border pt-3 mt-3">
                  <span className="text-muted-foreground">Model Variant:</span>
                  <span className="text-foreground">LNDMRK_FULL_F16</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">GPU Acceleration:</span>
                  <span className="text-emerald-700">ENABLED</span>
                </div>
              </div>
            </div>

            {/* Joint Telemetry — Squat-focused */}
            <div className="rounded border border-border bg-card p-5 flex-1">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-4">
                Joint Telemetry
              </p>
              
              {cameraState !== "active" ? (
                <div className="h-48 flex items-center justify-center text-center">
                  <p className="text-xs text-muted-foreground max-w-[200px]">
                    Telemetry readings will appear once the camera feed and pose engine are active.
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  
                  {/* Knee Flexion — primary squat metric */}
                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <h3 className="text-xs font-semibold text-foreground">Knee Flexion</h3>
                      <span className="font-mono text-[10px] text-muted-foreground">hip-knee-ankle</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-background border border-border p-2.5 rounded text-center">
                        <p className="font-mono text-[9px] uppercase text-muted-foreground">Left Side</p>
                        <p className="font-mono text-base font-semibold text-foreground mt-1 tabular-nums">
                          {angles.leftKnee}°
                        </p>
                      </div>
                      <div className="bg-background border border-border p-2.5 rounded text-center">
                        <p className="font-mono text-[9px] uppercase text-muted-foreground">Right Side</p>
                        <p className="font-mono text-base font-semibold text-foreground mt-1 tabular-nums">
                          {angles.rightKnee}°
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Hip Angle */}
                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <h3 className="text-xs font-semibold text-foreground">Hip Angle</h3>
                      <span className="font-mono text-[10px] text-muted-foreground">shoulder-hip-knee</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-background border border-border p-2.5 rounded text-center">
                        <p className="font-mono text-[9px] uppercase text-muted-foreground">Left Side</p>
                        <p className="font-mono text-base font-semibold text-foreground mt-1 tabular-nums">
                          {angles.leftHip}°
                        </p>
                      </div>
                      <div className="bg-background border border-border p-2.5 rounded text-center">
                        <p className="font-mono text-[9px] uppercase text-muted-foreground">Right Side</p>
                        <p className="font-mono text-base font-semibold text-foreground mt-1 tabular-nums">
                          {angles.rightHip}°
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Torso Lean */}
                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <h3 className="text-xs font-semibold text-foreground">Torso Lean</h3>
                      <span className="font-mono text-[10px] text-muted-foreground">from vertical</span>
                    </div>
                    <div className="bg-background border border-border p-2.5 rounded text-center">
                      <p className="font-mono text-[9px] uppercase text-muted-foreground">Angle</p>
                      <p className={`font-mono text-base font-semibold mt-1 tabular-nums ${
                        torsoLean >= 15 && torsoLean <= 45
                          ? "text-emerald-700"
                          : torsoLean > 50
                          ? "text-red-700"
                          : "text-amber-700"
                      }`}>
                        {torsoLean}°
                      </p>
                      <p className="font-mono text-[9px] text-muted-foreground mt-1">
                        optimal: 15°–45°
                      </p>
                    </div>
                  </div>

                  {/* Bilateral Symmetry */}
                  <div>
                    <div className="flex justify-between items-baseline mb-2">
                      <h3 className="text-xs font-semibold text-foreground">Bilateral Symmetry</h3>
                      <span className="font-mono text-[10px] text-muted-foreground">L/R knee Δ</span>
                    </div>
                    <div className="bg-background border border-border p-2.5 rounded text-center">
                      <p className="font-mono text-[9px] uppercase text-muted-foreground">Knee Difference</p>
                      <p className={`font-mono text-base font-semibold mt-1 tabular-nums ${
                        Math.abs(angles.leftKnee - angles.rightKnee) < 5
                          ? "text-emerald-700"
                          : Math.abs(angles.leftKnee - angles.rightKnee) < 10
                          ? "text-amber-700"
                          : "text-red-700"
                      }`}>
                        {Math.abs(angles.leftKnee - angles.rightKnee)}°
                      </p>
                      <p className="font-mono text-[9px] text-muted-foreground mt-1">
                        target: &lt; 5° difference
                      </p>
                    </div>
                  </div>

                </div>
              )}
            </div>

            {/* Squat Calibration Rules */}
            <div className="rounded border border-border bg-card p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3">
                Squat Calibration Rules
              </p>
              <ul className="text-xs text-muted-foreground space-y-2 list-disc list-inside">
                <li>Position phone 2–3 meters away at hip height.</li>
                <li>Ensure strict profile side view (sagittal plane).</li>
                <li>Keep entire body (feet to head) in frame.</li>
                <li>Descend until thighs are parallel (knee flexion ≤ 90°).</li>
                <li>Maintain upright torso (lean 15°–45° from vertical).</li>
                <li>Knees should track over toes, not cave inward.</li>
                <li>Heels remain planted throughout the movement.</li>
              </ul>
            </div>

          </div>

        </div>

      </div>
    </main>
  );
}
