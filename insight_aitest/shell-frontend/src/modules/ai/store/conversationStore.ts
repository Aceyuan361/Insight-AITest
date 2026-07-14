import { create } from 'zustand';
import { toast } from 'sonner';
import { useProjectStore } from '../../../shared/store/projectStore';
import { parseLLMError } from './llmErrors';

export interface Citation {
  document_id: number;
  document_name: string;
  chunk_index: number;
  snippet: string;
  score: number;
}

export interface Attachment {
  id: string;
  filename: string;
  mime: string;
  kind: 'image' | 'document';
  size: number;
  storage_path?: string;
  preview_text?: string | null;
}

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  thinking?: string;
  attachments?: Attachment[];
}

export interface Conversation {
  id: number;
  title: string;
  rag_enabled: boolean;
  thinking_level: string;  // off/low/medium/high
  project_id: number | null;
  created_at: string;
  updated_at: string;
}

interface ConversationState {
  conversations: Conversation[];
  activeId: number | null;
  messages: Record<number, Message[]>;
  streamingMessage: string | null;
  streamingThinking: string | null;
  streaming: boolean;
  loading: boolean;
  abortCtrl: AbortController | null;

  loadConversations: () => Promise<void>;
  createConversation: () => Promise<number>;
  selectConversation: (id: number) => Promise<void>;
  deleteConversation: (id: number) => Promise<void>;
  renameConversation: (id: number, title: string) => Promise<void>;
  setRagEnabled: (id: number, rag_enabled: boolean) => Promise<void>;
  setThinkingLevel: (id: number, thinking_level: string) => Promise<void>;
  loadMessages: (convId: number) => Promise<void>;
  sendMessage: (query: string, attachments?: Attachment[]) => Promise<void>;
  stopStreaming: () => void;
}

const BASE = '/api/modules/ai';

