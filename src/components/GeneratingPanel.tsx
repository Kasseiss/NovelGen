import { useEffect, useState } from 'react';
import { useStore } from '../store';
import { Loader2, Sparkles, AlertCircle, FileText, BookOpen, RotateCcw, Eye } from 'lucide-react';
import { NovelRecord } from '../types';

export default function GeneratingPanel() {
  const currentRecordId = useStore((s) => s.currentRecordId);
  const setSelectedNovel = useStore((s) => s.setSelectedNovel);
  const setCurrentChapterId = useStore((s) => s.setCurrentChapterId);
  const setView = useStore((s) => s.setView);
  const chapters = useStore((s) => s.chapters);
  const novelConfig = useStore((s) => s.novelConfig);

  const [remote, setRemote] = useState<NovelRecord | null>(null);

  useEffect(() => {
    if (!currentRecordId) return;
    let stop = false;
    const load = async () => {
      try {
        const resp = await fetch(`/api/novels/${currentRecordId}`);
        const data: NovelRecord = await resp.json();
        if (stop) return;
        setRemote(data);
        setSelectedNovel(data);
      } catch {}
    };
    load();
    const timer = setInterval(load, 3000);
    return () => { stop = true; clearInterval(timer); };
  }, [currentRecordId, setSelectedNovel]);

  const localChapters = chapters.length ? chapters : remote?.chapters || [];
  const completedCount = localChapters.filter((c) => c.status === 'completed').length;
  const totalWordCount = localChapters.reduce((sum, c) => sum + c.wordCount, 0);
  const progress = novelConfig.chapterCount > 0 ? Math.min(100, (completedCount / novelConfig.chapterCount) * 100) : 0;
  const currentChapter = localChapters.find((c) => c.status === 'writing' || c.status === 'planning');
  const isGenerating = (remote?.status || useStore.getState().selectedNovel?.status) === 'generating';

  const handleReadChapter = (chapterId: number) => {
    setCurrentChapterId(chapterId);
    setView('reading');
  };

  return (
    <div className="w-full h-full flex flex-col">
      <div className="px-4 sm:px-6 py-4 border-b border-ink-800">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3 min-w-0">
            {isGenerating ? (
              <>
                <Loader2 className="w-5 h-5 text-gold-400 animate-spin shrink-0" />
                <span className="text-gold-400 font-medium truncate">
                  第 {currentChapter?.id || completedCount + 1} 章 - {currentChapter?.status === 'planning' ? '生成大纲中' : '正在写作中'}...
                </span>
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5 text-emerald-400 shrink-0" />
                <span className="text-emerald-400 font-medium">{completedCount > 0 ? '生成完成' : '准备就绪'}</span>
              </>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {completedCount > 0 && (
              <button onClick={() => setView('reading')} className="flex items-center gap-1.5 px-3 sm:px-4 py-2 bg-gold-400/10 hover:bg-gold-400/20 text-gold-400 rounded-lg text-sm">
                <Eye className="w-4 h-4" /><span className="hidden sm:inline">阅读</span>
              </button>
            )}
            <button onClick={() => setView('history')} className="flex items-center gap-1.5 px-3 sm:px-4 py-2 bg-ink-800 hover:bg-ink-700 text-ink-300 rounded-lg text-sm">
              <BookOpen className="w-4 h-4" /><span className="hidden sm:inline">书架</span>
            </button>
            {!isGenerating && (
              <button onClick={() => setView('config')} className="flex items-center gap-1.5 px-3 sm:px-4 py-2 bg-ink-800 hover:bg-ink-700 text-ink-300 rounded-lg text-sm">
                <RotateCcw className="w-4 h-4" /><span className="hidden sm:inline">配置</span>
              </button>
            )}
          </div>
        </div>
        <div className="w-full h-2 bg-ink-800 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-gold-600 to-gold-400 rounded-full transition-all" style={{ width: `${progress}%` }} />
        </div>
        <div className="flex justify-between mt-2 text-xs text-ink-500">
          <span>{novelConfig.chapterCount > 0 ? `已完成 ${completedCount}/${novelConfig.chapterCount} 章` : `已完成 ${completedCount} 章`}</span>
          <span>总字数: {totalWordCount.toLocaleString()}</span>
        </div>
      </div>

      {remote?.error && (
        <div className="mx-4 sm:mx-6 mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />{remote.error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4">
        {localChapters.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-ink-600">
            <Loader2 className="w-8 h-8 animate-spin mb-3" />
            <p>正在准备生成...</p>
          </div>
        ) : (
          <div className="space-y-4 max-w-2xl mx-auto">
            {localChapters.map((chapter) => (
              <div
                key={chapter.id}
                className={`p-4 rounded-xl border ${
                  chapter.status === 'writing' ? 'bg-gold-400/5 border-gold-400/20' :
                  chapter.status === 'completed' ? 'bg-ink-900/50 border-ink-800 hover:border-gold-400/30 cursor-pointer' :
                  'bg-ink-900/30 border-ink-800/50'
                }`}
                onClick={() => chapter.status === 'completed' && handleReadChapter(chapter.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    {chapter.status === 'writing' && <Loader2 className="w-4 h-4 text-gold-400 animate-spin" />}
                    {chapter.status === 'completed' && <div className="w-2 h-2 rounded-full bg-emerald-500" />}
                    <span className={`${chapter.status === 'completed' ? 'text-ink-200' : 'text-gold-400'} truncate`}>
                      第{chapter.id}章{chapter.title ? `：${chapter.title}` : ''}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {chapter.status === 'completed' && (
                      <Eye className="w-3.5 h-3.5 text-ink-600" />
                    )}
                    {chapter.status === 'completed' && <span className="text-xs text-ink-500">{chapter.wordCount} 字</span>}
                  </div>
                </div>
                {chapter.status === 'writing' && <p className="text-sm text-ink-500 mt-2">正在写作中...</p>}
                {chapter.plan && (
                  <div className="mt-2 p-2 bg-ink-950/50 rounded-lg">
                    <div className="flex items-center gap-1.5 text-xs text-amber-400/70 mb-1">
                      <FileText className="w-3 h-3" />大纲
                    </div>
                    <p className="text-xs text-ink-400 leading-relaxed">{chapter.plan}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
