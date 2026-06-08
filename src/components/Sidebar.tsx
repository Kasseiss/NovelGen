import { BookOpen, ChevronLeft, ChevronRight, FileText, AlertCircle, Loader2, Eye, Menu } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useStore } from '../store';

function SidebarContent() {
  const chapters = useStore((s) => s.chapters);
  const currentChapterId = useStore((s) => s.currentChapterId);
  const setSidebarCollapsed = useStore((s) => s.setSidebarCollapsed);
  const setCurrentChapterId = useStore((s) => s.setCurrentChapterId);
  const setView = useStore((s) => s.setView);

  const handleChapterClick = (id: number) => {
    const chapter = chapters.find((c) => c.id === id);
    if (chapter?.status === 'completed') {
      setCurrentChapterId(id);
      setView('reading');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <div className="w-2 h-2 rounded-full bg-emerald-500" />;
      case 'pending':
        return <div className="w-2 h-2 rounded-full bg-ink-600" />;
      case 'planning':
        return <Loader2 className="w-3 h-3 text-amber-400 animate-spin" />;
      case 'writing':
        return <Loader2 className="w-3 h-3 text-gold-400 animate-spin" />;
      case 'error':
        return <AlertCircle className="w-3 h-3 text-red-400" />;
      default:
        return <div className="w-2 h-2 rounded-full bg-ink-700" />;
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-ink-950">
      <div className="flex items-center justify-between px-4 py-3 border-b border-ink-800">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-gold-400" />
          <span className="text-sm font-medium text-ink-200">章节列表</span>
        </div>
        <button onClick={() => setSidebarCollapsed(true)} className="p-1 text-ink-500 hover:text-gold-400 transition-colors">
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto py-2">
        {chapters.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-ink-600">
            <FileText className="w-8 h-8 mb-2 opacity-50" />
            <p className="text-sm">暂无章节</p>
          </div>
        ) : (
          <div className="space-y-1 px-2">
            {chapters.map((chapter) => (
              <div
                key={chapter.id}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                  chapter.id === currentChapterId
                    ? 'bg-gold-400/10 border border-gold-400/20'
                    : 'border border-transparent'
                } ${chapter.status === 'completed' ? 'hover:bg-ink-900 cursor-pointer' : ''}`}
                onClick={() => handleChapterClick(chapter.id)}
              >
                {getStatusIcon(chapter.status)}
                <div className="flex-1 min-w-0">
                  <p className={`text-sm truncate ${chapter.id === currentChapterId ? 'text-gold-400' : 'text-ink-300'}`}>
                    第{chapter.id}章
                  </p>
                  <p className="text-xs text-ink-600 truncate">
                    {chapter.title || (chapter.status === 'planning' ? '规划中...' : chapter.status === 'writing' ? '写作中...' : chapter.status === 'pending' ? '等待生成' : '等待生成')}
                  </p>
                </div>
                {chapter.status === 'completed' && <Eye className="w-3.5 h-3.5 text-ink-600" />}
                {chapter.wordCount > 0 && <span className="text-xs text-ink-600 shrink-0">{chapter.wordCount}字</span>}
              </div>
            ))}
          </div>
        )}
      </div>
      {chapters.length > 0 && (
        <div className="px-4 py-3 border-t border-ink-800">
          <div className="flex justify-between text-xs text-ink-500">
            <span>共 {chapters.length} 章</span>
            <span>{chapters.reduce((sum, ch) => sum + ch.wordCount, 0).toLocaleString()} 字</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Sidebar() {
  const sidebarCollapsed = useStore((s) => s.sidebarCollapsed);
  const setSidebarCollapsed = useStore((s) => s.setSidebarCollapsed);
  const chapters = useStore((s) => s.chapters);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (sidebarCollapsed) {
      setMobileOpen(false);
    }
  }, [sidebarCollapsed]);

  return (
    <>
      {/* Mobile trigger */}
      {sidebarCollapsed && chapters.length > 0 && (
        <button
          onClick={() => setMobileOpen(true)}
          className="md:hidden fixed bottom-4 left-4 z-40 p-3 bg-gold-400/20 hover:bg-gold-400/30 text-gold-400 rounded-full shadow-lg"
        >
          <Menu className="w-5 h-5" />
        </button>
      )}

      {/* Desktop expand trigger */}
      {sidebarCollapsed && chapters.length > 0 && (
        <button
          onClick={() => setSidebarCollapsed(false)}
          className="hidden md:flex fixed left-0 top-1/2 -translate-y-1/2 z-30 p-2 bg-ink-900 border border-ink-800 hover:border-gold-400/30 hover:text-gold-400 text-ink-400 rounded-r-lg transition-colors"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      )}

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <div className="absolute left-0 top-0 bottom-0 w-72">
            <SidebarContent />
          </div>
        </div>
      )}

      {/* Desktop sidebar */}
      {!sidebarCollapsed && (
        <div className="hidden md:flex w-72 border-r border-ink-800 flex-col shrink-0">
          <SidebarContent />
        </div>
      )}
    </>
  );
}
