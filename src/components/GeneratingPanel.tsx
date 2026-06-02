import { useStore } from '../store';
import { stopGeneration } from './GenerationRunner';
import { Pause, RotateCcw, Loader2, Sparkles, AlertCircle, FileText, Play, RefreshCw, BookOpen } from 'lucide-react';
import { generateChapterPlan, generateChapterContent, parseChapterContent, countChineseWords } from '../utils/api';

export default function GeneratingPanel() {
  const novelConfig = useStore((s) => s.novelConfig);
  const chapters = useStore((s) => s.chapters);
  const isGenerating = useStore((s) => s.isGenerating);
  const error = useStore((s) => s.error);
  const currentNum = useStore((s) => s.currentChapterId) || chapters.length;

  const handleStop = () => {
    stopGeneration();
    useStore.getState().setView('history');
  };

  const handleContinue = () => {
    useStore.getState().setIsGenerating(true);
    useStore.getState().setShouldStop(false);
  };

  const handleRegenerate = async (chapterId: number) => {
    useStore.getState().setIsGenerating(true);
    useStore.getState().setError(null);

    useStore.getState().updateChapter(chapterId, { title: '', content: '', wordCount: 0, plan: '', status: 'planning' });

    const state = useStore.getState();
    const prev = state.chapters.filter((c) => c.status === 'completed' && c.id < chapterId).slice(-2)
      .map((c) => `第${c.id}章「${c.title}」：${c.content.slice(-300)}`).join('\n\n');

    try {
      const { title, plan } = await generateChapterPlan(
        state.apiConfig, state.novelConfig.theme,
        chapterId, state.novelConfig.chapterCount, prev
      );

      useStore.getState().updateChapter(chapterId, { title, plan, status: 'writing' });

      const fullContent = await generateChapterContent(
        state.apiConfig, state.novelConfig.theme,
        chapterId, state.novelConfig.chapterCount, state.novelConfig.wordsPerChapter,
        plan, prev, state.apiConfig.systemPrompt
      );

      const { title: parsedTitle, content } = parseChapterContent(fullContent);
      const wordCount = countChineseWords(content);

      useStore.getState().updateChapter(chapterId, { title: parsedTitle || title, content, wordCount, status: 'completed' });
    } catch (err) {
      const msg = err instanceof Error ? err.message : '重新生成失败';
      useStore.getState().updateChapter(chapterId, { status: 'error' });
      useStore.getState().setError(msg);
    }

    useStore.getState().setIsGenerating(false);
    useStore.getState().setShouldStop(false);
  };

  const handleReset = () => {
    useStore.getState().setShouldStop(true);
    useStore.getState().setIsGenerating(false);
    useStore.getState().setView('config');
  };

  const completedCount = chapters.filter((c) => c.status === 'completed').length;
  const totalWordCount = chapters.reduce((sum, c) => sum + c.wordCount, 0);
  const progress = novelConfig.chapterCount > 0 ? Math.min(100, (completedCount / novelConfig.chapterCount) * 100) : 0;
  const canContinue = !isGenerating && chapters.length > 0 &&
    (novelConfig.chapterCount > 0 ? chapters.length < novelConfig.chapterCount : chapters.length < 500);
  const currentChapter = chapters.find((c) => c.status === 'planning' || c.status === 'writing');

  return (
    <div className="w-full h-full flex flex-col">
      <div className="px-4 sm:px-6 py-4 border-b border-ink-800">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3 min-w-0">
            {isGenerating ? (
              <>
                <Loader2 className="w-5 h-5 text-gold-400 animate-spin shrink-0" />
                <span className="text-gold-400 font-medium truncate">
                  第 {currentChapter?.id || currentNum} 章 - {currentChapter?.status === 'planning' ? '生成大纲中' : '正在写作中'}...
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
            {isGenerating && (
              <button onClick={handleStop} className="flex items-center gap-1.5 px-3 sm:px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg text-sm">
                <Pause className="w-4 h-4" /><span className="hidden sm:inline">停止生成</span>
              </button>
            )}
            {!isGenerating && canContinue && (
              <button onClick={handleContinue} className="flex items-center gap-1.5 px-3 sm:px-4 py-2 bg-gold-400/20 hover:bg-gold-400/30 text-gold-400 rounded-lg text-sm">
                <Play className="w-4 h-4" /><span className="hidden sm:inline">继续生成</span>
              </button>
            )}
            <button onClick={handleReset} className="flex items-center gap-1.5 px-3 sm:px-4 py-2 bg-ink-800 hover:bg-ink-700 text-ink-300 rounded-lg text-sm">
              <RotateCcw className="w-4 h-4" /><span className="hidden sm:inline">配置</span>
            </button>
            <button onClick={() => useStore.getState().setView('history')} className="flex items-center gap-1.5 px-3 sm:px-4 py-2 bg-ink-800 hover:bg-ink-700 text-ink-300 rounded-lg text-sm">
              <BookOpen className="w-4 h-4" /><span className="hidden sm:inline">书架</span>
            </button>
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

      {error && (
        <div className="mx-4 sm:mx-6 mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />{error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4">
        {chapters.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-ink-600">
            <Loader2 className="w-8 h-8 animate-spin mb-3" />
            <p>正在准备生成...</p>
          </div>
        ) : (
          <div className="space-y-4 max-w-2xl mx-auto">
            {chapters.map((chapter) => {
              const isPlanning = chapter.status === 'planning';
              const isWriting = chapter.status === 'writing';
              const isCompleted = chapter.status === 'completed';
              const isError = chapter.status === 'error';
              return (
                <div key={chapter.id} className={`p-4 rounded-xl border ${
                  isPlanning ? 'bg-amber-400/5 border-amber-400/20' :
                  isWriting ? 'bg-gold-400/5 border-gold-400/20' :
                  isCompleted ? 'bg-ink-900/50 border-ink-800' :
                  'bg-ink-900/30 border-ink-800/50'
                }`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0">
                      {isPlanning && <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />}
                      {isWriting && <Loader2 className="w-4 h-4 text-gold-400 animate-spin" />}
                      {isCompleted && <div className="w-2 h-2 rounded-full bg-emerald-500" />}
                      {isError && <AlertCircle className="w-4 h-4 text-red-400" />}
                      <span className={`${isPlanning ? 'text-amber-400' : isWriting ? 'text-gold-400' : isCompleted ? 'text-ink-200' : 'text-red-400'} truncate`}>
                        第{chapter.id}章{chapter.title ? `：${chapter.title}` : ''}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {isCompleted && <span className="text-xs text-ink-500">{chapter.wordCount} 字</span>}
                      {(isCompleted || isError) && (
                        <button
                          onClick={() => handleRegenerate(chapter.id)}
                          disabled={isGenerating}
                          className="flex items-center gap-1 text-xs px-2.5 py-1.5 bg-amber-400/10 hover:bg-amber-400/20 text-amber-400 rounded-lg disabled:opacity-40"
                        >
                          <RefreshCw className="w-3 h-3" />重新生成
                        </button>
                      )}
                      {isCompleted && (
                        <button onClick={() => { useStore.getState().setCurrentChapterId(chapter.id); useStore.getState().setView('reading'); }} className="text-xs px-3 py-1.5 bg-gold-400/10 text-gold-400 rounded-lg">阅读</button>
                      )}
                    </div>
                  </div>
                  {(isPlanning || isWriting) && (
                    <p className="text-sm text-ink-500 mt-2">{isPlanning ? '生成大纲中...' : '正在写作中...'}</p>
                  )}
                  {chapter.plan && (
                    <div className="mt-2 p-2 bg-ink-950/50 rounded-lg">
                      <div className="flex items-center gap-1.5 text-xs text-amber-400/70 mb-1">
                        <FileText className="w-3 h-3" />大纲
                      </div>
                      <p className="text-xs text-ink-400 leading-relaxed">{chapter.plan}</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
