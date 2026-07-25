import { create } from 'zustand';

export interface JointAngleData {
  angle: number;
  confidence: number;
}

export interface JointStatistic {
  joint: string;
  mean_angle: number;
  range_of_motion: number;
  stability: number;
  status: 'normal' | 'unstable' | 'abnormal';
  normal_range?: string;
  left_angle?: number;
  right_angle?: number;
  asymmetry_index?: number;
}

export interface PostureReport {
  grade: 'Excellent' | 'Good' | 'Fair' | 'Poor' | 'Critical';
  score: number;
  description: string;
  consistency: number;
  score_range: {
    min: number;
    max: number;
  };
}

export interface FrameAnalysisData {
  frame_number: number;
  timestamp: number;
  joint_angles: Record<string, JointAngleData>;
  posture_metrics?: {
    head_tilt?: number;
    shoulder_alignment?: number;
    hip_alignment?: number;
    overall_score?: number;
  };
  landmarks?: Record<string, { x: number; y: number; z: number; visibility: number }>;
  faults?: string[];
}

export interface VideoMetadata {
  width: number;
  height: number;
  fps: number;
  total_frames: number;
  duration: number;
  codec?: string;
  file_size_mb?: number;
}

export interface AnalysisResultData {
  video_id: string;
  analysis_type: string;
  metadata: VideoMetadata;
  analysis: {
    overview: {
      video_id: string;
      analysis_type: string;
      duration: number;
      frames_analyzed: number;
      total_frames: number;
      coverage: number;
    };
    joint_analysis: JointStatistic[];
    posture_report: PostureReport;
    recommendations: string[];
    raw_summary?: Record<string, unknown>;
  };
  frame_analyses?: FrameAnalysisData[];
}

export interface AthleteRecord {
  id: string;
  name: string;
  position: string;
  formScore: number;
  asymmetryIndex: number;
  status: 'optimal' | 'caution' | 'high_risk';
  lastAnalysisDate: string;
}

const mockDefaultAnalysis: AnalysisResultData = {
  video_id: "SQUAT_MULTIVIEW_01",
  analysis_type: "EasyMocap 3D Triangulation & SMPL Mesh Fitting",
  metadata: {
    width: 3840,
    height: 2160,
    fps: 30,
    total_frames: 291,
    duration: 9.7,
    codec: "H.264 / EasyMocap 3D",
    file_size_mb: 48.5,
  },
  analysis: {
    overview: {
      video_id: "SQUAT_MULTIVIEW_01",
      analysis_type: "Multi-View MoCap 3D Surface Reconstruction",
      duration: 9.7,
      frames_analyzed: 291,
      total_frames: 291,
      coverage: 100.0,
    },
    joint_analysis: [
      { joint: "Left Knee Flexion", mean_angle: 98.4, range_of_motion: 85.2, stability: 97.5, status: "normal", normal_range: "40° - 140°", left_angle: 45.2, right_angle: 46.1, asymmetry_index: 1.2 },
      { joint: "Right Knee Flexion", mean_angle: 97.8, range_of_motion: 84.8, stability: 96.8, status: "normal", normal_range: "40° - 140°", left_angle: 45.2, right_angle: 46.1, asymmetry_index: 1.2 },
      { joint: "Hip Extension / Hinge", mean_angle: 72.1, range_of_motion: 62.4, stability: 95.2, status: "normal", normal_range: "30° - 90°", left_angle: 68.4, right_angle: 69.1, asymmetry_index: 0.8 },
      { joint: "Spinal Forward Lean", mean_angle: 22.4, range_of_motion: 28.5, stability: 94.0, status: "normal", normal_range: "10° - 35°", left_angle: 22.1, right_angle: 22.1, asymmetry_index: 0.0 },
      { joint: "Ankle Dorsiflexion", mean_angle: 34.2, range_of_motion: 25.1, stability: 98.1, status: "normal", normal_range: "20° - 45°", left_angle: 32.5, right_angle: 33.1, asymmetry_index: 1.8 },
    ],
    posture_report: {
      grade: "Excellent",
      score: 94.8,
      description: "Parallel squat depth achieved with optimal lumbar neutrality, zero knee valgus collapse, and butter-smooth temporal acceleration curves.",
      consistency: 96.5,
      score_range: { min: 88, max: 98 },
    },
    recommendations: [
      "Maintain ankle dorsiflexion mobility during deep squat turnaround at Frame 107.",
      "Spinal forward lean angle (22.1°) is optimal for midfoot bar path balance.",
      "Bilateral knee flexion asymmetry is exceptionally low (1.2% delta).",
    ],
  },
  frame_analyses: Array.from({ length: 291 }, (_, i) => ({
    frame_number: i + 1,
    timestamp: i / 30.0,
    joint_angles: {
      left_knee: { angle: 160 - Math.sin((i / 291) * Math.PI) * 114.8, confidence: 0.98 },
      right_knee: { angle: 160 - Math.sin((i / 291) * Math.PI) * 113.9, confidence: 0.98 },
      left_hip: { angle: 175 - Math.sin((i / 291) * Math.PI) * 106.6, confidence: 0.97 },
      right_hip: { angle: 175 - Math.sin((i / 291) * Math.PI) * 105.9, confidence: 0.97 },
      spine: { angle: 5 + Math.sin((i / 291) * Math.PI) * 22.1, confidence: 0.99 },
    },
  })),
};

