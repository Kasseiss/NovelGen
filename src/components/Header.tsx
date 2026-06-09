import { BookOpen, Download, Settings, Clock, FileText, LogOut } from 'lucide-react';
import { useStore } from '../store';

export default function Header() {
  const chapters = useStore((s) => s.chapters);
  const view = useStore((s) => s.view);
  const setView = useStore((s) => s.setView);
  const isGenerating = useStore((s) => s.isGenerating);
  const theme = useStore((s) => s.novelConfig.theme);
  const username = useStore((s) => s.username);
  const logout = useStore((s) => s.logout);

  const handleExportTXT = () => {
    if (chapters.length === 0) return;

    const content = chapters
      .filter((c) => c.status === 'completed')
      .map((c) => `第${c.id}章：${c.title}\n\n${c.content}\n\n`)
      .join('---\n\n');

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const safeName = theme.slice(0, 20).replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '_');
    a.download = `${safeName || '小说'}_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const completedChapters = chapters.filter((c) => c.status === 'completed');
  const totalWordCount = completedChapters.reduce((sum, c) => sum + c.wordCount, 0);

  return (
    <header className="h-14 bg-ink-950 border-b border-ink-800 flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-3 min-w-0">
        <BookOpen className="w-5 h-5 text-gold-400 shrink-0" />
        <span className="font-serif font-bold text-ink-100 shrink-0">墨流</span>
        {completedChapters.length > 0 && (
          <span className="text-xs text-ink-500 hidden sm:inline">
            {completedChapters.length} 章 · {totalWordCount.toLocaleString()} 字
          </span>
        )}
      </div>

      <div className="flex items-center gap-1 sm:gap-2">
        <button
          onClick={() => setView('history')}
          className={`flex items-center gap-1.5 px-2 sm:px-3 py-1.5 text-xs sm:text-sm rounded-lg transition-all ${
            view === 'history'
              ? 'text-gold-400 bg-gold-400/10'
              : 'text-ink-400 hover:text-gold-400 hover:bg-ink-900'
          }`}
        >
          <Clock className="w-4 h-4" />
          <span className="hidden sm:inline">书架</span>
        </button>

        {view === 'reading' && (
          <button
            onClick={() => setView('generating')}
            className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 text-xs sm:text-sm text-ink-400 hover:text-gold-400 hover:bg-ink-900 rounded-lg transition-all"
          >
            <FileText className="w-4 h-4" />
            <span className="hidden sm:inline">生成视图</span>
          </button>
        )}

        {completedChapters.length > 0 && (
          <button
            onClick={handleExportTXT}
            className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 text-xs sm:text-sm text-ink-400 hover:text-gold-400 hover:bg-ink-900 rounded-lg transition-all"
          >
            <Download className="w-4 h-4" />
            <span className="hidden sm:inline">导出</span>
          </button>
        )}

        {!isGenerating && view !== 'config' && view !== 'history' && (
          <button
            onClick={() => setView('config')}
            className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 text-xs sm:text-sm text-ink-400 hover:text-gold-400 hover:bg-ink-900 rounded-lg transition-all"
          >
            <Settings className="w-4 h-4" />
            <span className="hidden sm:inline">新作品</span>
          </button>
        )}

        {username && (
          <div className="flex items-center gap-2 ml-1 pl-1 sm:ml-2 sm:pl-2 border-l border-ink-800">
            <span className="text-xs text-ink-500 hidden sm:inline">{username}</span>
            <button
              onClick={logout}
              className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 text-xs sm:text-sm text-ink-400 hover:text-gold-400 hover:bg-ink-900 rounded-lg transition-all"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">登出</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
