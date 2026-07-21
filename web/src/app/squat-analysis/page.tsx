"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function SquatAnalysisPage() {
  const [videos, setVideos] = useState<{ cam1: File | null; cam2: File | null; cam3: File | null }>({
    cam1: null,
    cam2: null,
    cam3: null,
  });
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleFileChange = (cam: keyof typeof videos) => (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setVideos((prev) => ({ ...prev, [cam]: e.target.files![0] }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!videos.cam1 || !videos.cam2 || !videos.cam3) {
      alert("Please upload all 3 camera angles.");
      return;
    }

    setIsUploading(true);
    setResult(null);

    const formData = new FormData();
    formData.append("cam1", videos.cam1);
    formData.append("cam2", videos.cam2);
    formData.append("cam3", videos.cam3);

    try {
      const res = await fetch("/api/squat-analysis", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error("Upload failed");
      }

      const data = await res.json();
      setResult(data);
    } catch (error) {
      console.error(error);
      alert("Failed to submit videos.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="container mx-auto max-w-4xl py-12 px-4">
      <h1 className="text-4xl font-bold mb-8">Squat Analysis</h1>

      <Card className="p-6 mb-8 bg-secondary/20">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-3">
              <Label htmlFor="cam1">Camera 1 (Front/Angle)</Label>
              <Input
                id="cam1"
                type="file"
                accept="video/*"
                onChange={handleFileChange("cam1")}
                className="file:text-foreground file:bg-secondary cursor-pointer"
              />
            </div>
            
            <div className="space-y-3">
              <Label htmlFor="cam2">Camera 2 (Side)</Label>
              <Input
                id="cam2"
                type="file"
                accept="video/*"
                onChange={handleFileChange("cam2")}
                className="file:text-foreground file:bg-secondary cursor-pointer"
              />
            </div>
            
            <div className="space-y-3">
              <Label htmlFor="cam3">Camera 3 (Back/Angle)</Label>
              <Input
                id="cam3"
                type="file"
                accept="video/*"
                onChange={handleFileChange("cam3")}
                className="file:text-foreground file:bg-secondary cursor-pointer"
              />
            </div>
          </div>

          <Button type="submit" disabled={isUploading} className="w-full">
            {isUploading ? "Uploading..." : "Submit for Analysis"}
          </Button>
        </form>
      </Card>

      <div className="mt-12">
        <h2 className="text-2xl font-semibold mb-4">Results Area</h2>
        <div className="border border-dashed border-border rounded-lg p-12 min-h-[400px] flex items-center justify-center bg-secondary/5">
          {result ? (
            <div className="text-center">
              <p className="text-emerald-500 font-medium mb-2">Analysis Complete (Placeholder)</p>
              <pre className="text-xs text-left bg-background p-4 rounded-md overflow-auto max-w-full">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          ) : (
            <div className="text-center text-muted-foreground">
              <p>3D model viewer and form-feedback metrics will appear here.</p>
              <p className="text-sm mt-2">Waiting for video submission...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
