"use client";

import { useState, useRef, useEffect } from "react";

export function LiveRecorder({
  onRecordingComplete,
  onCancel,
}: {
  onRecordingComplete: (file: File) => void;
  onCancel: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);

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
        setHasPermission(true);
      } catch (err) {
        console.error("Camera access denied or failed", err);
        setHasPermission(false);
      }
    }

    setupCamera();

    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  useEffect(() => {
    if (!isRecording) return;
    setRecordingTime(0);
    const interval = setInterval(() => setRecordingTime((t) => t + 1), 1000);
    return () => clearInterval(interval);
  }, [isRecording]);

  function startRecording() {
    if (!videoRef.current?.srcObject) return;
    const stream = videoRef.current.srcObject as MediaStream;
    
    // Choose a supported mime type
    const options = { mimeType: "video/webm;codecs=vp8,opus" };
    const mimeType = MediaRecorder.isTypeSupported(options.mimeType) ? options.mimeType : "video/webm";
    
    const mediaRecorder = new MediaRecorder(stream, { mimeType });
    mediaRecorderRef.current = mediaRecorder;
    chunksRef.current = [];

    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        chunksRef.current.push(e.data);
      }
    };

    mediaRecorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: mimeType });
      const file = new File([blob], `live-recording-${Date.now()}.webm`, { type: mimeType });
      onRecordingComplete(file);
    };

    mediaRecorder.start();
    setIsRecording(true);
  }

  function stopRecording() {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }

  function formatTime(s: number) {
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  }

  if (hasPermission === false) {
    return (
      <div className="rounded border border-red-200 bg-red-50 p-4 text-center">
        <p className="text-sm text-red-800">Camera access denied.</p>
        <button type="button" onClick={onCancel} className="mt-2 text-xs font-semibold text-red-900 underline">
          Go back
        </button>
      </div>
    );
  }

  return (
    <div className="relative rounded overflow-hidden bg-black border border-border">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-full aspect-video object-cover"
      />
      
      {hasPermission === null && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <p className="text-sm font-mono text-muted-foreground animate-pulse">Requesting camera...</p>
        </div>
      )}

      <div className="absolute bottom-4 inset-x-0 flex justify-center items-center gap-4">
        {isRecording ? (
          <div className="flex items-center gap-3 bg-background/80 backdrop-blur px-4 py-2 rounded-full">
            <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
            <span className="font-mono text-xs text-foreground w-12">{formatTime(recordingTime)}</span>
            <button
              type="button"
              onClick={stopRecording}
              className="rounded bg-red-600 px-3 py-1 text-xs font-semibold text-white hover:bg-red-700"
            >
              Stop
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onCancel}
              className="rounded-full bg-background/80 backdrop-blur px-4 py-2 text-xs font-medium text-foreground hover:bg-background"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={startRecording}
              disabled={hasPermission === null}
              className="rounded-full bg-red-600 px-4 py-2 text-xs font-semibold text-white shadow hover:bg-red-700 disabled:opacity-50"
            >
              Record
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
