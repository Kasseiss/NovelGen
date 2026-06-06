import { useRef, useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, BookOpen, RotateCcw, Loader2 } from 'lucide-react';
import { useStore } from '../store';

export default function ReaderPanel() {
  const chapters = useStore((s) => s.chapters);
  const setView = useStore((s) => s.setView);
  const currentRecordId = useStore((s) => s.currentRecordId);
  const setSelectedNovel = useStore((s) => s.setSelectedNovel);
  const contentRef = useRef<HTMLDivElement>(null);
  const [currentChapterId, setCurrentChapterId] = useState<number>(chapters.length ? chapters[0].id : 0);
  const [regeneratingId, setRegeneratingId] = useState<number | null>(null);

  useEffect(() => {
    if (chapters.length) {
      setCurrentChapterId((prev) => (prev ? prev : chapters[0].id));
    }
  }, [chapters]);

  useEffect(() => {
    if (contentRef.current) contentRef.current.scrollTop = 0;
  }, [currentChapterId]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      const idx = chapters.findIndex((c) => c.id === currentChapterId);
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (idx > 0) setCurrentChapterId(chapters[idx - 1].id);
      } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        if (idx < chapters.length - 1) setCurrentChapterId(chapters[idx + 1].id);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [chapters, currentChapterId]);

  const currentChapter = chapters.find((c) => c.id === currentChapterId);
  const currentIndex = chapters.findIndex((c) => c.id === currentChapterId);
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < chapters.length - 1;

  const handleRegenChapter = async () => {
    if (!currentRecordId || !currentChapterId || regeneratingId) return;
    setRegeneratingId(currentChapterId);
    try {
      await fetch('/api/novels/regenerate-chapter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ novelId: currentRecordId, chapterId: currentChapterId }),
      });
      const novel = useStore.getState().selectedNovel;
      if (novel) setSelectedNovel({ ...novel, status: 'generating', error: '', chapters: novel.chapters.map((c) => c.id === currentChapterId ? { ...c, status: 'writing' as const, content: '', wordCount: 0 } : c) });
      setView('generating');
      setRegeneratingId(null);
    } catch {
      setRegeneratingId(null);
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
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-xl sm:text-2xl font-bold text-gold-400 font-serif">
              第{currentChapter.id}章{currentChapter.title ? `：${currentChapter.title}` : ''}
            </h2>
            <p className="text-sm text-ink-600 mt-1">{currentChapter.wordCount > 0 ? `${currentChapter.wordCount} 字` : ''}</p>
          </div>
          <button
            onClick={handleRegenChapter}
            disabled={regeneratingId !== null}
            className="flex items-center gap-1.5 px-3 py-2 bg-ink-800 hover:bg-ink-700 text-ink-300 hover:text-gold-400 rounded-lg text-sm transition-all shrink-0 disabled:opacity-50"
          >
            {regeneratingId ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
            <span className="hidden sm:inline">重新生成</span>
          </button>
        </div>
      </div>

      <div ref={contentRef} className="flex-1 overflow-y-auto px-4 sm:px-8 py-4 sm:py-6">
        <div className="max-w-3xl mx-auto reading-content text-ink-100">
          {currentChapter.content.split('\n').map((paragraph, idx) => (
            paragraph.trim() ? <p key={idx}>{paragraph}</p> : null
          ))}
        </div>
      </div>

      <div className="px-4 sm:px-8 py-3 sm:py-4 border-t border-ink-800">
        <div className="flex items-center justify-between max-w-3xl mx-auto">
          <button onClick={() => hasPrev && setCurrentChapterId(chapters[currentIndex - 1].id)} disabled={!hasPrev} className={`flex items-center gap-2 px-3 sm:px-4 py-2 rounded-lg transition-all ${hasPrev ? 'text-ink-300 hover:text-gold-400 hover:bg-ink-900' : 'text-ink-700 cursor-not-allowed'}`}>
            <ChevronLeft className="w-4 h-4" /><span className="hidden sm:inline">上一章</span>
          </button>
          <span className="text-xs text-ink-600">{currentIndex + 1} / {chapters.length}</span>
          <button onClick={() => hasNext && setCurrentChapterId(chapters[currentIndex + 1].id)} disabled={!hasNext} className={`flex items-center gap-2 px-3 sm:px-4 py-2 rounded-lg transition-all ${hasNext ? 'text-ink-300 hover:text-gold-400 hover:bg-ink-900' : 'text-ink-700 cursor-not-allowed'}`}>
            <span className="hidden sm:inline">下一章</span><ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
