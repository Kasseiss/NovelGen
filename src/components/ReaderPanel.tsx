import { useRef, useEffect } from 'react';
import { ChevronLeft, ChevronRight, BookOpen } from 'lucide-react';
import { useStore } from '../store';

export default function ReaderPanel() {
  const chapters = useStore((s) => s.chapters);
  const currentChapterId = useStore((s) => s.currentChapterId);
  const setCurrentChapterId = useStore((s) => s.setCurrentChapterId);
  const setView = useStore((s) => s.setView);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = 0;
    }
  }, [currentChapterId]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      const state = useStore.getState();
      const idx = state.chapters.findIndex((c) => c.id === state.currentChapterId);

      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (idx > 0) {
          state.setCurrentChapterId(state.chapters[idx - 1].id);
        }
      } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        if (idx < state.chapters.length - 1) {
          state.setCurrentChapterId(state.chapters[idx + 1].id);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const currentChapter = chapters.find((c) => c.id === currentChapterId);
  const currentIndex = chapters.findIndex((c) => c.id === currentChapterId);
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < chapters.length - 1;

  const handlePrev = () => {
    if (hasPrev) {
      setCurrentChapterId(chapters[currentIndex - 1].id);
    }
  };

  const handleNext = () => {
    if (hasNext) {
      setCurrentChapterId(chapters[currentIndex + 1].id);
    }
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
      <div className="px-4 sm:px-8 py-4 sm:py-6 border-b border-ink-800">
        <h2 className="text-xl sm:text-2xl font-bold text-gold-400 font-serif">
          第{currentChapter.id}章{currentChapter.title ? `：${currentChapter.title}` : ''}
        </h2>
        <p className="text-sm text-ink-600 mt-1">
          {currentChapter.wordCount > 0 ? `${currentChapter.wordCount} 字` : ''}
        </p>
      </div>

      <div ref={contentRef} className="flex-1 overflow-y-auto px-4 sm:px-8 py-4 sm:py-6">
        <div className="max-w-3xl mx-auto reading-content text-ink-100">
          {currentChapter.content.split('\n').map((paragraph, idx) => (
            paragraph.trim() ? (
              <p key={idx}>{paragraph}</p>
            ) : null
          ))}
        </div>
      </div>

      <div className="px-4 sm:px-8 py-3 sm:py-4 border-t border-ink-800">
        <div className="flex items-center justify-between max-w-3xl mx-auto">
          <button
            onClick={handlePrev}
            disabled={!hasPrev}
            className={`flex items-center gap-2 px-3 sm:px-4 py-2 rounded-lg transition-all ${
              hasPrev
                ? 'text-ink-300 hover:text-gold-400 hover:bg-ink-900'
                : 'text-ink-700 cursor-not-allowed'
            }`}
          >
            <ChevronLeft className="w-4 h-4" />
            <span className="hidden sm:inline">上一章</span>
          </button>

          <span className="text-xs text-ink-600">
            {currentIndex + 1} / {chapters.length}
          </span>

          <button
            onClick={handleNext}
            disabled={!hasNext}
            className={`flex items-center gap-2 px-3 sm:px-4 py-2 rounded-lg transition-all ${
              hasNext
                ? 'text-ink-300 hover:text-gold-400 hover:bg-ink-900'
                : 'text-ink-700 cursor-not-allowed'
            }`}
          >
            <span className="hidden sm:inline">下一章</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
