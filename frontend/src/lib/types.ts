export type RunStatus = "pending" | "processing" | "completed" | "failed";

export interface Event {
  type: "fatigue" | "overstride" | string;
  frame: number;
  time_sec: number;
}

export interface MetricsSummary {
  cadence: number;
  stride_length: number;
  vertical_oscillation: number;
  symmetry_score: number;
  fatigue_frame: number | null;
  fatigue_time_sec: number | null;
  overstriding_count: number;
  events: Event[];
}

export interface TimeSeriesPoint {
  frame: number;
  time_sec: number;
  value: number;
}

export interface RunResult {
  run_id: string;
  status: RunStatus;
  metadata: {
    fps?: number;
    total_frames?: number;
    width?: number;
    height?: number;
    duration_sec?: number;
  };
  metrics: MetricsSummary | null;
  insights: string[];
  cadence_over_time: TimeSeriesPoint[];
  hip_y_over_time: TimeSeriesPoint[];
  left_ankle_y_over_time: TimeSeriesPoint[];
  right_ankle_y_over_time: TimeSeriesPoint[];
  annotated_video_ready: boolean;
  error?: string | null;
}
