import { create } from 'zustand';
import { AppState, NovelRecord, ViewState } from './types';

const STORAGE_KEY = 'novel-generator-config';

function loadConfig(): { novelConfig: AppState['novelConfig']; apiConfig: AppState['apiConfig'] } {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (data) return JSON.parse(data);
  } catch {}
  return {
    novelConfig: { theme: '', chapterCount: 0, wordsPerChapter: 3000 },
    apiConfig: { baseUrl: 'https://api.openai.com/v1', apiKey: '', model: 'gpt-4', systemPrompt: '' },
  };
}

function saveConfig(novelConfig: AppState['novelConfig'], apiConfig: AppState['apiConfig']) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ novelConfig, apiConfig }));
  } catch {}
}

const config = loadConfig();

export const useStore = create<AppState & {
  setNovelConfig: (config: Partial<AppState['novelConfig']>) => void;
  setApiConfig: (config: Partial<AppState['apiConfig']>) => void;
  setView: (view: ViewState) => void;
  setSelectedNovel: (novel: NovelRecord | null) => void;
  setCurrentChapterId: (id: number) => void;
  setSidebarCollapsed: (v: boolean) => void;
}>((set) => ({
  novelConfig: config.novelConfig,
  apiConfig: config.apiConfig,
  chapters: [],
  currentChapterId: 0,
  currentRecordId: null,
  isGenerating: false,
  shouldStop: false,
  view: 'history',
  sidebarCollapsed: false,
  error: null,
  selectedNovel: null,

  setNovelConfig: (cfg) => {
    set((s) => {
      const next = { novelConfig: { ...s.novelConfig, ...cfg } };
      saveConfig(next.novelConfig, s.apiConfig);
      return next;
    });
  },

  setApiConfig: (cfg) => {
    set((s) => {
      const next = { apiConfig: { ...s.apiConfig, ...cfg } };
      saveConfig(s.novelConfig, next.apiConfig);
      return next;
    });
  },

  setView: (view) => set({ view }),
  setCurrentChapterId: (id) => set({ currentChapterId: id }),
  setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),

  setSelectedNovel: (novel) => {
    const completedChapters = novel?.chapters?.filter(c => c.status === 'completed') || [];
    set({
      selectedNovel: novel,
      chapters: novel?.chapters || [],
      currentChapterId: completedChapters.length ? completedChapters[0].id : 0,
      currentRecordId: novel?.id || null,
      isGenerating: novel?.status === 'generating',
    });
  },
}));
