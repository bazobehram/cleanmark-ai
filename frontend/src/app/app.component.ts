import { Component, inject, ChangeDetectionStrategy } from '@angular/core';
import { HeaderComponent } from './components/header.component';
import { FileUploaderComponent } from './components/file-uploader.component';
import { CanvasSelectorComponent } from './components/canvas-selector.component';
import { ResultPreviewComponent } from './components/result-preview.component';
import { CleanerService } from './services/cleaner.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    HeaderComponent,
    FileUploaderComponent,
    CanvasSelectorComponent,
    ResultPreviewComponent
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-cyan-500 selection:text-white">
      <app-header />

      <main class="max-w-4xl mx-auto px-4 pt-6 pb-16 space-y-6">
        
        <!-- Başlık -->
        @if (!cleanerService.uploadedFile() && !cleanerService.processedResult()) {
          <div class="text-center max-w-xl mx-auto space-y-2 mb-2">
            <h1 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Filigran Silici & <span class="bg-gradient-to-r from-cyan-400 via-pink-400 to-indigo-400 bg-clip-text text-transparent">Instagram Format</span> Dönüştürücü
            </h1>
            <p class="text-xs sm:text-sm text-slate-400">
              Videolarınızdan ve fotoğraflarınızdan filigranları silin; tek tıkla <strong>Instagram 4:5 Dikey Akış</strong>, <strong>9:16 Reels</strong> veya <strong>1:1 Kare</strong> boyutuna dönüştürün.
            </p>
          </div>
        }

        <!-- Hata Bildirimi -->
        @if (cleanerService.errorMessage(); as error) {
          <div class="bg-rose-950/40 border border-rose-800 text-rose-300 px-4 py-3 rounded-xl text-xs flex items-center justify-between">
            <span class="flex items-center gap-2">
              <i class="fa-solid fa-triangle-exclamation"></i> {{ error }}
            </span>
            <button (click)="cleanerService.errorMessage.set(null)" class="text-rose-400 hover:text-white">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
        }

        <!-- Yükleme Göstergesi & İlerleme Çubuğu -->
        @if (cleanerService.isUploading()) {
          <div class="bg-slate-900/95 border border-cyan-500/40 rounded-2xl p-6 sm:p-8 text-center space-y-4 shadow-2xl backdrop-blur-md animate-fade-in">
            <div class="flex items-center justify-between text-xs sm:text-sm">
              <span class="text-cyan-300 font-bold flex items-center gap-2">
                <i class="fa-solid fa-cloud-arrow-up animate-bounce text-cyan-400 text-base"></i>
                @if (cleanerService.uploadProgress() === 0) {
                  Sunucuya bağlanıyor ve veri hazırlanıyor...
                } @else if (cleanerService.uploadProgress() >= 100) {
                  Dosya yüklendi, video karesi çıkarılıyor...
                } @else {
                  Dosya Yükleniyor...
                }
              </span>
              <span class="font-mono text-cyan-400 font-extrabold text-sm sm:text-base bg-cyan-500/10 px-2.5 py-1 rounded-lg border border-cyan-500/20">
                %{{ cleanerService.uploadProgress() }}
              </span>
            </div>
            
            <div class="w-full bg-slate-950 rounded-full h-3.5 p-0.5 border border-cyan-500/30 overflow-hidden shadow-inner">
              <div class="bg-gradient-to-r from-cyan-500 via-teal-400 to-indigo-500 h-full rounded-full transition-all duration-150 shadow-lg shadow-cyan-500/40 relative overflow-hidden"
                   [style.width.%]="cleanerService.uploadProgress() || (cleanerService.isUploading() ? 2 : 0)">
                <div class="absolute inset-0 bg-white/20 animate-pulse"></div>
              </div>
            </div>

            <p class="text-[11px] text-slate-400">
              @if (cleanerService.uploadProgress() >= 100) {
                <span class="text-emerald-400 font-medium"><i class="fa-solid fa-circle-check mr-1"></i> Yükleme tamamlandı, filigranlar analiz ediliyor...</span>
              } @else {
                <span>Lütfen yükleme tamamlanana kadar sayfayı kapatmayın.</span>
              }
            </p>
          </div>
        }

        <!-- 1. Adım: Dosya Yükleyici -->
        @if (!cleanerService.uploadedFile() && !cleanerService.processedResult() && !cleanerService.isUploading()) {
          <app-file-uploader />
        }

        <!-- 2. Adım: Alan Seçici ve Instagram Format Vitrini -->
        @if (cleanerService.uploadedFile() && !cleanerService.processedResult()) {
          <app-canvas-selector />
        }

        <!-- 3. Adım: Sonuç ve İndirme -->
        @if (cleanerService.processedResult()) {
          <app-result-preview />
        }

      </main>
    </div>
  `
})
export class AppComponent {
  cleanerService = inject(CleanerService);
}
