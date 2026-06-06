import { useState } from 'react';
import { BookOpen, Key, Settings, ChevronDown, ChevronUp, Sparkles, Zap } from 'lucide-react';
import { useStore } from '../store';
import { showToast } from './Toast';

const SYSTEM_PROMPT_PRESETS = [
  {
    name: '默认',
    prompt: `你是一位专业的中文网络小说作家，擅长根据用户要求创作引人入胜的长篇小说。

【创作规则】
1. 严格按照用户提供的主题、风格和要求进行创作
2. 每章内容必须连贯，与前后章节保持剧情衔接
3. 章节开头不需要重复小说标题
4. 章节结构：先输出章节标题（格式：第X章：标题），然后换行输出正文
5. 正文要求情节紧凑、描写生动、对话自然
6. 字数必须达到用户要求的字数，只多不少
7. 如果提供了前文内容，请确保新章节与剧情连贯

【输出格式】
第X章：章节标题

（正文内容，段落分明，不少于要求字数）`,
  },
  {
    name: '热血爽文',
    prompt: `你是一位顶级网络小说写手，擅长写热血爽文。你的文风特点：节奏极快，爽点密集，打脸不断，主角永远是最强的。

【创作规则】
1. 每章必须有至少一个爽点（打脸、突破、获得宝物、装逼成功等）
2. 主角性格果断狠辣，不圣母，不拖泥带水
3. 配角要有记忆点，反派要够嚣张然后被狠狠打脸
4. 战斗场景要写得燃，要有压迫感然后逆转的爽感
5. 章节结尾要留悬念，让读者想看下一章
6. 字数必须达到要求，只多不少

【输出格式】
第X章：章节标题

（正文内容）`,
  },
  {
    name: '细腻文艺',
    prompt: `你是一位文笔细腻的小说家，擅长写有文学质感的小说。你的作品注重人物内心刻画、环境氛围营造和情感表达。

【创作规则】
1. 注重心理描写和情感铺垫，让读者共情
2. 环境描写要有画面感，善用五感（视觉、听觉、嗅觉、触觉、味觉）
3. 对话要符合人物性格，有潜台词
4. 叙事节奏可以适当放慢，但要有张力
5. 前后章节要有伏笔呼应
6. 字数必须达到要求，只多不少

【输出格式】
第X章：章节标题

（正文内容）`,
  },
  {
    name: '轻松搞笑',
    prompt: `你是一位擅长写轻松搞笑小说的作家。你的文风幽默风趣，节奏轻快，让读者看得开心。

【创作规则】
1. 对话要有趣，多用吐槽和梗
2. 主角性格可以沙雕、腹黑、毒舌，要有喜剧感
3. 剧情可以离谱但要自洽
4. 适当加入打破第四面墙的元素
5. 即使是紧张的场景也要有笑点
6. 字数必须达到要求，只多不少

【输出格式】
第X章：章节标题

（正文内容）`,
  },
];

