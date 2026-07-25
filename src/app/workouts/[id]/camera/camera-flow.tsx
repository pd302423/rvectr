"use client";

import { useState, useRef, useEffect } from "react";
import { toast } from "sonner";
import { createClient } from "@/lib/supabase/client";

export type ExerciseRow = {
  id: string;
  name: string;
  slug: string;
  order_index: number;
  rest_seconds_min?: number;
};

// --- XHR Upload function from record-submit ---
function uploadFileWithXhr(
  file: File,
  storagePath: string,
  token: string,
  onProgress: (percent: number) => void
): Promise<string> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    if (!supabaseUrl) return reject(new Error("Supabase URL is not configured."));
    const uploadUrl = `${supabaseUrl}/storage/v1/object/assessment-videos/${storagePath}`;
    xhr.open("POST", uploadUrl, true);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.setRequestHeader("apikey", process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!);
    xhr.setRequestHeader("Content-Type", file.type || "video/mp4");
    xhr.setRequestHeader("x-upsert", "true");
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status === 200 || xhr.status === 201) resolve(storagePath);
      else reject(new Error(`Upload failed with status ${xhr.status}`));
    };
    xhr.onerror = () => reject(new Error("Network connection error."));
    xhr.send(file);
  });
}

export function CameraFlow({
  exercises,
  submitAction,
}: {
  exercises: ExerciseRow[];
  submitAction: (videoPaths: Record<string, string>) => Promise<never> | Promise<void>;
}) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [files, setFiles] = useState<Record<string, File>>({});
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Rest state
  const [isResting, setIsResting] = useState(false);
  const [restTimeLeft, setRestTimeLeft] = useState(0);

  const [facingMode, setFacingMode] = useState<"user" | "environment">("user");

  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const currentExercise = exercises[currentIndex];
  const isFinished = currentIndex >= exercises.length;

  useEffect(() => {
    let stream: MediaStream | null = null;
    async function setupCamera() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode },
          audio: true,
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        console.error("Camera access failed", err);
        toast.error("Please allow camera access to begin the assessment.");
      }
    }
    setupCamera();
    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, [facingMode]);

  function toggleCamera() {
    setFacingMode((prev) => (prev === "user" ? "environment" : "user"));
  }

  // Timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRecording) {
      interval = setInterval(() => setRecordingTime((t) => t + 1), 1000);
    } else {
      setRecordingTime(0);
    }
    return () => clearInterval(interval);
  }, [isRecording]);

  // Audio cues
  useEffect(() => {
    if (!isFinished && currentExercise && !isRecording && !isUploading && !isResting) {
      speak(`Get ready for ${currentExercise.name}. Tap start when you are in position.`);
    }
  }, [currentIndex, isFinished, isRecording, isUploading, isResting, currentExercise]);

  function speak(text: string) {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  }

  // Timer for Rest
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isResting && restTimeLeft > 0) {
      interval = setInterval(() => setRestTimeLeft((t) => t - 1), 1000);
    } else if (isResting && restTimeLeft <= 0) {
      finishRest();
    }
    return () => clearInterval(interval);
  }, [isResting, restTimeLeft]);

  function finishRest() {
    setIsResting(false);
    setCurrentIndex((i) => i + 1);
  }

  function startRecording() {
    if (!videoRef.current?.srcObject) return;
    const stream = videoRef.current.srcObject as MediaStream;
    const options = { mimeType: "video/webm;codecs=vp8,opus" };
    const mimeType = MediaRecorder.isTypeSupported(options.mimeType) ? options.mimeType : "video/webm";
    
    const mediaRecorder = new MediaRecorder(stream, { mimeType });
    mediaRecorderRef.current = mediaRecorder;
    chunksRef.current = [];

    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
    };

    mediaRecorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: mimeType });
      const file = new File([blob], `${currentExercise.slug}-${Date.now()}.webm`, { type: mimeType });
      setFiles((prev) => ({ ...prev, [currentExercise.id]: file }));
      
      if (currentIndex < exercises.length - 1) {
        setIsResting(true);
        setRestTimeLeft(currentExercise.rest_seconds_min || 300);
        speak(`Test complete. Rest for ${Math.floor((currentExercise.rest_seconds_min || 300) / 60)} minutes.`);
      } else {
        speak("Assessment complete. Uploading videos.");
        setCurrentIndex((i) => i + 1);
        handleFinalUpload(file); // trigger upload automatically for the last one
      }
    };

    mediaRecorder.start();
    setIsRecording(true);
    speak("Recording started. Begin.");
  }

  function stopRecording() {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setFiles((prev) => ({ ...prev, [currentExercise.id]: file }));
    
    if (currentIndex < exercises.length - 1) {
      setIsResting(true);
      setRestTimeLeft(currentExercise.rest_seconds_min || 300);
      speak(`Test complete. Rest for ${Math.floor((currentExercise.rest_seconds_min || 300) / 60)} minutes.`);
    } else {
      speak("Assessment complete. Uploading videos.");
      setCurrentIndex((i) => i + 1);
      handleFinalUpload(file);
    }
  }

  async function handleFinalUpload(lastFile?: File) {
    setIsUploading(true);
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      toast.error("Session expired.");
      return;
    }
    const token = session.access_token;
    const userId = session.user.id;
    const uploadedPaths: Record<string, string> = {};

    let totalUploaded = 0;
    try {
      await Promise.all(
        exercises.map(async (ex) => {
          const file = files[ex.id] || (ex.id === currentExercise?.id ? lastFile : null);
          if (!file) return;
          const storagePath = `${userId}/${ex.id}.webm`;
          await uploadFileWithXhr(file, storagePath, token, () => {});
          uploadedPaths[ex.id] = storagePath;
          totalUploaded++;
          setUploadProgress(Math.round((totalUploaded / exercises.length) * 100));
        })
      );
      toast.success("Assessment submitted!");
      await submitAction(uploadedPaths);
    } catch (err: any) {
      toast.error("Upload failed: " + err.message);
      setIsUploading(false);
    }
  }

  if (isFinished) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-6 text-center">
        <h2 className="text-3xl font-serif mb-4">Assessment Complete</h2>
        <p className="text-muted-foreground mb-8">You've recorded all tests. Upload them to the AI for grading.</p>
        
        {isUploading ? (
          <div className="w-full max-w-sm mx-auto">
            <div className="mb-2 text-sm">Uploading videos... {uploadProgress}%</div>
            <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
              <div className="h-full bg-white transition-all duration-300" style={{ width: `${uploadProgress}%` }} />
            </div>
          </div>
        ) : (
          <p className="text-muted-foreground animate-pulse">Initializing upload...</p>
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full flex flex-col bg-[#0a0a0a] text-white">
      {/* Top HUD */}
      <div className="p-6 pt-12 flex justify-between items-start">
        <div className="space-y-1">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-emerald-500">
            Assessment {currentIndex + 1} / {exercises.length}
          </p>
          <h1 className="text-2xl font-serif text-white tracking-tight">
            {currentExercise?.name}
          </h1>
        </div>
        <div className="flex gap-3">
          <button
            onClick={toggleCamera}
            className="flex items-center gap-2 text-xs font-medium text-gray-300 bg-white/5 hover:bg-white/10 border border-white/10 px-4 py-2 rounded-full transition-all"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.29 7.04 12 12.01 20.71 7.04"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
            Flip
          </button>
          <a href="." className="flex items-center text-xs font-medium text-gray-300 bg-white/5 hover:bg-white/10 border border-white/10 px-4 py-2 rounded-full transition-all">
            Exit
          </a>
        </div>
      </div>

      {/* Viewfinder Area */}
      <div className="flex-1 w-full px-6 flex flex-col justify-center items-center">
        <div className="relative w-full max-w-sm aspect-[3/4] sm:aspect-[9/16] rounded-[2rem] overflow-hidden bg-black border border-white/10 shadow-2xl ring-1 ring-white/5">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="absolute inset-0 w-full h-full object-cover"
          />
          
          {/* Viewfinder Guidelines */}
          <div className="absolute inset-6 border-2 border-dashed border-white/20 rounded-xl pointer-events-none mix-blend-overlay" />
          
          {/* Recording Indicator inside viewfinder */}
          {isRecording && (
            <div className="absolute top-4 right-4 flex items-center gap-2 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10">
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              <span className="text-red-500 font-mono text-xs tabular-nums font-semibold tracking-wider">
                {Math.floor(recordingTime / 60)}:{(recordingTime % 60).toString().padStart(2, "0")}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Controls */}
      <div className="p-8 pb-12 flex flex-col items-center">
        {isResting ? (
          <div className="flex flex-col items-center gap-6 w-full max-w-xs mx-auto">
            <p className="text-sm text-emerald-500 font-mono uppercase tracking-[0.15em] font-semibold text-center">Rest Period</p>
            <div className="text-white font-mono text-6xl tabular-nums tracking-tighter">
              {Math.floor(restTimeLeft / 60)}:{(restTimeLeft % 60).toString().padStart(2, "0")}
            </div>
            <button
              onClick={finishRest}
              className="mt-2 w-full bg-white text-black py-4 rounded-xl font-semibold text-[15px] active:scale-95 transition-all shadow-lg hover:bg-gray-100"
            >
              Skip Rest
            </button>
          </div>
        ) : isRecording ? (
          <div className="flex flex-col items-center gap-6">
            <button
              onClick={stopRecording}
              className="w-20 h-20 bg-red-500 rounded-full flex items-center justify-center ring-4 ring-red-500/20 active:scale-95 transition-all shadow-xl shadow-red-500/20"
            >
              <div className="w-8 h-8 bg-white rounded-md" />
            </button>
            <p className="text-xs text-gray-400 font-mono uppercase tracking-[0.2em]">Tap to Stop</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-6 w-full">
            <p className="text-center text-sm text-gray-400 max-w-[280px] leading-relaxed">
              Ensure your full body is visible within the frame guidelines.
            </p>
            <button
              onClick={startRecording}
              className="w-20 h-20 bg-transparent rounded-full flex items-center justify-center border-[3px] border-white active:scale-95 transition-all shadow-xl shadow-white/10"
            >
              <div className="w-[68px] h-[68px] bg-red-500 rounded-full" />
            </button>
            
            <div className="flex items-center gap-6 mt-2">
              <p className="text-xs text-gray-400 font-mono uppercase tracking-[0.2em]">Record</p>
              <div className="w-1 h-1 rounded-full bg-gray-700" />
              <label className="text-xs text-emerald-400 font-mono uppercase tracking-[0.2em] cursor-pointer hover:text-emerald-300 transition-colors">
                Upload File
                <input
                  type="file"
                  accept="video/*"
                  className="hidden"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                />
              </label>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
