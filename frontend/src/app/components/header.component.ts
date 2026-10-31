import { Component, ChangeDetectionStrategy } from '@angular/core';

@Component({
  selector: 'app-header',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-lg sticky top-0 z-50">
      <div class="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 via-teal-500 to-indigo-600 flex items-center justify-center shadow-md shadow-cyan-500/20">
            <i class="fa-solid fa-eraser text-white text-xs"></i>
          </div>
          <div class="flex items-center gap-2">
            <span class="font-bold text-base bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-transparent">
              CleanMark AI
            </span>
            <span class="text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-1.5 py-0.5 rounded-full font-semibold">
              Watermark Eraser
            </span>
          </div>
        </div>

        <div class="flex items-center gap-2 text-xs text-slate-400">
          <span class="flex items-center gap-1 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-lg">
            <i class="fa-regular fa-image text-cyan-400"></i> Resim & Video Inpainter
          </span>
        </div>
      </div>
    </header>
  `
})
export class HeaderComponent {}
