import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpEventType } from '@angular/common/http';
import { Box, UploadResponse, ProcessResponse, AspectRatioType, FramingModeType, CleaningMethodType, TaskStatusResponse } from '../models/cleaner.model';
import { Observable, tap, catchError, of } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class CleanerService {
  private http = inject(HttpClient);

  uploadedFile = signal<UploadResponse | null>(null);
  processedResult = signal<ProcessResponse | null>(null);
  isUploading = signal<boolean>(false);
  isProcessing = signal<boolean>(false);
  isDetecting = signal<boolean>(false);
  errorMessage = signal<string | null>(null);

  // İlerleme Yüzdeleri (Progress Percentages)
  uploadProgress = signal<number>(0);
  processingProgress = signal<number>(0);
  processingStep = signal<string>('');
  currentTaskId = signal<string | null>(null);

  // Format ve Dönüştürme Sinyalleri
  selectedRatio = signal<AspectRatioType>('4:5');
  framingMode = signal<FramingModeType>('blur_background');
  cleaningMethod = signal<CleaningMethodType>('telea');
  cleanWatermark = signal<boolean>(true);

  private pollIntervalId: any = null;

  constructor() {
    this.restoreSession();
  }

  restoreSession() {
    // 1. Önceki yüklenen dosyayı kurtar
    const savedFile = localStorage.getItem('cleanmark_active_file');
    if (savedFile) {
      try {
        const parsed = JSON.parse(savedFile);
        this.uploadedFile.set(parsed);
      } catch (e) {
        localStorage.removeItem('cleanmark_active_file');
      }
    }

    // 2. Devam eden veya tamamlanan görevi sorgula
    const savedTaskId = localStorage.getItem('cleanmark_current_task_id');
    if (savedTaskId) {
      this.currentTaskId.set(savedTaskId);
      this.http.get<TaskStatusResponse>(`/api/tasks/${savedTaskId}`).subscribe({
        next: (task) => {
          if (task.status === 'processing') {
            this.isProcessing.set(true);
            this.processingProgress.set(task.progress || 10);
            this.processingStep.set(task.step || 'İşleme devam ediliyor...');
            this.pollTask(savedTaskId);
          } else if (task.status === 'completed' && task.result) {
            this.processedResult.set(task.result);
            this.isProcessing.set(false);
          } else {
            localStorage.removeItem('cleanmark_current_task_id');
            this.currentTaskId.set(null);
            this.isProcessing.set(false);
          }
        },
        error: () => {
          localStorage.removeItem('cleanmark_current_task_id');
          this.currentTaskId.set(null);
        }
      });
    }
  }

  detectWatermarks(fileId: string) {
    this.isDetecting.set(true);
    return this.http.post<{ suggested_boxes: Box[] }>('/api/detect-watermark', { file_id: fileId }).pipe(
      tap(() => this.isDetecting.set(false)),
      catchError((err) => {
        this.isDetecting.set(false);
        this.errorMessage.set('Otomatik filigran tespiti yapılamadı.');
        return of({ suggested_boxes: [] });
      })
    );
  }

  upload(file: File) {
    this.isUploading.set(true);
    this.uploadProgress.set(0);
    this.errorMessage.set(null);
    this.processedResult.set(null);
    localStorage.removeItem('cleanmark_current_task_id');

    const formData = new FormData();
    formData.append('file', file);

    this.http.post<UploadResponse>('/api/upload', formData, {
      reportProgress: true,
      observe: 'events'
    }).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.UploadProgress && event.total) {
          const progress = Math.max(1, Math.round(100 * event.loaded / event.total));
          this.uploadProgress.set(progress);
        } else if (event.type === HttpEventType.Response && event.body) {
          this.uploadedFile.set(event.body);
          this.isUploading.set(false);
          this.uploadProgress.set(100);
          try {
            localStorage.setItem('cleanmark_active_file', JSON.stringify(event.body));
          } catch (e) {}
        }
      },
      error: (err) => {
        this.isUploading.set(false);
        this.uploadProgress.set(0);
        this.errorMessage.set(err.error?.detail || 'Dosya yüklenemedi.');
      }
    });
  }

  processMedia(boxes: Box[]) {
    const current = this.uploadedFile();
    if (!current) return;

    this.isProcessing.set(true);
    this.processingProgress.set(5);
    this.processingStep.set('İşlem başlatılıyor...');
    this.errorMessage.set(null);

    const payload = {
      file_id: current.file_id,
      boxes: boxes,
      clean_watermark: this.cleanWatermark() && boxes.length > 0,
      method: this.cleaningMethod(),
      target_ratio: this.selectedRatio(),
      framing_mode: this.framingMode()
    };

    this.http.post<{ task_id: string, status: string }>('/api/process', payload).subscribe({
      next: (res) => {
        const taskId = res.task_id;
        this.currentTaskId.set(taskId);
        localStorage.setItem('cleanmark_current_task_id', taskId);
        this.pollTask(taskId);
      },
      error: (err) => {
        this.isProcessing.set(false);
        this.errorMessage.set(err.error?.detail || 'İşlem başlatılamadı.');
      }
    });
  }

  cancelProcessing() {
    const taskId = this.currentTaskId();
    this.stopPolling();
    this.isProcessing.set(false);
    this.processingStep.set('İşlem iptal edildi.');
    localStorage.removeItem('cleanmark_current_task_id');

    if (taskId) {
      this.http.post(`/api/tasks/${taskId}/cancel`, {}).subscribe({
        next: () => {
          this.currentTaskId.set(null);
        },
        error: () => {
          this.currentTaskId.set(null);
        }
      });
    }
  }

  private stopPolling() {
    if (this.pollIntervalId) {
      clearInterval(this.pollIntervalId);
      this.pollIntervalId = null;
    }
  }

  private pollTask(taskId: string) {
    this.stopPolling();

    this.pollIntervalId = setInterval(() => {
      this.http.get<TaskStatusResponse>(`/api/tasks/${taskId}`).subscribe({
        next: (task) => {
          if (task.progress !== undefined) {
            this.processingProgress.set(task.progress);
          }
          if (task.step) {
            this.processingStep.set(task.step);
          }

          if (task.status === 'completed' && task.result) {
            this.stopPolling();
            this.processedResult.set(task.result);
            this.isProcessing.set(false);
          } else if (task.status === 'cancelled') {
            this.stopPolling();
            this.isProcessing.set(false);
            this.currentTaskId.set(null);
            localStorage.removeItem('cleanmark_current_task_id');
            this.processingStep.set('İşlem iptal edildi.');
          } else if (task.status === 'failed') {
            this.stopPolling();
            this.isProcessing.set(false);
            this.currentTaskId.set(null);
            localStorage.removeItem('cleanmark_current_task_id');
            this.errorMessage.set(task.error || 'İşlem sırasında hata oluştu.');
          }
        },
        error: (err) => {
          this.stopPolling();
          this.isProcessing.set(false);
          this.errorMessage.set(err.error?.detail || 'Görev durumu sorgulanamadı.');
        }
      });
    }, 750);
  }

  reset() {
    this.stopPolling();
    this.uploadedFile.set(null);
    this.processedResult.set(null);
    this.errorMessage.set(null);
    this.isUploading.set(false);
    this.isProcessing.set(false);
    this.uploadProgress.set(0);
    this.processingProgress.set(0);
    this.processingStep.set('');
    this.currentTaskId.set(null);
    localStorage.removeItem('cleanmark_active_file');
    localStorage.removeItem('cleanmark_current_task_id');
  }
}
