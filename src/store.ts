import { create } from 'zustand';
import { AppState, Chapter, NovelRecord, ViewState } from './types';
import { showToast } from './components/Toast';

const STORAGE_KEY = 'novel-generator-config';
const HISTORY_KEY = 'novel-generator-history';
const ACTIVE_RECORD_KEY = 'novel-generator-active-record';

function loadConfig(): { novelConfig: AppState['novelConfig']; apiConfig: AppState['apiConfig'] } {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (data) return JSON.parse(data);
  } catch {}
  return {
    novelConfig: { theme: '', chapterCount: 10, wordsPerChapter: 3000 },
    apiConfig: { baseUrl: 'https://api.openai.com/v1', apiKey: '', model: 'gpt-4', systemPrompt: '' },
  };
}

function saveConfig(novelConfig: AppState['novelConfig'], apiConfig: AppState['apiConfig']) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ novelConfig, apiConfig })); } catch {}
}

export function loadHistory(): NovelRecord[] {
  try {
    const data = localStorage.getItem(HISTORY_KEY);
    if (data) return JSON.parse(data);
  } catch {}
  return [];
}

function saveHistory(records: NovelRecord[]) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(records));
  } catch (e) {
    if (e instanceof DOMException && e.name === 'QuotaExceededError') {
      showToast('存储空间不足，请删除一些历史记录', 'error');
    }
  }
}

function getActiveRecordId(): string | null {
  try { return localStorage.getItem(ACTIVE_RECORD_KEY); } catch { return null; }
}

function setActiveRecordId(id: string | null) {
  try {
    if (id) localStorage.setItem(ACTIVE_RECORD_KEY, id);
    else localStorage.removeItem(ACTIVE_RECORD_KEY);
  } catch {}
}

const config = loadConfig();
const activeRecordId = getActiveRecordId();
const history = loadHistory();
const activeRecord = activeRecordId ? history.find((r) => r.id === activeRecordId && r.status === 'generating') : null;

const initialState: AppState = {
  novelConfig: activeRecord ? activeRecord.novelConfig : config.novelConfig,
  apiConfig: activeRecord ? activeRecord.apiConfig : config.apiConfig,
  chapters: activeRecord ? activeRecord.chapters : [],
  currentChapterId: activeRecord && activeRecord.chapters.length > 0 ? Math.max(...activeRecord.chapters.map((c) => c.id)) : 0,
  currentRecordId: activeRecord ? activeRecord.id : null,
  isGenerating: !!activeRecord,
  shouldStop: false,
  view: activeRecord ? 'generating' : 'history',
  sidebarCollapsed: false,
  error: null,
};

