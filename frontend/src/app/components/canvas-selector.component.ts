import { Component, ElementRef, ViewChild, AfterViewInit, inject, signal, ChangeDetectionStrategy } from '@angular/core';
import { CleanerService } from '../services/cleaner.service';
import { Box, AspectRatioType, FramingModeType } from '../models/cleaner.model';

@Component({
  selector: 'app-canvas-selector',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (cleanerService.uploadedFile(); as file) {
      <div class="space-y-6">

        <!-- 1. BÖLÜM: Filigran / Logo Seçim Alanı -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-xl space-y-4">
          <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
            <div>
              <span class="text-xs sm:text-sm font-bold text-white flex items-center gap-1.5">
                <i class="fa-solid fa-crosshairs text-cyan-400"></i> Adım 1: Silinecek Filigran / Logo Alanı
              </span>
              <p class="text-[11px] text-slate-400">
                Logonun üzerine <strong>tıklayın</strong>, <strong>kutu çizin</strong> veya <strong>Otomatik Bul</strong> butonunu kullanın.
              </p>
            </div>
            <button (click)="cleanerService.reset()" 
                    class="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 bg-slate-800 px-2.5 py-1.5 rounded-lg border border-slate-700">
              <i class="fa-solid fa-arrow-left"></i> Farklı Dosya
            </button>
          </div>

          <!-- Otomatik Tespit & Hızlı Şablonlar Çubuğu -->
          <div class="flex flex-wrap items-center gap-2 text-xs">
            
            <!-- AI Otomatik Filigran Bul Butonu -->
            <button type="button" (click)="triggerAutoDetect()" [disabled]="cleanerService.isDetecting()"
                    class="bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-slate-950 font-bold px-3 py-1.5 rounded-lg border border-yellow-400 shadow-md shadow-amber-500/20 active:scale-95 transition-all flex items-center gap-1.5 text-xs">
              @if (cleanerService.isDetecting()) {
                <i class="fa-solid fa-spinner fa-spin text-xs"></i> Taranıyor...
              } @else {
                <i class="fa-solid fa-wand-magic-sparkles text-xs"></i> ✨ Otomatik Filigran Bul (AI Detect)
              }
            </button>

            <span class="text-[11px] text-slate-500 font-semibold ml-1 mr-0.5">Şablonlar:</span>

            <button (click)="setPreset('kling')" 
                    class="bg-indigo-950/60 hover:bg-indigo-900/80 text-indigo-300 px-2.5 py-1.5 rounded-lg border border-indigo-700/60 active:scale-95 transition-all flex items-center gap-1">
              <i class="fa-solid fa-star text-amber-400 text-[10px]"></i> Kling AI Yıldızı (Sağ Alt)
            </button>

            <button (click)="setPreset('tiktok-br')" 
                    class="bg-slate-800 hover:bg-slate-750 text-slate-300 px-2.5 py-1.5 rounded-lg border border-slate-700 active:scale-95 transition-all flex items-center gap-1">
              <i class="fa-brands fa-tiktok text-cyan-400 text-[10px]"></i> TikTok Sağ Alt
            </button>

            <button (click)="setPreset('tiktok-tl')" 
                    class="bg-slate-800 hover:bg-slate-750 text-slate-300 px-2.5 py-1.5 rounded-lg border border-slate-700 active:scale-95 transition-all flex items-center gap-1">
              <i class="fa-brands fa-tiktok text-pink-400 text-[10px]"></i> TikTok Sol Üst
            </button>

            <button (click)="setPreset('bottom-right')" 
                    class="bg-slate-800 hover:bg-slate-750 text-slate-300 px-2 py-1.5 rounded-lg border border-slate-700 active:scale-95 transition-all">
              Sağ Alt Geniş
            </button>

            <button (click)="clearBoxes()" 
                    class="text-rose-400 hover:text-rose-300 px-2 py-1.5 ml-auto text-xs flex items-center gap-1">
              <i class="fa-solid fa-trash-can"></i> Temizle
            </button>
          </div>

          <!-- Durum ve Seçilen Alan Bilgi Rozeti -->
          @if (boxes().length === 0) {
            <div class="bg-amber-950/30 border border-amber-600/40 text-amber-300/90 px-3.5 py-2.5 rounded-xl text-xs flex items-center justify-between">
              <div class="flex items-center gap-2">
                <i class="fa-solid fa-triangle-exclamation text-amber-400 text-sm"></i>
                <span>Henüz silinecek alan seçilmedi. Videodaki filigranın üzerine <strong>tıklayın</strong> veya <strong>"Otomatik Filigran Bul"</strong> butonuna basın.</span>
              </div>
              <button (click)="setPreset('kling')" class="text-amber-400 hover:text-white underline text-[11px] whitespace-nowrap ml-2">
                Kling AI Seç
              </button>
            </div>
          } @else {
            <div class="space-y-2">
              @if (hasAutoDetected()) {
                <div class="bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 px-3.5 py-2 rounded-xl text-xs flex items-center justify-between animate-fade-in">
                  <span class="flex items-center gap-2">
                    <i class="fa-solid fa-circle-check text-emerald-400"></i>
                    <strong>Otomatik Tespit Edildi:</strong> {{ boxes().length }} filigran alanı silinmeye hazır!
                  </span>
                  <span class="text-emerald-400/70 text-[11px]">İsterseniz kutuyu sürükleyip değiştirebilirsiniz</span>
                </div>
              }

              <!-- Seçili Alanlar Listesi -->
              <div class="flex flex-wrap items-center gap-1.5">
                <span class="text-[11px] text-slate-400 font-semibold mr-1">Seçili Alanlar ({{ boxes().length }}):</span>
                @for (b of boxes(); track $index) {
                  <span class="inline-flex items-center gap-1.5 bg-rose-950/50 border border-rose-500/50 text-rose-200 px-2.5 py-1 rounded-lg text-[11px] shadow-sm">
                    <i class="fa-solid fa-crosshairs text-rose-400"></i>
                    <span>{{ b.label || ('Alan #' + ($index + 1)) }} [{{ b.x }}, {{ b.y }} - {{ b.w }}x{{ b.h }}]</span>
                    <button type="button" (click)="removeBox($index)" class="hover:text-white ml-1 text-rose-400" title="Alanı Kaldır">
                      <i class="fa-solid fa-xmark"></i>
                    </button>
                  </span>
                }
              </div>
            </div>
          }

          <!-- Canvas Çizim Alanı -->
          <div class="relative w-full flex items-center justify-center bg-slate-950 rounded-xl overflow-hidden border border-slate-800 touch-none select-none">
            <canvas #canvasRef
                    (mousedown)="onMouseDown($event)"
                    (mousemove)="onMouseMove($event)"
                    (mouseup)="onMouseUp()"
                    (touchstart)="onTouchStart($event)"
                    (touchmove)="onTouchMove($event)"
                    (touchend)="onMouseUp()"
                    class="max-w-full max-h-[52vh] object-contain cursor-crosshair">
            </canvas>
          </div>

          <p class="text-[11px] text-slate-500 text-center">
            <i class="fa-solid fa-mouse-pointer text-cyan-400 mr-1"></i> İpucu: Videodaki logonun üzerine <strong>tek tıklayarak</strong> kutuyu anında yerleştirebilir veya farenizle sürükleyerek özel boyut çizebilirsiniz.
          </p>
        </div>

        <!-- 2. BÖLÜM: Sosyal Medya Boyut ve Format Dönüştürücü (Instagram Showcase) -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-xl space-y-5">
          <div class="border-b border-slate-800 pb-3">
            <span class="text-xs sm:text-sm font-bold text-white flex items-center gap-1.5">
              <i class="fa-brands fa-instagram text-pink-500"></i> Adım 2: Sosyal Medya Boyut Dönüştürücü & Canlı Vitrin
            </span>
            <p class="text-[11px] text-slate-400">
              Videonuzun veya görselinizin Instagram ve TikTok'ta nasıl görüneceğini seçin ve canlı önizleyin.
            </p>
          </div>

          <!-- Format Seçim Kartları Grid -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            
            <!-- 4:5 Instagram Feed Kartı -->
            <div (click)="selectRatio('4:5')"
                 [class]="cleanerService.selectedRatio() === '4:5' ? 'border-cyan-500 bg-cyan-500/10 shadow-md shadow-cyan-500/10' : 'border-slate-800 bg-slate-950/60 hover:border-slate-700'"
                 class="border-2 rounded-xl p-3 cursor-pointer transition-all flex flex-col justify-between">
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-bold text-white">4:5 Dikey Akış</span>
                <i class="fa-brands fa-instagram text-pink-400 text-sm"></i>
              </div>
              <div class="w-7 h-9 mx-auto border-2 border-dashed border-cyan-400/60 rounded flex items-center justify-center text-[10px] text-cyan-300 font-mono mb-2">
                4:5
              </div>
              <div class="text-[10px] text-center text-slate-400">
                1080 × 1350<br>
                <span class="text-emerald-400 font-medium">Akışta Kesinti Yok</span>
              </div>
            </div>

            <!-- 9:16 Reels / TikTok Kartı -->
            <div (click)="selectRatio('9:16')"
                 [class]="cleanerService.selectedRatio() === '9:16' ? 'border-cyan-500 bg-cyan-500/10 shadow-md shadow-cyan-500/10' : 'border-slate-800 bg-slate-950/60 hover:border-slate-700'"
                 class="border-2 rounded-xl p-3 cursor-pointer transition-all flex flex-col justify-between">
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-bold text-white">9:16 Reels/TikTok</span>
                <i class="fa-brands fa-tiktok text-cyan-400 text-sm"></i>
              </div>
              <div class="w-6 h-10 mx-auto border-2 border-dashed border-cyan-400/60 rounded flex items-center justify-center text-[10px] text-cyan-300 font-mono mb-2">
                9:16
              </div>
              <div class="text-[10px] text-center text-slate-400">
                1080 × 1920<br>
                <span class="text-indigo-400 font-medium">Tam Ekran Dikey</span>
              </div>
            </div>

            <!-- 1:1 Kare Kartı -->
            <div (click)="selectRatio('1:1')"
                 [class]="cleanerService.selectedRatio() === '1:1' ? 'border-cyan-500 bg-cyan-500/10 shadow-md shadow-cyan-500/10' : 'border-slate-800 bg-slate-950/60 hover:border-slate-700'"
                 class="border-2 rounded-xl p-3 cursor-pointer transition-all flex flex-col justify-between">
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-bold text-white">1:1 Kare Post</span>
                <i class="fa-regular fa-square text-slate-400 text-sm"></i>
              </div>
              <div class="w-8 h-8 mx-auto border-2 border-dashed border-cyan-400/60 rounded flex items-center justify-center text-[10px] text-cyan-300 font-mono mb-2">
                1:1
              </div>
              <div class="text-[10px] text-center text-slate-400">
                1080 × 1080<br>
                <span class="text-slate-300 font-medium">Klasik Kare</span>
              </div>
            </div>

            <!-- Orijinal Oran Kartı -->
            <div (click)="selectRatio('original')"
                 [class]="cleanerService.selectedRatio() === 'original' ? 'border-cyan-500 bg-cyan-500/10 shadow-md shadow-cyan-500/10' : 'border-slate-800 bg-slate-950/60 hover:border-slate-700'"
                 class="border-2 rounded-xl p-3 cursor-pointer transition-all flex flex-col justify-between">
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-bold text-white">Orijinal Boyut</span>
                <i class="fa-solid fa-expand text-slate-400 text-sm"></i>
              </div>
              <div class="w-10 h-7 mx-auto border-2 border-dashed border-slate-600 rounded flex items-center justify-center text-[10px] text-slate-400 font-mono mb-2">
                {{ file.width }}x{{ file.height }}
              </div>
              <div class="text-[10px] text-center text-slate-400">
                Oran Korunur<br>
                <span class="text-slate-500">Dönüştürme Yok</span>
              </div>
            </div>

          </div>

          <!-- Çerçeveleme Modu (Framing Style) -->
          @if (cleanerService.selectedRatio() !== 'original') {
            <div class="pt-2">
              <label class="block text-xs font-semibold text-slate-300 mb-2">Çerçeveleme ve Yerleşim Modu</label>
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <button type="button" (click)="setFraming('blur_background')"
                        [class]="cleanerService.framingMode() === 'blur_background' ? 'bg-indigo-600/25 border-indigo-500 text-white' : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'"
                        class="border rounded-xl p-2.5 text-xs text-left transition-all">
                  <div class="font-bold flex items-center gap-1.5 mb-0.5">
                    <i class="fa-solid fa-wand-magic text-indigo-400"></i> Bulanık Arka Plan (Fit & Blur)
                  </div>
                  <div class="text-[10px] text-slate-400">Görüntü hiç kesilmez, arkaya şık bulanık yansıma eklenir. (Önerilen)</div>
                </button>

                <button type="button" (click)="setFraming('crop_center')"
                        [class]="cleanerService.framingMode() === 'crop_center' ? 'bg-indigo-600/25 border-indigo-500 text-white' : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'"
                        class="border rounded-xl p-2.5 text-xs text-left transition-all">
                  <div class="font-bold flex items-center gap-1.5 mb-0.5">
                    <i class="fa-solid fa-crop text-indigo-400"></i> Ortadan Kırp (Fill / Zoom)
                  </div>
                  <div class="text-[10px] text-slate-400">Tüm ekranı doldurur, sağ ve soldan hafif kırpar.</div>
                </button>

                <button type="button" (click)="setFraming('pad_black')"
                        [class]="cleanerService.framingMode() === 'pad_black' ? 'bg-indigo-600/25 border-indigo-500 text-white' : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'"
                        class="border rounded-xl p-2.5 text-xs text-left transition-all">
                  <div class="font-bold flex items-center gap-1.5 mb-0.5">
                    <i class="fa-solid fa-bars text-indigo-400"></i> Siyah Bant (Letterbox)
                  </div>
                  <div class="text-[10px] text-slate-400">Klasik üst-alt veya sağ-sol siyah kenarlıklar.</div>
                </button>
              </div>
            </div>
          }

          <!-- CANLI İNTERAKTİF SHOWCASE / VİTRİN SİMÜLASYONU -->
          @if (cleanerService.selectedRatio() !== 'original') {
            <div class="pt-2">
              <span class="block text-xs font-semibold text-slate-300 mb-2">
                <i class="fa-regular fa-eye text-cyan-400 mr-1"></i> Instagram Canlı Vitrin Simülasyonu (Showcase Preview)
              </span>
              
              <div class="bg-slate-950 border border-slate-800 rounded-2xl p-4 flex flex-col items-center justify-center overflow-hidden">
                <!-- Simüle Edilmiş Instagram Çerçevesi -->
                <div [style.aspect-ratio]="getAspectRatioCss(cleanerService.selectedRatio())"
                     class="relative w-64 max-w-full bg-black rounded-xl overflow-hidden border border-slate-700 shadow-2xl flex items-center justify-center">
                  
                  <!-- Bulanık Arka Plan Simülasyonu -->
                  @if (cleanerService.framingMode() === 'blur_background') {
                    <img [src]="file.preview_url" 
                         class="absolute inset-0 w-full h-full object-cover filter blur-md opacity-60 scale-110">
                    <img [src]="file.preview_url" 
                         class="relative max-w-full max-h-full object-contain z-10 shadow-lg">
                  } @else if (cleanerService.framingMode() === 'crop_center') {
                    <img [src]="file.preview_url" 
                         class="w-full h-full object-cover">
                  } @else {
                    <img [src]="file.preview_url" 
                         class="max-w-full max-h-full object-contain">
                  }

                  <!-- Instagram UI Mockup İkonları Overlay -->
                  <div class="absolute inset-0 pointer-events-none flex flex-col justify-between p-2.5 z-20">
                    <div class="flex items-center gap-1.5 text-[10px] text-white/90 drop-shadow">
                      <div class="w-4 h-4 rounded-full bg-gradient-to-tr from-pink-500 to-yellow-500"></div>
                      <span class="font-bold">kullanici_adi</span>
                    </div>

                    <div class="flex items-end justify-between text-white/90 text-xs drop-shadow">
                      <div class="space-y-0.5">
                        <div class="text-[9px] font-semibold">CleanMark AI Showcase</div>
                        <div class="text-[8px] text-white/70">#instagram #video</div>
                      </div>
                      <div class="flex flex-col items-center gap-2 text-sm text-white/90">
                        <i class="fa-regular fa-heart"></i>
                        <i class="fa-regular fa-comment"></i>
                        <i class="fa-regular fa-paper-plane"></i>
                      </div>
                    </div>
                  </div>

                </div>

                <p class="text-[10px] text-slate-500 mt-2 text-center">
                  Yukarıdaki vitrin, videonuzun Instagram'da yayınlandığında nasıl görüneceğini gerçek zamanlı olarak gösterir.
                </p>
              </div>
            </div>
          }

          <!-- Temizleme Motoru Seçimi (Inpainting vs Delogo) -->
          <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-white flex items-center gap-2">
                <i class="fa-solid fa-wand-magic-sparkles text-cyan-400"></i>
                Temizleme Motoru & Kalite Tercihi
              </span>
              <span class="text-[10px] text-emerald-400 font-semibold bg-emerald-950/50 px-2 py-0.5 rounded border border-emerald-800/60">
                Önerilen: AI Doku Onarımı
              </span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <div (click)="cleanerService.cleaningMethod.set('telea')"
                   [class]="cleanerService.cleaningMethod() === 'telea' ? 'border-cyan-500 bg-cyan-500/10 shadow-md shadow-cyan-500/10' : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'"
                   class="border-2 rounded-xl p-3 cursor-pointer transition-all flex items-start gap-3">
                <div class="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 text-sm shrink-0">
                  <i class="fa-solid fa-feather-pointed"></i>
                </div>
                <div class="space-y-0.5">
                  <div class="text-xs font-bold text-white flex items-center gap-1.5">
                    <span>✨ AI Doku Onarımı</span>
                    <span class="text-[9px] bg-cyan-500/20 text-cyan-300 px-1.5 py-0.5 rounded font-mono">Lekesiz</span>
                  </div>
                  <p class="text-[10px] text-slate-400">
                    Yalnızca filigran siluetini onarır; arkadaki yazıları, yüzleri ve saç dokusunu lekesiz, kristal netlikte korur.
                  </p>
                </div>
              </div>

              <div (click)="cleanerService.cleaningMethod.set('delogo')"
                   [class]="cleanerService.cleaningMethod() === 'delogo' ? 'border-indigo-500 bg-indigo-500/10 shadow-md shadow-indigo-500/10' : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'"
                   class="border-2 rounded-xl p-3 cursor-pointer transition-all flex items-start gap-3">
                <div class="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400 text-sm shrink-0">
                  <i class="fa-solid fa-shapes"></i>
                </div>
                <div class="space-y-0.5">
                  <div class="text-xs font-bold text-slate-300">
                    Klasik Bulanıklaştırma (Delogo)
                  </div>
                  <p class="text-[10px] text-slate-500">
                    Tüm seçili kutu alanını kenar renkleriyle doğrusal olarak bulanıklaştırır.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Canlı İşleme İlerleme Kartı & Yüzdesi -->
          @if (cleanerService.isProcessing()) {
            <div class="bg-slate-950 border border-indigo-500/40 rounded-2xl p-5 shadow-2xl space-y-3 animate-fade-in">
              <div class="flex items-center justify-between text-xs sm:text-sm">
                <span class="text-indigo-300 font-bold flex items-center gap-2">
                  <i class="fa-solid fa-wand-magic-sparkles text-yellow-400 animate-spin"></i>
                  {{ cleanerService.processingStep() || 'Medya İşleniyor...' }}
                </span>
                <div class="flex items-center gap-2">
                  <span class="font-mono text-indigo-300 font-extrabold text-sm sm:text-base bg-indigo-500/10 px-2.5 py-1 rounded-lg border border-indigo-500/20">
                    %{{ cleanerService.processingProgress() }}
                  </span>
                  <button type="button" (click)="cleanerService.cancelProcessing()"
                          class="bg-rose-950/70 hover:bg-rose-900 border border-rose-700/70 text-rose-300 hover:text-white px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm active:scale-95">
                    <i class="fa-solid fa-ban text-rose-400"></i>
                    <span>İptal Et</span>
                  </button>
                </div>
              </div>
              
              <div class="w-full bg-slate-900 rounded-full h-3.5 p-0.5 border border-indigo-500/30 overflow-hidden shadow-inner">
                <div class="bg-gradient-to-r from-cyan-500 via-indigo-500 to-pink-500 h-full rounded-full transition-all duration-300 shadow-lg shadow-indigo-500/40 relative overflow-hidden"
                     [style.width.%]="cleanerService.processingProgress()">
                  <div class="absolute inset-0 bg-white/20 animate-pulse"></div>
                </div>
              </div>

              <div class="flex items-center justify-between text-[11px] text-slate-400">
                <span>Sayfayı yenileseniz dahi işlem arka planda devam eder.</span>
                <span>Lütfen bekleyiniz...</span>
              </div>
            </div>
          }

          <!-- Ana İşlem Butonu -->
          <div class="pt-3 border-t border-slate-800 flex items-center justify-between gap-3">
            @if (cleanerService.isProcessing()) {
              <button type="button" (click)="cleanerService.cancelProcessing()"
                      class="bg-rose-950/80 hover:bg-rose-900 border border-rose-700 text-rose-300 hover:text-white text-xs sm:text-sm font-bold py-3 px-6 rounded-xl flex items-center gap-2 transition-all active:scale-95 shadow-lg shadow-rose-950/50">
                <i class="fa-solid fa-ban text-rose-400"></i>
                <span>İşlemi İptal Et</span>
              </button>
            } @else {
              <button type="button" (click)="cleanerService.reset()"
                      class="text-xs text-slate-400 hover:text-white py-2 px-3 rounded-lg hover:bg-slate-800 transition-all flex items-center gap-1.5">
                <i class="fa-solid fa-arrow-left"></i>
                <span>Başka Dosya Seç</span>
              </button>
            }

            <button (click)="onProcess()" [disabled]="cleanerService.isProcessing()"
                    class="w-full sm:w-auto bg-gradient-to-r from-cyan-600 via-indigo-600 to-purple-600 hover:from-cyan-500 hover:to-purple-500 text-white font-bold text-xs sm:text-sm py-3 px-8 rounded-xl shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50">
              @if (cleanerService.isProcessing()) {
                <i class="fa-solid fa-spinner fa-spin text-sm"></i>
                <span>İşleniyor (%{{ cleanerService.processingProgress() }})...</span>
              } @else {
                <i class="fa-solid fa-wand-magic-sparkles text-yellow-300"></i>
                <span>
                  @if (boxes().length > 0) {
                    Filigranı Sil ({{ boxes().length }} Alan) ve {{ cleanerService.selectedRatio() }} Boyutuna Dönüştür
                  } @else {
                    Filigranı Temizle ve Instagram Boyutuna Dönüştür
                  }
                </span>
              }
            </button>
          </div>

        </div>

        <!-- UYARI MODALI: ALAN SEÇİLMEDEN TIKLANDIĞINDA AÇILIR -->
        @if (showEmptyModal()) {
          <div class="fixed inset-0 bg-slate-950/85 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
            <div class="bg-slate-900 border border-amber-500/50 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
              <div class="flex items-center gap-3 text-amber-400">
                <i class="fa-solid fa-triangle-exclamation text-2xl"></i>
                <div>
                  <h3 class="text-sm sm:text-base font-bold text-white">Filigran Alanı Seçilmedi!</h3>
                  <p class="text-[11px] text-amber-400/80">Kutucuk çizilmedi veya şablon seçilmedi</p>
                </div>
              </div>

              <p class="text-xs text-slate-300 leading-relaxed">
                Videodan silinmesini istediğiniz filigran veya logo alanını henüz seçmediniz. Ne yapmak istersiniz?
              </p>

              <div class="space-y-2 pt-2">
                <button (click)="autoDetectAndProcess()"
                        class="w-full bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-slate-950 font-bold py-2.5 px-4 rounded-xl text-xs flex items-center justify-center gap-2 shadow-lg shadow-amber-500/20 active:scale-95 transition-all">
                  <i class="fa-solid fa-wand-magic-sparkles"></i> ✨ Otomatik Filigran Bul ve Sil
                </button>

                <button (click)="processWithoutWatermark()"
                        class="w-full bg-slate-800 hover:bg-slate-750 text-slate-200 font-semibold py-2.5 px-4 rounded-xl text-xs border border-slate-700 flex items-center justify-center gap-2">
                  <i class="fa-solid fa-crop"></i> Filigran Silmeden Sadece Boyut Dönüştür ({{ cleanerService.selectedRatio() }})
                </button>

                <button (click)="showEmptyModal.set(false)"
                        class="w-full bg-transparent hover:bg-slate-800/60 text-slate-400 hover:text-white py-2 text-xs text-center rounded-xl">
                  Geri Dön, Kendim Seçeceğim
                </button>
              </div>
            </div>
          </div>
        }

      </div>
    }
  `
})
export class CanvasSelectorComponent implements AfterViewInit {
  cleanerService = inject(CleanerService);

  @ViewChild('canvasRef') canvasRef!: ElementRef<HTMLCanvasElement>;

  boxes = signal<Box[]>([]);
  hasAutoDetected = signal<boolean>(false);
  showEmptyModal = signal<boolean>(false);

  private isDrawing = false;
  private startX = 0;
  private startY = 0;
  private currentX = 0;
  private currentY = 0;
  private img = new Image();

  ngAfterViewInit() {
    const file = this.cleanerService.uploadedFile();
    if (file) {
      if (file.suggested_boxes && file.suggested_boxes.length > 0) {
        this.boxes.set([...file.suggested_boxes]);
        this.hasAutoDetected.set(true);
      }
      this.loadImage(file.preview_url);
    }
  }

  private loadImage(src: string) {
    this.img.crossOrigin = 'anonymous';
    this.img.src = src;
    this.img.onload = () => {
      const canvas = this.canvasRef.nativeElement;
      canvas.width = this.img.width;
      canvas.height = this.img.height;
      this.redraw();
    };
  }

  private redraw() {
    const canvas = this.canvasRef?.nativeElement;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(this.img, 0, 0);

    this.boxes().forEach((b, idx) => {
      // Yarı saydam kırmızı kutu
      ctx.fillStyle = 'rgba(239, 68, 68, 0.4)';
      ctx.fillRect(b.x, b.y, b.w, b.h);
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 3;
      ctx.strokeRect(b.x, b.y, b.w, b.h);

      // Kutu başlığı & koordinat etiketi
      ctx.fillStyle = '#ef4444';
      ctx.fillRect(b.x, Math.max(0, b.y - 24), Math.max(90, b.w), 24);

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 13px sans-serif';
      ctx.fillText(`${b.label || ('Alan #' + (idx + 1))}`, b.x + 6, Math.max(16, b.y - 7));
    });

    if (this.isDrawing) {
      const x = Math.min(this.startX, this.currentX);
      const y = Math.min(this.startY, this.currentY);
      const w = Math.abs(this.currentX - this.startX);
      const h = Math.abs(this.currentY - this.startY);

      ctx.fillStyle = 'rgba(6, 182, 212, 0.4)';
      ctx.fillRect(x, y, w, h);
      ctx.strokeStyle = '#06b6d4';
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, w, h);
    }
  }

  private getCanvasCoords(e: MouseEvent | Touch): { x: number, y: number } {
    const canvas = this.canvasRef.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
  }

  onMouseDown(e: MouseEvent) {
    const coords = this.getCanvasCoords(e);
    this.isDrawing = true;
    this.startX = coords.x;
    this.startY = coords.y;
    this.currentX = coords.x;
    this.currentY = coords.y;
  }

  onMouseMove(e: MouseEvent) {
    if (!this.isDrawing) return;
    const coords = this.getCanvasCoords(e);
    this.currentX = coords.x;
    this.currentY = coords.y;
    this.redraw();
  }

  onMouseUp() {
    if (!this.isDrawing) return;
    this.isDrawing = false;

    const dragDistX = Math.abs(this.currentX - this.startX);
    const dragDistY = Math.abs(this.currentY - this.startY);

    if (dragDistX > 10 && dragDistY > 10) {
      // Kullanıcı kutu sürükledi
      const x = Math.round(Math.min(this.startX, this.currentX));
      const y = Math.round(Math.min(this.startY, this.currentY));
      const w = Math.round(dragDistX);
      const h = Math.round(dragDistY);
      this.boxes.update(list => [...list, { x, y, w, h, label: `Alan #${list.length + 1}` }]);
    } else {
      // AKILLI TIKLAMA (Smart Tap): Tek tıklamada tıklanan noktayı merkez alan 70x70 kutu yerleştir!
      const W = this.img.width || 1280;
      const H = this.img.height || 720;
      const defaultW = Math.round(W * 0.065); // ~70-80px
      const defaultH = Math.round(H * 0.095); // ~60-70px
      const cx = Math.round(this.startX);
      const cy = Math.round(this.startY);

      const x = Math.max(0, Math.min(cx - Math.round(defaultW / 2), W - defaultW));
      const y = Math.max(0, Math.min(cy - Math.round(defaultH / 2), H - defaultH));

      this.boxes.update(list => [...list, { x, y, w: defaultW, h: defaultH, label: 'Tıklanan Alan' }]);
    }

    this.redraw();
  }

  onTouchStart(e: TouchEvent) {
    if (e.touches.length === 1) {
      const coords = this.getCanvasCoords(e.touches[0]);
      this.isDrawing = true;
      this.startX = coords.x;
      this.startY = coords.y;
      this.currentX = coords.x;
      this.currentY = coords.y;
    }
  }

  onTouchMove(e: TouchEvent) {
    if (!this.isDrawing || e.touches.length !== 1) return;
    e.preventDefault();
    const coords = this.getCanvasCoords(e.touches[0]);
    this.currentX = coords.x;
    this.currentY = coords.y;
    this.redraw();
  }

  triggerAutoDetect() {
    const file = this.cleanerService.uploadedFile();
    if (!file) return;

    this.cleanerService.detectWatermarks(file.file_id).subscribe({
      next: (res) => {
        if (res.suggested_boxes && res.suggested_boxes.length > 0) {
          this.boxes.set(res.suggested_boxes);
          this.hasAutoDetected.set(true);
        } else {
          // Bulunamazsa Kling AI şablonunu uygula
          this.setPreset('kling');
        }
        this.redraw();
      }
    });
  }

  setPreset(type: 'kling' | 'tiktok-br' | 'tiktok-tl' | 'bottom-right' | 'top-left' | 'top-right' | 'bottom-left') {
    const W = this.img.width || 1280;
    const H = this.img.height || 720;

    let newBox: Box;
    if (type === 'kling') {
      // Kling AI 4 köşeli yıldızı (Sağ alt köşe, %86 X, %77 Y, %8 W, %11 H)
      newBox = { 
        x: Math.round(W * 0.86), 
        y: Math.round(H * 0.77), 
        w: Math.round(W * 0.08), 
        h: Math.round(H * 0.11), 
        label: 'Kling AI Yıldızı' 
      };
    } else if (type === 'tiktok-br') {
      newBox = { 
        x: Math.round(W * 0.68), 
        y: Math.round(H * 0.74), 
        w: Math.round(W * 0.30), 
        h: Math.round(H * 0.22), 
        label: 'TikTok Sağ Alt' 
      };
    } else if (type === 'tiktok-tl') {
      newBox = { 
        x: Math.round(W * 0.02), 
        y: Math.round(H * 0.02), 
        w: Math.round(W * 0.30), 
        h: Math.round(H * 0.18), 
        label: 'TikTok Sol Üst' 
      };
    } else if (type === 'bottom-right') {
      newBox = { 
        x: Math.round(W * 0.68), 
        y: Math.round(H * 0.70), 
        w: Math.round(W * 0.30), 
        h: Math.round(H * 0.28), 
        label: 'Sağ Alt Köşe' 
      };
    } else if (type === 'top-left') {
      newBox = { 
        x: Math.round(W * 0.02), 
        y: Math.round(H * 0.02), 
        w: Math.round(W * 0.28), 
        h: Math.round(H * 0.18), 
        label: 'Sol Üst Köşe' 
      };
    } else if (type === 'top-right') {
      newBox = { 
        x: Math.round(W * 0.70), 
        y: Math.round(H * 0.02), 
        w: Math.round(W * 0.28), 
        h: Math.round(H * 0.18), 
        label: 'Sağ Üst Köşe' 
      };
    } else {
      newBox = { 
        x: Math.round(W * 0.02), 
        y: Math.round(H * 0.70), 
        w: Math.round(W * 0.28), 
        h: Math.round(H * 0.28), 
        label: 'Sol Alt Köşe' 
      };
    }

    this.boxes.set([newBox]);
    this.redraw();
  }

  removeBox(index: number) {
    this.boxes.update(list => list.filter((_, i) => i !== index));
    this.redraw();
  }

  clearBoxes() {
    this.boxes.set([]);
    this.hasAutoDetected.set(false);
    this.redraw();
  }

  selectRatio(ratio: AspectRatioType) {
    this.cleanerService.selectedRatio.set(ratio);
  }

  setFraming(mode: FramingModeType) {
    this.cleanerService.framingMode.set(mode);
  }

  getAspectRatioCss(ratio: AspectRatioType): string {
    if (ratio === '4:5') return '4 / 5';
    if (ratio === '9:16') return '9 / 16';
    if (ratio === '1:1') return '1 / 1';
    if (ratio === '16:9') return '16 / 9';
    return '16 / 9';
  }

  onProcess() {
    if (this.boxes().length === 0) {
      this.showEmptyModal.set(true);
      return;
    }
    this.cleanerService.processMedia(this.boxes());
  }

  processWithoutWatermark() {
    this.showEmptyModal.set(false);
    this.cleanerService.processMedia([]);
  }

  autoDetectAndProcess() {
    const file = this.cleanerService.uploadedFile();
    if (!file) return;

    this.cleanerService.detectWatermarks(file.file_id).subscribe({
      next: (res) => {
        let selectedBoxes: Box[] = [];
        if (res.suggested_boxes && res.suggested_boxes.length > 0) {
          selectedBoxes = res.suggested_boxes;
        } else {
          // Fallback Kling AI
          const W = this.img.width || 1280;
          const H = this.img.height || 720;
          selectedBoxes = [{
            x: Math.round(W * 0.86),
            y: Math.round(H * 0.77),
            w: Math.round(W * 0.08),
            h: Math.round(H * 0.11),
            label: 'Kling AI Yıldızı'
          }];
        }
        this.boxes.set(selectedBoxes);
        this.redraw();
        this.showEmptyModal.set(false);
        this.cleanerService.processMedia(selectedBoxes);
      }
    });
  }
}