export default function ConfigPanel() {
  const setNovelConfig = useStore((s) => s.setNovelConfig);
  const setApiConfig = useStore((s) => s.setApiConfig);
  const setView = useStore((s) => s.setView);
  const novelConfig = useStore((s) => s.novelConfig);
  const apiConfig = useStore((s) => s.apiConfig);

  const [showApiConfig, setShowApiConfig] = useState(false);
  const [localTheme, setLocalTheme] = useState(novelConfig.theme);
  const [localChapterCount, setLocalChapterCount] = useState('');
  const [localWordsPerChapter, setLocalWordsPerChapter] = useState('');
  const [localBaseUrl, setLocalBaseUrl] = useState(apiConfig.baseUrl);
  const [localApiKey, setLocalApiKey] = useState(apiConfig.apiKey);
  const [localModel, setLocalModel] = useState(apiConfig.model);
  const [localSystemPrompt, setLocalSystemPrompt] = useState(apiConfig.systemPrompt);

  const handleStart = async () => {
    if (!localTheme.trim()) {
      showToast('请输入小说主题', 'error');
      return;
    }
    if (!localApiKey.trim()) {
      showToast('请输入 API Key', 'error');
      return;
    }

    const chapterCount = localChapterCount === '' ? 0 : Math.max(0, parseInt(localChapterCount) || 0);
    const wordsPerChapter = localWordsPerChapter === '' ? 3000 : parseInt(localWordsPerChapter) || 0;

    if (localChapterCount !== '' && parseInt(localChapterCount) < 0) {
      showToast('章节数不能为负数', 'error');
      return;
    }
    if (wordsPerChapter < 1) {
      showToast('每章字数必须大于0', 'error');
      return;
    }

    setNovelConfig({
      theme: localTheme,
      chapterCount,
      wordsPerChapter,
    });
    setApiConfig({
      baseUrl: localBaseUrl,
      apiKey: localApiKey,
      model: localModel,
      systemPrompt: localSystemPrompt,
    });

    try {
      const resp = await fetch('/api/novels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          theme: localTheme,
          apiConfig: {
            baseUrl: localBaseUrl,
            apiKey: localApiKey,
            model: localModel,
            systemPrompt: localSystemPrompt,
          },
          novelConfig: {
            chapterCount,
            wordsPerChapter,
          },
        }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        showToast(data?.error || '创建失败', 'error');
        return;
      }
      useStore.getState().setSelectedNovel(data);
      useStore.getState().setView('generating');
    } catch (e) {
      showToast('创建任务失败', 'error');
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto p-4 sm:p-8 animate-fade-in">
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
                type="text"
                value={localChapterCount}
                onChange={(e) => {
                  const v = e.target.value.replace(/[^0-9]/g, '');
                  setLocalChapterCount(v);
                }}
                placeholder="留空=无限生成"
                className="w-full bg-ink-950 border border-ink-800 rounded-lg px-4 py-2.5 text-ink-50 placeholder-ink-600 focus:outline-none focus:border-gold-400/50 focus:ring-1 focus:ring-gold-400/20 transition-all"
              />
              <p className="text-ink-600 text-xs mt-1">0 = 无限生成</p>
            </div>
            <div>
              <label className="block text-ink-300 text-sm mb-2">每章字数</label>
              <input
                type="text"
                value={localWordsPerChapter}
                onChange={(e) => {
                  const v = e.target.value.replace(/[^0-9]/g, '');
                  setLocalWordsPerChapter(v);
                }}
                placeholder="留空=3000字"
                className="w-full bg-ink-950 border border-ink-800 rounded-lg px-4 py-2.5 text-ink-50 placeholder-ink-600 focus:outline-none focus:border-gold-400/50 focus:ring-1 focus:ring-gold-400/20 transition-all"
              />
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
                <label className="block text-ink-300 text-sm mb-2">系统提示词</label>
                <div className="flex flex-wrap gap-2 mb-3">
                  {SYSTEM_PROMPT_PRESETS.map((preset) => (
                    <button
                      key={preset.name}
                      onClick={() => setLocalSystemPrompt(preset.prompt)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-ink-800 hover:bg-ink-700 text-ink-300 hover:text-gold-400 rounded-lg transition-colors"
                    >
                      <Zap className="w-3 h-3" />
                      {preset.name}
                    </button>
                  ))}
                </div>
                <textarea
                  value={localSystemPrompt}
                  onChange={(e) => setLocalSystemPrompt(e.target.value)}
                  placeholder="点击上方预设快速填入，或自定义系统提示词..."
                  className="w-full h-40 bg-ink-950 border border-ink-800 rounded-lg px-4 py-3 text-ink-50 placeholder-ink-600 focus:outline-none focus:border-gold-400/50 focus:ring-1 focus:ring-gold-400/20 resize-none transition-all text-sm"
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
