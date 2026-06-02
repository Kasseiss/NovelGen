import { useState } from 'react';
import { BookOpen, Key, Settings, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import { useStore } from '../store';
import { showToast } from './Toast';

export default function ConfigPanel() {
  const setNovelConfig = useStore((s) => s.setNovelConfig);
  const setApiConfig = useStore((s) => s.setApiConfig);
  const setView = useStore((s) => s.setView);
  const novelConfig = useStore((s) => s.novelConfig);
  const apiConfig = useStore((s) => s.apiConfig);

  const [showApiConfig, setShowApiConfig] = useState(false);
  const [localTheme, setLocalTheme] = useState(novelConfig.theme);
  const [localChapterCount, setLocalChapterCount] = useState(novelConfig.chapterCount);
  const [localWordsPerChapter, setLocalWordsPerChapter] = useState(novelConfig.wordsPerChapter);
  const [localBaseUrl, setLocalBaseUrl] = useState(apiConfig.baseUrl);
  const [localApiKey, setLocalApiKey] = useState(apiConfig.apiKey);
  const [localModel, setLocalModel] = useState(apiConfig.model);
  const [localSystemPrompt, setLocalSystemPrompt] = useState(apiConfig.systemPrompt);

  const handleStart = () => {
    if (!localTheme.trim()) {
      showToast('请输入小说主题', 'error');
      return;
    }
    if (!localApiKey.trim()) {
      showToast('请输入 API Key', 'error');
      return;
    }

    setNovelConfig({
      theme: localTheme,
      chapterCount: localChapterCount,
      wordsPerChapter: localWordsPerChapter,
    });
    setApiConfig({
      baseUrl: localBaseUrl,
      apiKey: localApiKey,
      model: localModel,
      systemPrompt: localSystemPrompt,
    });

    const state = useStore.getState();
    if (state.currentRecordId) {
      state.completeHistoryRecord();
    }
    useStore.setState({ chapters: [], currentChapterId: 0, currentRecordId: null, error: null });
    useStore.setState({ isGenerating: true });
    setView('history');
  };

  return (
    <div className="w-full max-w-3xl mx-auto animate-fade-in">
      <div className="text-center mb-10">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-gold-400/20 to-gold-600/10 border border-gold-400/20 mb-4">
          <BookOpen className="w-8 h-8 text-gold-400" />
        </div>
        <h1 className="text-3xl font-bold gradient-text font-serif mb-2">墨流小说生成器</h1>
        <p className="text-ink-300 text-sm">让 AI 为你编织无限故事</p>
      </div>

      <div className="space-y-6">
        {/* Theme Input */}
        <div className="bg-ink-900/50 border border-ink-800 rounded-xl p-6 glow-gold">
          <label className="flex items-center gap-2 text-gold-400 font-medium mb-3">
            <Sparkles className="w-4 h-4" />
            小说主题与要求
          </label>
          <textarea
            value={localTheme}
            onChange={(e) => setLocalTheme(e.target.value)}
            placeholder="请输入小说主题、风格、角色设定等要求...&#10;&#10;例如：写一个修仙小说，主角是一个废柴少年，意外获得上古神器，从此踏上修仙之路。风格要热血、搞笑，带有一些现代梗。"
            className="w-full h-40 bg-ink-950 border border-ink-800 rounded-lg px-4 py-3 text-ink-50 placeholder-ink-600 focus:outline-none focus:border-gold-400/50 focus:ring-1 focus:ring-gold-400/20 resize-none transition-all"
          />
        </div>

        {/* Settings */}
        <div className="bg-ink-900/50 border border-ink-800 rounded-xl p-6 glow-gold">
          <label className="flex items-center gap-2 text-gold-400 font-medium mb-4">
            <Settings className="w-4 h-4" />
            生成设置
          </label>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-ink-300 text-sm mb-2">章节数量</label>
              <input
                type="number"
                value={localChapterCount}
                onChange={(e) => setLocalChapterCount(Math.max(0, Math.min(500, parseInt(e.target.value) || 0)))}
                min={0}
                max={500}
                className="w-full bg-ink-950 border border-ink-800 rounded-lg px-4 py-2.5 text-ink-50 focus:outline-none focus:border-gold-400/50 focus:ring-1 focus:ring-gold-400/20 transition-all"
              />
              <p className="text-ink-600 text-xs mt-1">0 = 无限生成（最多 500 章）</p>
            </div>
            <div>
              <label className="block text-ink-300 text-sm mb-2">每章字数</label>
              <input
                type="number"
                value={localWordsPerChapter}
                onChange={(e) => setLocalWordsPerChapter(Math.max(500, Math.min(10000, parseInt(e.target.value) || 500)))}
                min={500}
                max={10000}
                step={100}
                className="w-full bg-ink-950 border border-ink-800 rounded-lg px-4 py-2.5 text-ink-50 focus:outline-none focus:border-gold-400/50 focus:ring-1 focus:ring-gold-400/20 transition-all"
              />
              <p className="text-ink-600 text-xs mt-1">范围: 500 - 10,000</p>
            </div>
          </div>
        </div>

        {/* API Config */}
        <div className="bg-ink-900/50 border border-ink-800 rounded-xl overflow-hidden glow-gold">
          <button
            onClick={() => setShowApiConfig(!showApiConfig)}
            className="w-full flex items-center justify-between p-6 text-left hover:bg-ink-800/30 transition-colors"
          >
            <label className="flex items-center gap-2 text-gold-400 font-medium cursor-pointer">
              <Key className="w-4 h-4" />
              API 配置
            </label>
            {showApiConfig ? (
              <ChevronUp className="w-4 h-4 text-ink-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-ink-400" />
            )}
          </button>
          {showApiConfig && (
            <div className="px-6 pb-6 space-y-4 animate-fade-in">
              <div>
                <label className="block text-ink-300 text-sm mb-2">API 地址</label>
                <input
                  type="text"
                  value={localBaseUrl}
                  onChange={(e) => setLocalBaseUrl(e.target.value)}
                  placeholder="https://api.openai.com/v1"
                  className="w-full bg-ink-950 border border-ink-800 rounded-lg px-4 py-2.5 text-ink-50 placeholder-ink-600 focus:outline-none focus:border-gold-400/50 focus:ring-1 focus:ring-gold-400/20 transition-all"
                />
              </div>
              <div>
                <label className="block text-ink-300 text-sm mb-2">API Key</label>
                <input
                  type="password"
                  value={localApiKey}
                  onChange={(e) => setLocalApiKey(e.target.value)}
                  placeholder="sk-xxxxxxxxxxxx"
                  className="w-full bg-ink-950 border border-ink-800 rounded-lg px-4 py-2.5 text-ink-50 placeholder-ink-600 focus:outline-none focus:border-gold-400/50 focus:ring-1 focus:ring-gold-400/20 transition-all"
                />
              </div>
              <div>
                <label className="block text-ink-300 text-sm mb-2">模型名称</label>
                <input
                  type="text"
                  value={localModel}
                  onChange={(e) => setLocalModel(e.target.value)}
                  placeholder="gpt-4"
                  className="w-full bg-ink-950 border border-ink-800 rounded-lg px-4 py-2.5 text-ink-50 placeholder-ink-600 focus:outline-none focus:border-gold-400/50 focus:ring-1 focus:ring-gold-400/20 transition-all"
                />
              </div>
              <div>
                <label className="block text-ink-300 text-sm mb-2">系统提示词（可选）</label>
                <textarea
                  value={localSystemPrompt}
                  onChange={(e) => setLocalSystemPrompt(e.target.value)}
                  placeholder="自定义系统提示词，用于控制生成风格..."
                  className="w-full h-32 bg-ink-950 border border-ink-800 rounded-lg px-4 py-3 text-ink-50 placeholder-ink-600 focus:outline-none focus:border-gold-400/50 focus:ring-1 focus:ring-gold-400/20 resize-none transition-all text-sm"
                />
              </div>
            </div>
          )}
        </div>

        {/* Start Button */}
        <button
          onClick={handleStart}
          className="w-full py-4 bg-gradient-to-r from-gold-600/80 to-gold-500/80 hover:from-gold-500 hover:to-gold-400 text-ink-950 font-bold text-lg rounded-xl transition-all glow-gold-hover transform hover:scale-[1.02] active:scale-[0.98]"
        >
          <span className="flex items-center justify-center gap-2">
            <Sparkles className="w-5 h-5" />
            开始生成小说
          </span>
        </button>
      </div>
    </div>
  );
}
