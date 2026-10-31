import { Component, inject, signal, ChangeDetectionStrategy } from '@angular/core';
import { CleanerService } from '../services/cleaner.service';

@Component({
  selector: 'app-file-uploader',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="bg-slate-900/90 border-2 border-dashed border-slate-800 hover:border-cyan-500/50 rounded-2xl p-8 text-center transition-all cursor-pointer backdrop-blur-sm"
         (dragover)="onDragOver($event)"
         (dragleave)="onDragLeave($event)"
         (drop)="onDrop($event)"
         (click)="fileInput.click()">
      
      <input #fileInput type="file" class="hidden" 
             accept="image/*,video/mp4,video/quicktime,video/webm"
             (change)="onFileSelected($event)">

      <div class="max-w-md mx-auto space-y-4">
        <div class="w-16 h-16 mx-auto rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 text-2xl shadow-lg shadow-cyan-500/10">
          <i class="fa-solid fa-cloud-arrow-up"></i>
        </div>

        <div>
          <h3 class="text-base font-bold text-white mb-1">
            Resim veya Video Dosyasını Buraya Sürükleyin
          </h3>
          <p class="text-xs text-slate-400">
            JPG, PNG, WebP fotoğraflar veya MP4, MOV, WebM videolar
          </p>
        </div>

        <button type="button" 
                class="bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold py-2.5 px-5 rounded-xl shadow-lg shadow-cyan-600/20 inline-flex items-center gap-2 transition-all active:scale-95">
          <i class="fa-regular fa-folder-open"></i>
          <span>Cihazdan Dosya Seç</span>
        </button>
      </div>
    </div>
  `
})
export class FileUploaderComponent {
  cleanerService = inject(CleanerService);
  isDragging = signal(false);

  onDragOver(e: DragEvent) {
    e.preventDefault();
    this.isDragging.set(true);
  }

  onDragLeave(e: DragEvent) {
    e.preventDefault();
    this.isDragging.set(false);
  }

  onDrop(e: DragEvent) {
    e.preventDefault();
    this.isDragging.set(false);
    if (e.dataTransfer && e.dataTransfer.files.length > 0) {
      this.handleFile(e.dataTransfer.files[0]);
    }
  }

  onFileSelected(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFile(input.files[0]);
    }
  }

  private handleFile(file: File) {
    this.cleanerService.upload(file);
  }
}
