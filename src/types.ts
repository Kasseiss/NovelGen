export interface NovelConfig {
  theme: string;
  chapterCount: number;
  wordsPerChapter: number;
}

export interface ApiConfig {
  baseUrl: string;
  apiKey: string;
  model: string;
  systemPrompt: string;
}

export interface Chapter {
  id: number;
  title: string;
  content: string;
  wordCount: number;
  plan: string;
  status: 'planning' | 'writing' | 'completed' | 'error';
}

export type ViewState = 'config' | 'generating' | 'reading' | 'history';

export interface NovelRecord {
  id: string;
  theme: string;
  apiConfig: ApiConfig;
  novelConfig: NovelConfig;
  chapters: Chapter[];
  status: 'generating' | 'completed';
  createdAt: string;
  updatedAt: string;
}

export interface AppState {
  novelConfig: NovelConfig;
  apiConfig: ApiConfig;
  chapters: Chapter[];
  currentChapterId: number;
  currentRecordId: string | null;
  isGenerating: boolean;
  shouldStop: boolean;
  view: ViewState;
  sidebarCollapsed: boolean;
  error: string | null;
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}
