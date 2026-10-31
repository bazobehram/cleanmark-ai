export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
  label?: string;
}

export type AspectRatioType = 'original' | '9:16' | '4:5' | '1:1' | '16:9';
export type FramingModeType = 'blur_background' | 'crop_center' | 'pad_black';
export type CleaningMethodType = 'telea' | 'delogo';

export interface UploadResponse {
  file_id: string;
  filename: string;
  is_video: boolean;
  width: number;
  height: number;
  preview_url: string;
  original_url: string;
  suggested_boxes?: Box[];
}

export interface ProcessResponse {
  success: boolean;
  processed_file_id: string;
  is_video: boolean;
  target_ratio: string;
  cleaned_url: string;
  filename: string;
  download_url: string;
}

export interface TaskStatusResponse {
  task_id: string;
  file_id?: string;
  status: 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  step: string;
  error?: string | null;
  result?: ProcessResponse | null;
}

