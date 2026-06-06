import { useRef, useEffect, useCallback, useState } from 'react';
import { ChevronLeft, ChevronRight, BookOpen, RotateCcw, Loader2, X } from 'lucide-react';
import { useStore } from '../store';

export default function ReaderPanel() {
  const chapters = useStore((s) => s.chapters);
  const currentChapterId = useStore((s) => s.currentChapterId);
  const setCurrentChapterId = useStore((s) => s.setCurrentChapterId);
  const setView = useStore((s) => s.setView);
  const currentRecordId = useStore((s) => s.currentRecordId);
  const setSelectedNovel = useStore((s) => s.setSelectedNovel);
  const contentRef = useRef<HTMLDivElement>(null);
  const touchStartX = useRef<number | null>(null);
  const [showControls, setShowControls] = useState(false);

  const completedChapters = chapters.filter(c => c.status === 'completed');
  const completedIndex = completedChapters.findIndex((c) => c.id === currentChapterId);

  const goToPrev = useCallback(() => {
    if (completedIndex > 0) setCurrentChapterId(completedChapters[completedIndex - 1].id);
  }, [completedIndex, completedChapters, setCurrentChapterId]);

  const goToNext = useCallback(() => {
    if (completedIndex < completedChapters.length - 1) setCurrentChapterId(completedChapters[completedIndex + 1].id);
  }, [completedIndex, completedChapters, setCurrentChapterId]);

  useEffect(() => {
    if (contentRef.current) contentRef.current.scrollTop = 0;
    setShowControls(false);
  }, [currentChapterId]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === 'ArrowLeft') { e.preventDefault(); goToPrev(); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); goToNext(); }
      else if (e.key === 'Escape') setShowControls(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [goToPrev, goToNext]);

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX.current === null) return;
    const dx = e.changedTouches[0].clientX - touchStartX.current;
    touchStartX.current = null;
    if (Math.abs(dx) < 60) return;
    if (dx > 0) goToPrev();
    else goToNext();
  };

  const handleAreaClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const ratio = x / rect.width;
    if (ratio < 0.35) goToPrev();
    else if (ratio > 0.65) goToNext();
    else setShowControls((v) => !v);
  };

  const currentChapter = chapters.find((c) => c.id === currentChapterId);
  const hasPrev = completedIndex > 0;
  const hasNext = completedIndex < completedChapters.length - 1;

  const handleRegenChapter = async () => {
    if (!currentRecordId || !currentChapterId) return;
    try {
      await fetch('/api/novels/regenerate-chapter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ novelId: currentRecordId, chapterId: currentChapterId }),
      });
      const novel = useStore.getState().selectedNovel;
      if (novel) setSelectedNovel({ ...novel, status: 'generating', error: '', chapters: novel.chapters.map((c) => c.id === currentChapterId ? { ...c, status: 'writing' as const, content: '', wordCount: 0 } : c) });
      setView('generating');
    } catch {}
  };

  if (!currentChapter) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-ink-600">
        <BookOpen className="w-12 h-12 mb-4 opacity-50" />
        <p>请选择一章阅读</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col relative">
      <div
        ref={contentRef}
        className="flex-1 overflow-y-auto px-5 sm:px-8 py-6 sm:py-8 cursor-pointer select-none"
        onClick={handleAreaClick}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        <div className="max-w-3xl mx-auto reading-content text-ink-100">
          <h2 className="text-lg sm:text-2xl font-bold text-gold-400 font-serif mb-4 sm:mb-6">
            第{currentChapter.id}章{currentChapter.title ? `：${currentChapter.title}` : ''}
          </h2>
          {currentChapter.content.split('\n').map((paragraph, idx) => (
            paragraph.trim() ? <p key={idx}>{paragraph}</p> : null
          ))}
        </div>
      </div>

      {showControls && (
        <div className="absolute inset-0 z-50 flex flex-col" onClick={() => setShowControls(false)}>
          <div className="absolute inset-0 bg-black/60" />

          <div className="relative flex-1 flex items-center justify-center px-6">
            <div className="flex items-center gap-6 sm:gap-10">
              <button
                onClick={(e) => { e.stopPropagation(); goToPrev(); }}
                disabled={!hasPrev}
                className={`p-4 sm:p-5 rounded-full transition-all ${hasPrev ? 'bg-white/10 text-white hover:bg-white/20 active:bg-white/30' : 'bg-white/5 text-white/30 cursor-not-allowed'}`}
              >
                <ChevronLeft className="w-7 h-7 sm:w-8 sm:h-8" />
              </button>

              <div className="text-center text-white min-w-[120px]">
                <p className="text-sm opacity-70">{completedIndex + 1} / {completedChapters.length}</p>
                {currentChapter.wordCount > 0 && <p className="text-xs opacity-50 mt-1">{currentChapter.wordCount} 字</p>}
              </div>

              <button
                onClick={(e) => { e.stopPropagation(); goToNext(); }}
                disabled={!hasNext}
                className={`p-4 sm:p-5 rounded-full transition-all ${hasNext ? 'bg-white/10 text-white hover:bg-white/20 active:bg-white/30' : 'bg-white/5 text-white/30 cursor-not-allowed'}`}
              >
                <ChevronRight className="w-7 h-7 sm:w-8 sm:h-8" />
              </button>
            </div>
          </div>

          <div className="relative flex items-center justify-between px-4 sm:px-8 py-4 sm:py-5 bg-black/60">
            <button
              onClick={(e) => { e.stopPropagation(); setView('history'); }}
              className="flex items-center gap-2 px-3 py-2 text-white/80 hover:text-white text-sm rounded-lg hover:bg-white/10 transition-colors"
            >
              <BookOpen className="w-4 h-4" />
              <span className="hidden sm:inline">书架</span>
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); handleRegenChapter(); }}
              className="flex items-center gap-2 px-3 py-2 text-white/80 hover:text-white text-sm rounded-lg hover:bg-white/10 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              <span className="hidden sm:inline">重新生成</span>
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); setShowControls(false); }}
              className="flex items-center gap-2 px-3 py-2 text-white/80 hover:text-white text-sm rounded-lg hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4" />
              <span className="hidden sm:inline">关闭</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
