import { ApiConfig, ChatMessage } from '../types';

export function authHeaders(token: string): HeadersInit {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };
}

const TIMEOUT_MS = 60000;

async function fetchWithTimeout(url: string, init: RequestInit, signal?: AbortSignal): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);

  if (signal) {
    signal.addEventListener('abort', () => controller.abort());
  }

  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

export async function chatCompletion(
  apiConfig: ApiConfig,
  messages: ChatMessage[],
  maxTokens: number,
  signal?: AbortSignal
): Promise<string> {
  const response = await fetchWithTimeout(
    `${apiConfig.baseUrl}/chat/completions`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiConfig.apiKey}`,
      },
      body: JSON.stringify({
        model: apiConfig.model,
        messages,
        stream: false,
        temperature: 0.8,
        max_tokens: maxTokens,
      }),
    },
    signal
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API 请求失败: ${response.status} ${errorText}`);
  }

  const data = await response.json();
  const content = data.choices?.[0]?.message?.content;
  if (!content) {
    throw new Error('API 返回内容为空');
  }
  return content;
}

export async function generateChapterPlan(
  apiConfig: ApiConfig,
  theme: string,
  chapterNum: number,
  totalChapters: number,
  previousChaptersSummary: string,
  signal?: AbortSignal
): Promise<{ title: string; plan: string }> {
  const totalText = totalChapters > 0 ? `总共 ${totalChapters} 章` : '无限连载';

  let userMsg = `【小说主题】\n${theme}\n\n`;
  userMsg += `【任务】\n这是第 ${chapterNum} 章，${totalText}。\n\n`;
  if (previousChaptersSummary) {
    userMsg += `【前文摘要】\n${previousChaptersSummary}\n\n`;
  }
  userMsg += `请用最简短、最直接的话，写出这一章要写什么。\n`;
  userMsg += `不要废话，不要绕弯子，直接说清楚：\n`;
  userMsg += `- 这一章的核心事件是什么\n`;
  userMsg += `- 主角要干什么、遇到什么、怎么解决\n`;
  userMsg += `- 章节标题是什么\n\n`;
  userMsg += `严格按以下格式输出：\n`;
  userMsg += `标题：xxx\n`;
  userMsg += `内容：xxx`;

  const messages: ChatMessage[] = [
    { role: 'system', content: '你是一个小说大纲策划师。你的任务是用最简短直接的话规划每一章的内容。不要废话，不要文学性描述，只要说清楚这一章写什么。' },
    { role: 'user', content: userMsg },
  ];

  const raw = await chatCompletion(apiConfig, messages, 500, signal);

  let title = `未命名章节`;
  let plan = raw.trim();

  const titleMatch = raw.match(/标题[：:]\s*(.+)/);
  if (titleMatch) {
    title = titleMatch[1].trim();
  }

  const planMatch = raw.match(/内容[：:]\s*([\s\S]+)/);
  if (planMatch) {
    plan = planMatch[1].trim();
  }

  if (!planMatch && !titleMatch) {
    plan = raw.trim();
  }

  return { title, plan };
}

export async function generateChapterContent(
  apiConfig: ApiConfig,
  theme: string,
  chapterNum: number,
  totalChapters: number,
  wordsPerChapter: number,
  chapterPlan: string,
  previousContent: string,
  systemPrompt: string,
  signal?: AbortSignal
): Promise<string> {
  const totalText = totalChapters > 0 ? `总共 ${totalChapters} 章` : '无限连载';

  let userMsg = `【小说主题】\n${theme}\n\n`;
  userMsg += `【本章任务】\n这是第 ${chapterNum} 章，${totalText}。\n`;
  userMsg += `本章要求字数：${wordsPerChapter} 字以上。\n\n`;
  userMsg += `【本章大纲】\n${chapterPlan}\n\n`;

  if (previousContent) {
    const truncated = previousContent.slice(-1500);
    userMsg += `【前文结尾】（确保剧情连贯）\n${truncated}\n\n`;
  }

  userMsg += `请严格按照上面的大纲创作本章正文。\n`;
  userMsg += `要求：\n`;
  userMsg += `1. 先输出章节标题，格式：第${chapterNum}章：标题\n`;
  userMsg += `2. 然后换行输出正文\n`;
  userMsg += `3. 正文必须紧扣大纲内容\n`;
  userMsg += `4. 情节紧凑、描写生动、对话自然\n`;
  userMsg += `5. 字数必须达到 ${wordsPerChapter} 字以上，只多不少`;

  const defaultSystem = `你是一位专业的中文网络小说作家。

【核心规则】
1. 严格按照提供的大纲创作，不要偏离主题
2. 每章字数必须达到要求，只多不少
3. 情节紧凑、描写生动、对话自然
4. 章节间剧情必须连贯
5. 不要在章节开头重复小说标题

【输出格式】
第X章：章节标题

（正文内容，段落分明）`;

  const messages: ChatMessage[] = [
    { role: 'system', content: systemPrompt || defaultSystem },
    { role: 'user', content: userMsg },
  ];

  const maxTokens = Math.ceil(wordsPerChapter * 2);
  return await chatCompletion(apiConfig, messages, maxTokens, signal);
}

export function parseChapterContent(rawContent: string): { title: string; content: string } {
  const lines = rawContent.trim().split('\n');
  let title = '';
  let contentStart = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    const match = line.match(/^第[一二三四五六七八九十百千万零\d]+章[：:：]\s*(.+)$/);
    if (match) {
      title = match[1].trim();
      contentStart = i + 1;
      break;
    }
  }

  if (!title) {
    title = '未命名章节';
    contentStart = 0;
  }

  const content = lines.slice(contentStart).join('\n').trim();
  return { title, content };
}

export function countChineseWords(text: string): number {
  return text.replace(/\s/g, '').length;
}
