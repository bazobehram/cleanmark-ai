import { Component, inject, ChangeDetectionStrategy } from '@angular/core';
import { CleanerService } from '../services/cleaner.service';

@Component({
  selector: 'app-result-preview',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (cleanerService.processedResult(); as res) {
      <div class="bg-slate-900 border border-emerald-500/30 rounded-2xl p-4 sm:p-6 shadow-2xl space-y-5">
        
        <!-- Üst Başlık & Format Bilgisi -->
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div class="flex items-center gap-2.5">
            <span class="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 flex items-center justify-center text-sm shadow-md shadow-emerald-500/10">
              <i class="fa-solid fa-check"></i>
            </span>
            <div>
              <h3 class="text-sm sm:text-base font-bold text-white flex items-center gap-2">
                İşlem Başarıyla Tamamlandı!
                <span class="text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-full font-mono">
                  {{ res.target_ratio === 'original' ? 'Orijinal Boyut' : res.target_ratio }}
                </span>
              </h3>
              <p class="text-[11px] text-slate-400">Filigran temizlendi ve hedef sosyal medya formatına dönüştürüldü.</p>
            </div>
          </div>

          <button (click)="cleanerService.reset()" 
                  class="text-xs bg-slate-800 hover:bg-slate-750 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700 flex items-center gap-1.5 transition-all">
            <i class="fa-solid fa-rotate-left"></i> Yeni Dosya Yükle
          </button>
        </div>

        <!-- Önizleme Alanı -->
        @if (res.is_video) {
          <!-- Video Oynatıcı -->
          <div class="w-full bg-slate-950 rounded-2xl p-3 border border-slate-800 flex flex-col items-center justify-center">
            <video controls playsinline class="max-h-[60vh] max-w-full rounded-xl shadow-2xl">
              <source [src]="res.cleaned_url" type="video/mp4">
              Tarayıcınız video oynatmayı desteklemiyor.
            </video>
          </div>
        } @else {
          <!-- Resim Karşılaştırma -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 text-center space-y-2">
              <span class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Orijinal (Girdi)</span>
              <img [src]="cleanerService.uploadedFile()?.preview_url" 
                   class="max-h-[45vh] w-full object-contain rounded-lg">
            </div>
            <div class="bg-slate-950 p-3 rounded-xl border border-emerald-500/30 text-center space-y-2">
              <span class="text-[10px] uppercase font-bold text-emerald-400 tracking-wider">Dönüştürülmüş & Temizlenmiş</span>
              <img [src]="res.cleaned_url" 
                   class="max-h-[45vh] w-full object-contain rounded-lg">
            </div>
          </div>
        }

        <!-- İndirme Butonu -->
        <div class="pt-2 flex flex-col sm:flex-row items-center justify-end gap-3">
          <a [href]="res.download_url" [download]="res.filename"
             class="w-full sm:w-auto bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white font-bold text-sm py-3 px-8 rounded-xl shadow-lg shadow-emerald-600/25 flex items-center justify-center gap-2 transition-all active:scale-95">
            <i class="fa-solid fa-download"></i>
            <span>Dönüştürülmüş Dosyayı İndir</span>
          </a>
        </div>

      </div>
    }
  `
})
export class ResultPreviewComponent {
  cleanerService = inject(CleanerService);
}
