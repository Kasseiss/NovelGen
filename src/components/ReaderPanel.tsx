import { useRef, useEffect, useCallback } from 'react';
import { ChevronLeft, ChevronRight, BookOpen, RotateCcw, Loader2 } from 'lucide-react';
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
  }, [currentChapterId]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); goToPrev(); }
      else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); goToNext(); }
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
    <div className="w-full h-full flex flex-col">
      <div className="px-3 sm:px-8 py-3 sm:py-4 border-b border-ink-800 shrink-0">
        <div className="flex items-center justify-between gap-2">
          <button
            onClick={goToPrev}
            disabled={!hasPrev}
            className={`p-2 sm:px-3 sm:py-2 rounded-lg transition-all shrink-0 ${hasPrev ? 'text-ink-300 hover:text-gold-400 hover:bg-ink-900 active:bg-ink-800' : 'text-ink-700 cursor-not-allowed'}`}
          >
            <ChevronLeft className="w-5 h-5" />
          </button>

          <div className="flex-1 min-w-0 text-center">
            <h2 className="text-base sm:text-2xl font-bold text-gold-400 font-serif truncate">
              第{currentChapter.id}章{currentChapter.title ? `：${currentChapter.title}` : ''}
            </h2>
            <div className="flex items-center justify-center gap-3 mt-0.5">
              <span className="text-xs text-ink-600">{completedIndex + 1} / {completedChapters.length}</span>
              {currentChapter.wordCount > 0 && <span className="text-xs text-ink-600">{currentChapter.wordCount} 字</span>}
              <button
                onClick={handleRegenChapter}
                className="text-xs text-ink-600 hover:text-gold-400 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5 inline" />
              </button>
            </div>
          </div>

          <button
            onClick={goToNext}
            disabled={!hasNext}
            className={`p-2 sm:px-3 sm:py-2 rounded-lg transition-all shrink-0 ${hasNext ? 'text-ink-300 hover:text-gold-400 hover:bg-ink-900 active:bg-ink-800' : 'text-ink-700 cursor-not-allowed'}`}
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      <div
        ref={contentRef}
        className="flex-1 overflow-y-auto px-4 sm:px-8 py-4 sm:py-6"
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        <div className="max-w-3xl mx-auto reading-content text-ink-100">
          {currentChapter.content.split('\n').map((paragraph, idx) => (
            paragraph.trim() ? <p key={idx}>{paragraph}</p> : null
          ))}
        </div>
      </div>
    </div>
  );
}
