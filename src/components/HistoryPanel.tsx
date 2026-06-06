import { useState, useEffect } from 'react';
import { BookOpen, Plus, Trash2, Loader2, Play, BookMarked } from 'lucide-react';
import { useStore } from '../store';
import { NovelRecord } from '../types';

export default function HistoryPanel() {
  const setView = useStore((s) => s.setView);
  const setSelectedNovel = useStore((s) => s.setSelectedNovel);
  const [records, setRecords] = useState<NovelRecord[]>([]);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  useEffect(() => {
    let stop = false;
    const load = async () => {
      try {
        const resp = await fetch('/api/novels');
        const data = await resp.json();
        if (!stop) setRecords(data);
      } catch {}
    };
    load();
    const timer = setInterval(load, 3000);
    return () => { stop = true; clearInterval(timer); };
  }, []);

  const deleteNovel = async () => {
    if (!confirmDeleteId) return;
    await fetch('/api/novels/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: confirmDeleteId }),
    });
    setConfirmDeleteId(null);
    const resp = await fetch('/api/novels');
    setRecords(await resp.json());
  };

  const openNovel = (item: NovelRecord) => {
    setSelectedNovel(item);
    if (item.status === 'generating' || item.status === 'error') {
      setView('generating');
    } else {
      setView('reading');
    }
  };

  return (
    <div className="w-full h-full flex flex-col">
      <div className="px-4 sm:px-6 py-4 border-b border-ink-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BookOpen className="w-5 h-5 text-gold-400" />
          <h2 className="text-lg font-medium text-ink-100">我的书架</h2>
          {records.length > 0 && (
            <span className="text-sm text-ink-500">{records.length} 部作品</span>
          )}
        </div>
        <button
          onClick={() => setView('config')}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gold-400/10 hover:bg-gold-400/20 text-gold-400 rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />写新作品
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
        {records.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-ink-600">
            <BookMarked className="w-16 h-16 mb-4 opacity-30" />
            <p className="text-lg mb-2">书架空空如也</p>
            <p className="text-sm text-ink-700 mb-6">点击上方"写新作品"开始你的第一部小说</p>
            <button
              onClick={() => setView('config')}
              className="flex items-center gap-2 px-6 py-3 bg-gold-400/10 hover:bg-gold-400/20 text-gold-400 rounded-xl transition-colors"
            >
              <Plus className="w-4 h-4" />开始创作
            </button>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-4">
            {records.map((record) => {
              const totalWords = record.chapters.reduce((s, c) => s + c.wordCount, 0);
              const completedChapters = record.chapters.filter((x) => x.status === 'completed').length;
              const targetChapters = record.chapterCount || 500;
              const isGenerating = record.status === 'generating';
              const progress = Math.min(100, (completedChapters / targetChapters) * 100);

              return (
                <div
                  key={record.id}
                  onClick={() => openNovel(record)}
                  style={{ touchAction: 'manipulation' }}
                  className={`group p-5 rounded-xl border cursor-pointer transition-all active:scale-[0.98] ${
                    isGenerating
                      ? 'bg-amber-400/5 border-amber-400/20 hover:border-amber-400/40'
                      : record.status === 'error'
                      ? 'bg-red-500/5 border-red-500/20 hover:border-red-500/40'
                      : 'bg-ink-900/50 border-ink-800 hover:border-ink-700 hover:bg-ink-900/80'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        {isGenerating && <Loader2 className="w-4 h-4 text-amber-400 animate-spin shrink-0" />}
                        {record.status === 'completed' && <div className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />}
                        {record.status === 'error' && <div className="w-2 h-2 rounded-full bg-red-500 shrink-0" />}
                        <h3 className="text-ink-100 font-medium truncate">{record.theme.slice(0, 60)}</h3>
                      </div>

                      <div className="flex items-center gap-4 text-xs text-ink-500 mb-3">
                        {isGenerating ? <span className="text-amber-400">正在后台生成...</span> : record.status === 'error' ? <span className="text-red-400">生成失败</span> : <span>{record.updatedAt}</span>}
                        <span>{completedChapters} 章</span>
                        <span>{totalWords.toLocaleString()} 字</span>
                        <span>{record.chapterCount > 0 ? `${record.chapterCount} 章目标` : '无限模式'}</span>
                      </div>

                      {isGenerating && (
                        <div className="mb-3">
                          <div className="w-full h-1.5 bg-ink-800 rounded-full overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-amber-500 to-amber-400 rounded-full transition-all" style={{ width: `${progress}%` }} />
                          </div>
                          <p className="text-xs text-ink-600 mt-1">{record.chapterCount > 0 ? `已完成 ${completedChapters}/${record.chapterCount} 章` : `已完成 ${completedChapters} 章`}</p>
                        </div>
                      )}

                      {record.chapters.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {record.chapters.slice(0, 6).map((ch) => (
                            <span key={ch.id} className="text-xs text-ink-500 bg-ink-800/80 px-2 py-0.5 rounded">
                              {ch.id}. {ch.title ? ch.title.slice(0, 8) : `第${ch.id}章`}
                            </span>
                          ))}
                          {record.chapters.length > 6 && <span className="text-xs text-ink-600">+{record.chapters.length - 6}</span>}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2 shrink-0 pointer-events-none opacity-60 group-hover:opacity-100 transition-opacity">
                      {isGenerating ? (
                        <div className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-amber-400/15 text-amber-400 rounded-lg">
                          <Play className="w-3 h-3" />查看
                        </div>
                      ) : completedChapters > 0 ? (
                        <div className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-gold-400/10 text-gold-400 rounded-lg">
                          <BookOpen className="w-3 h-3" />阅读
                        </div>
                      ) : null}
                      <button
                        onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(record.id); }}
                        className="pointer-events-auto p-1.5 text-ink-700 hover:text-red-400 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {confirmDeleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setConfirmDeleteId(null)} />
          <div className="relative bg-ink-900 border border-ink-800 rounded-xl p-6 mx-4 max-w-sm w-full shadow-xl">
            <h3 className="text-ink-100 font-medium mb-2">确认删除</h3>
            <p className="text-ink-400 text-sm mb-6">确定要删除这部作品吗？删除后无法恢复。</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setConfirmDeleteId(null)} className="px-4 py-2 text-sm text-ink-300 bg-ink-800 rounded-lg">取消</button>
              <button onClick={deleteNovel} className="px-4 py-2 text-sm text-white bg-red-500/80 rounded-lg">确认删除</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
