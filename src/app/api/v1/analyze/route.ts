import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const analysisType = searchParams.get("analysis_type") || "full";

    const formData = await request.formData().catch(() => null);
    const file = formData ? (formData.get("video") as File | null) : null;

    const fileSizeMb = file ? Number((file.size / (1024 * 1024)).toFixed(2)) : 12.5;
    const videoId = "analysis-" + Math.random().toString(36).substring(2, 9);

    const mockResult = {
      video_id: videoId,
      analysis_type: analysisType,
      metadata: {
        width: 1920,
        height: 1080,
        fps: 30,
        total_frames: 180,
        duration: 6.0,
        file_size_mb: fileSizeMb,
      },
      analysis: {
        overview: {
          video_id: videoId,
          analysis_type: analysisType,
          duration: 6.0,
          frames_analyzed: 180,
          total_frames: 180,
          coverage: 100,
        },
        joint_analysis: [
          { joint: "left_knee", mean_angle: 92.4, range_of_motion: 64.2, stability: 92.1, status: "normal", normal_range: "0° - 150°" },
          { joint: "right_knee", mean_angle: 91.8, range_of_motion: 63.8, stability: 93.4, status: "normal", normal_range: "0° - 150°" },
          { joint: "left_hip", mean_angle: 104.2, range_of_motion: 48.5, stability: 88.6, status: "normal", normal_range: "0° - 120°" },
          { joint: "right_hip", mean_angle: 103.9, range_of_motion: 47.9, stability: 89.1, status: "normal", normal_range: "0° - 120°" },
          { joint: "left_elbow", mean_angle: 142.1, range_of_motion: 28.4, stability: 95.0, status: "normal", normal_range: "0° - 150°" },
          { joint: "right_elbow", mean_angle: 141.5, range_of_motion: 29.1, stability: 94.8, status: "normal", normal_range: "0° - 150°" },
        ],
        posture_report: {
          grade: "Excellent",
          score: 94.2,
          description: "Outstanding postural alignment with symmetrical joint tracking.",
          consistency: 91.5,
          score_range: { min: 88.0, max: 97.5 },
        },
        recommendations: [
          "Optimal knee flexion angles detected during maximum depth phase.",
          "Slight asymmetry detected in hip extension during ascending phase.",
          "Maintain core stability to sustain dynamic posture scores under load.",
        ],
      },
      frame_analyses: Array.from({ length: 180 }, (_, i) => ({
        frame_number: i,
        timestamp: Number((i / 30).toFixed(2)),
        joint_angles: {
          left_knee: { angle: 90 + Math.sin(i / 10) * 30, confidence: 0.95 },
          right_knee: { angle: 90 + Math.sin(i / 10) * 30, confidence: 0.94 },
        },
        posture_metrics: {
          overall_score: 94.2,
          head_tilt: 1.2,
          shoulder_alignment: 0.8,
          hip_alignment: 0.5,
        },
        landmarks: {
          LEFT_SHOULDER: { x: 0.4, y: 0.3, z: 0, visibility: 0.9 },
          RIGHT_SHOULDER: { x: 0.6, y: 0.3, z: 0, visibility: 0.9 },
          LEFT_HIP: { x: 0.42, y: 0.6, z: 0, visibility: 0.9 },
          RIGHT_HIP: { x: 0.58, y: 0.6, z: 0, visibility: 0.9 },
          LEFT_KNEE: { x: 0.41, y: 0.8, z: 0, visibility: 0.9 },
          RIGHT_KNEE: { x: 0.59, y: 0.8, z: 0, visibility: 0.9 },
          LEFT_ANKLE: { x: 0.42, y: 0.95, z: 0, visibility: 0.9 },
          RIGHT_ANKLE: { x: 0.58, y: 0.95, z: 0, visibility: 0.9 },
        },
      })),
    };

    return NextResponse.json(mockResult);
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || "Failed to analyze video" },
      { status: 500 }
    );
  }
}