export const useConversationStore = create<ConversationState>((set, get) => ({
  conversations: [],
  activeId: null,
  messages: {},
  streamingMessage: null,
  streamingThinking: null,
  streaming: false,
  loading: false,
  abortCtrl: null,

  loadConversations: async () => {
    const { currentProjectId } = useProjectStore.getState();
    const q = currentProjectId !== null ? `?project_id=${currentProjectId}` : '';
    const r = await fetch(`${BASE}/conversations${q}`);
    const convs = await r.json();
    set({ conversations: convs });
  },

  createConversation: async () => {
    const { currentProjectId } = useProjectStore.getState();
    const { conversations, messages } = get();
    // 前端复用已有空会话（无消息），避免重复创建
    const emptyConv = conversations.find(
      (c) => c.project_id === currentProjectId && (messages[c.id]?.length ?? 0) === 0
    );
    if (emptyConv) {
      set({ activeId: emptyConv.id });
      return emptyConv.id;
    }
    const r = await fetch(`${BASE}/conversations`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: currentProjectId }),
    });
    if (!r.ok) {
      toast.error('创建会话失败');
      return -1;
    }
    const conv = await r.json();
    set((s) => ({
      conversations: [conv, ...s.conversations],
      activeId: conv.id,
      messages: { ...s.messages, [conv.id]: [] },
    }));
    return conv.id;
  },

  selectConversation: async (id: number) => {
    set({ activeId: id });
    await get().loadMessages(id);
  },

  deleteConversation: async (id: number) => {
    const r = await fetch(`${BASE}/conversations/${id}`, { method: 'DELETE' });
    if (!r.ok) return;  // API 失败时不更新本地状态（防止删除后恢复）
    set((s) => {
      const messages = { ...s.messages };
      delete messages[id];
      return {
        conversations: s.conversations.filter((c) => c.id !== id),
        activeId: s.activeId === id ? null : s.activeId,
        messages,
      };
    });
  },

  renameConversation: async (id: number, title: string) => {
    await fetch(`${BASE}/conversations/${id}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    set((s) => ({
      conversations: s.conversations.map((c) => (c.id === id ? { ...c, title } : c)),
    }));
  },

  setRagEnabled: async (id: number, rag_enabled: boolean) => {
    await fetch(`${BASE}/conversations/${id}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rag_enabled }),
    });
    set((s) => ({
      conversations: s.conversations.map((c) => (c.id === id ? { ...c, rag_enabled } : c)),
    }));
  },

  setThinkingLevel: async (id: number, thinking_level: string) => {
    await fetch(`${BASE}/conversations/${id}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ thinking_level }),
    });
    set((s) => ({
      conversations: s.conversations.map((c) => (c.id === id ? { ...c, thinking_level } : c)),
    }));
  },

  loadMessages: async (convId: number) => {
    const r = await fetch(`${BASE}/conversations/${convId}`);
    const data = await r.json();
    set((s) => ({ messages: { ...s.messages, [convId]: data.messages || [] } }));
  },

  sendMessage: async (query: string, attachments?: Attachment[]) => {
    const { activeId } = get();
    if (!activeId || get().streaming) return;

    // 乐观更新
    set((s) => ({
      messages: {
        ...s.messages,
        [activeId]: [
          ...(s.messages[activeId] ?? []),
          { role: 'user', content: query, attachments },
        ],
      },
      streaming: true,
      streamingMessage: '',
      streamingThinking: null,
    }));

    const abortCtrl = new AbortController();
    set({ abortCtrl });

    try {
      const conv = get().conversations.find((c) => c.id === activeId);
      const res = await fetch(`${BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: activeId,
          query,
          history_turns: 6,
          attachments,
          thinking_level: conv?.thinking_level ?? 'off',
        }),
        signal: abortCtrl.signal,
      });

      // 非 2xx 响应：body 是 JSON 错误体而非 SSE，需按状态码语义化提示
      if (!res.ok || !res.body) {
        const errText = await res.text().catch(() => '');
        const parsed = parseLLMError(errText || `HTTP ${res.status}`, res.status);
        // 写入错误占位 assistant 消息，保证前端历史完整
        set((s) => ({
          streaming: false,
          streamingMessage: null,
          streamingThinking: null,
          messages: {
            ...s.messages,
            [activeId]: [
              ...(s.messages[activeId] ?? []),
              { role: 'assistant' as const, content: `⚠️ 回复失败：${parsed.message}` },
            ],
          },
        }));
        toast.error(parsed.message);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let citations: Citation[] = [];
      let answer = '';
      let thinking = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop()!;
        for (const evt of events) {
          const type = evt.match(/^event: (.+)$/m)?.[1];
          const dataStr = evt.match(/^data: (.+)$/m)?.[1] ?? '{}';
          let data: any;
          try { data = JSON.parse(dataStr); } catch { continue; }
          if (type === 'citations') citations = data.citations ?? [];
          if (type === 'thinking') {
            thinking += data.text;
            set({ streamingThinking: thinking });
          }
          if (type === 'token') {
            answer += data.text;
            set({ streamingMessage: answer });
          }
          if (type === 'done') {
            set((s) => ({
              streamingMessage: null,
              streamingThinking: null,
              streaming: false,
              messages: {
                ...s.messages,
                [activeId]: [
                  ...(s.messages[activeId] ?? []),
                  {
                    role: 'assistant',
                    content: answer,
                    citations,
                    thinking: thinking || undefined,
                  },
                ],
              },
            }));
          }
          if (type === 'error') {
            set((s) => ({
              streamingMessage: null,
              streamingThinking: null,
              streaming: false,
              messages: {
                ...s.messages,
                [activeId]: [
                  ...(s.messages[activeId] ?? []),
                  { role: 'assistant' as const, content: `⚠️ 回复失败：${parseLLMError(data.message).message}` },
                ],
              },
            }));
            toast.error(parseLLMError(data.message).message);
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        set({ streamingMessage: null, streamingThinking: null, streaming: false });
        const parsed = parseLLMError(e?.message);
        toast.error(parsed.message);
      } else {
        // 用户中断：保留部分回答
        const partial = get().streamingMessage ?? '';
        set((s) => ({
          streamingMessage: null,
          streamingThinking: null,
          streaming: false,
          messages: partial
            ? {
                ...s.messages,
                [activeId!]: [
                  ...(s.messages[activeId!] ?? []),
                  { role: 'assistant', content: partial + '\n\n（已中断）' },
                ],
              }
            : s.messages,
        }));
      }
    } finally {
      set({ abortCtrl: null });
      if (!get().streaming) set({ streamingMessage: null });
    }
  },

  stopStreaming: () => {
    get().abortCtrl?.abort();
  },
}));