export const useStore = create<AppState & {
  setNovelConfig: (config: Partial<AppState['novelConfig']>) => void;
  setApiConfig: (config: Partial<AppState['apiConfig']>) => void;
  setChapters: (chapters: Chapter[]) => void;
  addChapter: (chapter: Chapter) => void;
  updateChapter: (id: number, updates: Partial<Chapter>) => void;
  setCurrentChapterId: (id: number) => void;
  setIsGenerating: (value: boolean) => void;
  setShouldStop: (value: boolean) => void;
  setView: (view: ViewState) => void;
  setSidebarCollapsed: (value: boolean) => void;
  setError: (error: string | null) => void;
  createHistoryRecord: () => string;
  updateHistoryRecord: () => void;
  completeHistoryRecord: () => void;
  deleteHistoryRecord: (recordId: string) => void;
  loadFromHistory: (recordId: string) => void;
}>((set, get) => ({
  ...initialState,

  setNovelConfig: (config) => {
    set((s) => {
      const next = { novelConfig: { ...s.novelConfig, ...config } };
      saveConfig(next.novelConfig, s.apiConfig);
      return next;
    });
  },

  setApiConfig: (config) => {
    set((s) => {
      const next = { apiConfig: { ...s.apiConfig, ...config } };
      saveConfig(s.novelConfig, next.apiConfig);
      return next;
    });
  },

  setChapters: (chapters) => set({ chapters }),

  addChapter: (chapter) => {
    const s = get();
    if (s.chapters.some((c) => c.id === chapter.id)) return;
    set({ chapters: [...s.chapters, chapter] });
  },

  updateChapter: (id, updates) => {
    const s = get();
    const newChapters = s.chapters.map((c) => (c.id === id ? { ...c, ...updates } : c));
    set({ chapters: newChapters });
    if (s.currentRecordId) {
      const records = loadHistory();
      const idx = records.findIndex((r) => r.id === s.currentRecordId);
      if (idx !== -1) {
        records[idx].chapters = newChapters;
        records[idx].updatedAt = new Date().toLocaleString('zh-CN');
        saveHistory(records);
      }
    }
  },

  setCurrentChapterId: (id) => set({ currentChapterId: id }),
  setIsGenerating: (value) => set({ isGenerating: value }),
  setShouldStop: (value) => set({ shouldStop: value }),
  setView: (view) => set({ view }),
  setSidebarCollapsed: (value) => set({ sidebarCollapsed: value }),
  setError: (error) => set({ error }),

  createHistoryRecord: () => {
    const s = get();
    const record: NovelRecord = {
      id: `${Date.now()}`,
      theme: s.novelConfig.theme,
      apiConfig: { ...s.apiConfig },
      novelConfig: { ...s.novelConfig },
      chapters: [],
      status: 'generating',
      createdAt: new Date().toLocaleString('zh-CN'),
      updatedAt: new Date().toLocaleString('zh-CN'),
    };
    const records = loadHistory();
    records.unshift(record);
    saveHistory(records);
    setActiveRecordId(record.id);
    set({ currentRecordId: record.id });
    return record.id;
  },

  updateHistoryRecord: () => {
    const s = get();
    if (!s.currentRecordId) return;
    const records = loadHistory();
    const idx = records.findIndex((r) => r.id === s.currentRecordId);
    if (idx !== -1) {
      records[idx].chapters = s.chapters;
      records[idx].updatedAt = new Date().toLocaleString('zh-CN');
      saveHistory(records);
    }
  },

  completeHistoryRecord: () => {
    const s = get();
    if (!s.currentRecordId) return;
    const records = loadHistory();
    const idx = records.findIndex((r) => r.id === s.currentRecordId);
    if (idx !== -1) {
      records[idx].chapters = s.chapters.filter((c) => c.status === 'completed');
      records[idx].status = 'completed';
      records[idx].updatedAt = new Date().toLocaleString('zh-CN');
      saveHistory(records);
    }
    setActiveRecordId(null);
    set({ currentRecordId: null });
  },

  deleteHistoryRecord: (recordId) => {
    const records = loadHistory().filter((r) => r.id !== recordId);
    saveHistory(records);
    if (get().currentRecordId === recordId) {
      setActiveRecordId(null);
      set({ currentRecordId: null });
    }
  },

  loadFromHistory: (recordId) => {
    const s = get();
    const records = loadHistory();
    const record = records.find((r) => r.id === recordId);
    if (!record) return;
    const isGeneratingRecord = record.status === 'generating';

    if (isGeneratingRecord && s.currentRecordId === recordId && s.isGenerating) {
      set({ view: 'generating' });
      return;
    }

    setActiveRecordId(isGeneratingRecord ? recordId : null);
    set({
      novelConfig: record.novelConfig,
      apiConfig: record.apiConfig,
      chapters: record.chapters,
      currentChapterId: record.chapters.length > 0 ? Math.max(...record.chapters.map((c) => c.id)) : 0,
      currentRecordId: isGeneratingRecord ? recordId : null,
      isGenerating: isGeneratingRecord,
      shouldStop: false,
      view: isGeneratingRecord ? 'generating' : 'reading',
      error: null,
    });
  },
}));
