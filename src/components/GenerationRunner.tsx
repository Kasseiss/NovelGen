import { useEffect } from 'react';
import { useStore } from '../store';
import { generateChapterPlan, generateChapterContent, parseChapterContent, countChineseWords } from '../utils/api';

let loopRunning = false;
let abortController: AbortController | null = null;

export function stopGeneration() {
  loopRunning = false;
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
}

export default function GenerationRunner() {
  const isGenerating = useStore((s) => s.isGenerating);

  useEffect(() => {
    if (!isGenerating || loopRunning) return;
    loopRunning = true;
    useStore.getState().setError(null);

    if (!useStore.getState().currentRecordId) {
      useStore.getState().createHistoryRecord();
    }

    const run = async () => {
      let chapterNum = (() => {
        const state = useStore.getState();
        const incomplete = state.chapters.find((c) => c.status === 'planning' || c.status === 'writing');
        if (incomplete) return incomplete.id;
        const lastCompleted = state.chapters.filter((c) => c.status === 'completed');
        if (lastCompleted.length === 0) return 1;
        return Math.max(...lastCompleted.map((c) => c.id)) + 1;
      })();

      while (loopRunning) {
        const state = useStore.getState();
        if (state.shouldStop) break;
        if (state.novelConfig.chapterCount > 0 && chapterNum > state.novelConfig.chapterCount) break;
        if (chapterNum > 500) break;

        const prev = state.chapters.filter((c) => c.status === 'completed').slice(-3)
          .map((c) => `第${c.id}章「${c.title}」：${c.content.slice(-500)}`).join('\n\n');

        const existing = state.chapters.find((c) => c.id === chapterNum);
        if (!existing) {
          useStore.getState().addChapter({
            id: chapterNum, title: '', content: '', wordCount: 0, plan: '', status: 'planning',
          });
        } else if (existing.status === 'completed') {
          chapterNum++;
          continue;
        }

        if (state.view === 'generating') {
          useStore.getState().setCurrentChapterId(chapterNum);
        }

        try {
          abortController = new AbortController();
          const signal = abortController.signal;

          const { title, plan } = await generateChapterPlan(
            state.apiConfig, state.novelConfig.theme,
            chapterNum, state.novelConfig.chapterCount, prev, signal
          );

          if (!loopRunning) break;
          useStore.getState().updateChapter(chapterNum, { title, plan, status: 'writing' });

          const fullContent = await generateChapterContent(
            state.apiConfig, state.novelConfig.theme,
            chapterNum, state.novelConfig.chapterCount, state.novelConfig.wordsPerChapter,
            plan, prev, state.apiConfig.systemPrompt, signal
          );

          if (!loopRunning) break;
          const { title: parsedTitle, content } = parseChapterContent(fullContent);
          const wordCount = countChineseWords(content);

          useStore.getState().updateChapter(chapterNum, {
            title: parsedTitle || title, content, wordCount, status: 'completed',
          });

          chapterNum++;
        } catch (err) {
          if (!loopRunning) break;
          const msg = err instanceof Error ? err.message : '生成失败';
          useStore.getState().updateChapter(chapterNum, { status: 'error' });
          useStore.getState().setError(msg);
          break;
        }
      }

      const wasRunning = loopRunning;
      loopRunning = false;
      abortController = null;
      if (wasRunning) {
        const finalState = useStore.getState();
        if (finalState.currentRecordId) {
          finalState.completeHistoryRecord();
        }
      }
      useStore.getState().setIsGenerating(false);
      useStore.getState().setShouldStop(false);
    };

    run();
  }, [isGenerating]);

  return null;
}