interface BiomechanicsStore {
  currentAnalysis: AnalysisResultData | null;
  activeFrame: number;
  isPlaying: boolean;
  activeTab: 'overview' | 'joints' | 'posture' | 'recommendations' | '3d' | 'asymmetry' | 'waveform';
  multiCamAngle: 'frontal' | 'sagittal' | 'diagonal' | 'grid';
  userRole: 'coach' | 'athlete';
  telestratorTool: 'none' | 'protractor' | 'ruler' | 'draw';
  showAnatomicalPlanes: boolean;

  // Actions
  setAnalysis: (data: AnalysisResultData) => void;
  setActiveFrame: (frameIndex: number) => void;
  togglePlay: () => void;
  setPlaying: (playing: boolean) => void;
  setActiveTab: (tab: 'overview' | 'joints' | 'posture' | 'recommendations' | '3d' | 'asymmetry' | 'waveform') => void;
  setMultiCamAngle: (angle: 'frontal' | 'sagittal' | 'diagonal' | 'grid') => void;
  setUserRole: (role: 'coach' | 'athlete') => void;
  setTelestratorTool: (tool: 'none' | 'protractor' | 'ruler' | 'draw') => void;
  toggleAnatomicalPlanes: () => void;
  reset: () => void;
}

export const useBiomechanicsStore = create<BiomechanicsStore>((set) => ({
  currentAnalysis: mockDefaultAnalysis,
  activeFrame: 106,
  isPlaying: false,
  activeTab: 'overview',
  multiCamAngle: 'grid',
  userRole: 'coach',
  telestratorTool: 'none',
  showAnatomicalPlanes: true,

  setAnalysis: (data) => set({ currentAnalysis: data, activeFrame: 0 }),
  setActiveFrame: (frameIndex) => set({ activeFrame: frameIndex }),
  togglePlay: () => set((state) => ({ isPlaying: !state.isPlaying })),
  setPlaying: (playing) => set({ isPlaying: playing }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setMultiCamAngle: (angle) => set({ multiCamAngle: angle }),
  setUserRole: (role) => set({ userRole: role }),
  setTelestratorTool: (tool) => set({ telestratorTool: tool }),
  toggleAnatomicalPlanes: () => set((state) => ({ showAnatomicalPlanes: !state.showAnatomicalPlanes })),
  reset: () =>
    set({
      currentAnalysis: mockDefaultAnalysis,
      activeFrame: 106,
      isPlaying: false,
      activeTab: 'overview',
      multiCamAngle: 'grid',
      userRole: 'coach',
      telestratorTool: 'none',
      showAnatomicalPlanes: true,
    }),
}));
