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
  currentAnalysis: null,
  activeFrame: 0,
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
      currentAnalysis: null,
      activeFrame: 0,
      isPlaying: false,
      activeTab: 'overview',
      multiCamAngle: 'grid',
      userRole: 'coach',
      telestratorTool: 'none',
      showAnatomicalPlanes: true,
    }),
}));
