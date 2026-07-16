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
    xhr.setRequestHeader("Content-Type", file.type);
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

  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const currentExercise = exercises[currentIndex];
  const isFinished = currentIndex >= exercises.length;

  useEffect(() => {
    let stream: MediaStream | null = null;
    async function setupCamera() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
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
    };
  }, []);

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
    <div className="relative h-screen w-screen flex flex-col bg-black">
      {/* Background Camera */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="absolute inset-0 w-full h-full object-cover opacity-80"
      />
      
      {/* Top HUD */}
      <div className="relative z-10 p-6 pt-12 flex justify-between items-start bg-gradient-to-b from-black/80 to-transparent">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-wider text-gray-400">
            Test {currentIndex + 1} of {exercises.length}
          </p>
          <h1 className="text-3xl font-serif text-white mt-1 shadow-black drop-shadow-md">
            {currentExercise?.name}
          </h1>
        </div>
        <a href="." className="text-sm font-mono text-gray-400 bg-black/40 px-3 py-1.5 rounded-full backdrop-blur-md">
          Exit
        </a>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Bottom Controls */}
      <div className="relative z-10 p-8 pb-16 flex flex-col items-center bg-gradient-to-t from-black via-black/80 to-transparent">
        {isResting ? (
          <div className="flex flex-col items-center gap-6 w-full max-w-xs mx-auto">
            <p className="text-sm text-gray-300 font-mono uppercase tracking-wider text-center">Rest Period</p>
            <div className="text-white font-mono text-5xl tabular-nums drop-shadow-md">
              {Math.floor(restTimeLeft / 60)}:{(restTimeLeft % 60).toString().padStart(2, "0")}
            </div>
            <button
              onClick={finishRest}
              className="mt-4 w-full bg-white text-black py-4 rounded-full font-semibold text-lg active:scale-95 transition-transform"
            >
              Skip Rest
            </button>
          </div>
        ) : isRecording ? (
          <div className="flex flex-col items-center gap-6">
            <div className="text-red-500 font-mono text-xl tabular-nums animate-pulse">
              {Math.floor(recordingTime / 60)}:{(recordingTime % 60).toString().padStart(2, "0")}
            </div>
            <button
              onClick={stopRecording}
              className="w-24 h-24 bg-red-600 rounded-full flex items-center justify-center border-4 border-white/20 active:scale-95 transition-all"
            >
              <div className="w-8 h-8 bg-white rounded-sm" />
            </button>
            <p className="text-sm text-gray-400 mt-2 font-mono uppercase tracking-wider">Tap to Stop</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-6">
            <p className="text-center text-sm text-gray-300 max-w-[250px] mb-2 leading-relaxed">
              Step back into frame. The AI will monitor your movement.
            </p>
            <button
              onClick={startRecording}
              className="w-24 h-24 bg-white/10 rounded-full flex items-center justify-center border-4 border-white active:scale-95 transition-all"
            >
              <div className="w-20 h-20 bg-red-500 rounded-full" />
            </button>
            <p className="text-sm text-gray-400 mt-2 font-mono uppercase tracking-wider">Tap to Start</p>
          </div>
        )}
      </div>
    </div>
  );
}
