import { create } from 'zustand';
import { toast } from 'sonner';
import { useProjectStore } from '../../../shared/store/projectStore';
import { parseLLMError } from './llmErrors';

export interface PlanStep {
  skill: string;
  desc: string;
  params: Record<string, unknown>;
}

export interface Strategy {
  id: string;
  label: string;
  description: string;
  plan: PlanStep[];
}

export interface TaskData {
  id: number;
  intent: string;
  plan: PlanStep[];
  status: string;
  current_step: number;
  total_steps: number;
  result: Record<string, unknown>;
  error: string | null;
  context: { summary?: string; scope?: string[]; document_ids?: number[] };
  strategies: Strategy[];
  selected_strategy: string | null;
  uploaded_files: string[];
  conversation_id: number | null;
  created_at: string;
  updated_at: string;
  finished_at: string | null;
}

/** Agent 处理阶段（用于显示细化进度） */
export type AgentPhase = 'idle' | 'uploading' | 'understanding' | 'strategizing' | 'executing' | 'done' | 'error';

export interface AgentMessage {
  role: 'user' | 'agent';
  content?: string;
  files?: string[];
  card?: 'understand' | 'strategies' | 'progress' | 'result' | 'chat'
       | 'test_points'      // 审阅面板阶段1
       | 'case_review';     // 审阅面板阶段3
  thinking?: string;                   // 对话模式的思考过程（落定后存）
  taskId?: number;
}

/** 审阅面板中的单条用例 */
export interface ReviewCase {
  id: number
  title: string
  type: string
  priority: string
  test_design: string
  status: string
  description?: string
  content: Record<string, unknown>
  source?: string
  batch_id?: string
  task_id?: number
  version_id?: number | null
}

/** 单个 Task 的用例审阅状态 */
export interface ReviewState {
  caseIds: number[]
  cases: ReviewCase[]
  selectedIds: Set<number>
  editingId: number | null
  targetVersionId: number | null
  syncStatus: 'idle' | 'confirming' | 'syncing' | 'done'
  batchId: string | null
  loaded: boolean    // batch 是否已请求加载完毕（区分"加载中"与"空批次"）
  loadError: string | null
}

/** ReAct Agent 的决策类型 */
export type Decision = 'continue' | 'retry' | 'fix' | 'abort'

/** 单条 trace 记录：一次 action/observation/reflection 循环 */
export interface TraceEntry {
  step_index: number
  iteration: number
  action: { skill: string; desc: string; params?: Record<string, unknown> }
  observation: Record<string, unknown>
  reflection: { thought: string; decision: Decision; reasoning: string; confidence: number } | null
  decision: Decision
}

/** 任务中止时的根因分析结果 */
export interface TaskRca {
  step_index: number
  reason: string
  rca: Record<string, unknown>
  trace: TraceEntry[]
}

interface TaskState {
  messagesByTask: Record<number, AgentMessage[]>;  // 按 taskId 分桶的消息缓存
  messages: AgentMessage[];
  currentTask: TaskData | null;
  tasks: TaskData[];                   // Task 历史列表（侧边栏渲染）
  pendingFiles: File[];                // 待发送的文件（先暂存，发送时才上传）
  pendingFileNames: string[];
  stepLogs: { step_index: number; type: string; skill?: string; desc?: string; result?: Record<string, unknown>; error?: string; current?: number; total?: number }[];
  phase: AgentPhase;                   // 当前 Agent 处理阶段
  phaseMessage: string;                // 阶段提示文案
  selectedStrategy: string | null;
  streamingThinking: string | null;    // 流式思考过程缓冲（reasoning token）
  streamingMessage: string | null;     // 流式对话回复缓冲（content token）
  thinkingLevel: 'off' | 'low' | 'medium' | 'high';  // 当前思考级别
  kbMode: 'off' | 'auto' | 'manual';   // KB模式：关闭/自动向量/手动选文档
  selectedDocIds: number[];             // 手动档选中的文档ID
  abortCtrl: AbortController | null;   // 流式中断控制
  review: Record<number, ReviewState>; // taskId -> 该任务的用例审阅状态
  trace: Record<number, Record<number, TraceEntry[]>>;  // taskId -> stepIndex -> entries
  rca: Record<number, TaskRca | null>;  // taskId -> rca

  // Actions
  addPendingFiles: (files: File[]) => void;
  removePendingFile: (index: number) => void;
  setThinkingLevel: (level: 'off' | 'low' | 'medium' | 'high') => void;
  setKbMode: (mode: 'off' | 'auto' | 'manual') => void;
  setSelectedDocIds: (ids: number[]) => void;
  sendIntent: (text: string) => Promise<void>;
  _sendTask: (text: string, uploadedFiles: { filename: string; content: string }[], projectId: number | null, versionId: number | null, thinkingLevel: string, useKb: boolean, documentIds?: number[], conversationId?: number) => Promise<void>;  // 统一任务管道（LLM做意图识别）
  _sendIntentSync: (intent: string, uploadedFiles: { filename: string; content: string }[], projectId: number | null, versionId: number | null, documentIds?: number[], conversationId?: number) => Promise<void>;
  stopStreaming: () => void;           // 中断流式
  selectStrategy: (strategyId: string) => Promise<void>;
  selectTask: (id: number) => Promise<void>;    // 加载历史 Task 到工作台（从后端加载持久化消息）
  loadTasks: () => Promise<void>;      // 加载 Task 历史列表
  deleteTask: (id: number) => Promise<void>;
  resetConversation: () => void;
  streamTask: (taskId: number) => Promise<void>;  // SSE 流式监听

  // 两阶段生成闭环
  generateBatch: (taskId: number, testPoints: Record<string, unknown>[], projectId?: number | null, versionId?: number | null) => Promise<void>;

  // 用例审阅面板相关 actions
  loadBatchCases: (taskId: number, batchId: string) => Promise<void>;
  toggleSelect: (taskId: number, caseId: number) => void;
  toggleSelectAll: (taskId: number) => void;
  updateReviewCase: (taskId: number, caseId: number, fields: Partial<ReviewCase>) => Promise<void>;
  syncToVersion: (taskId: number, versionId: number, deleteUnselected: boolean) => Promise<void>;
}

const BASE = '/api/modules/ai/tasks';
const CASE_BASE = '/api/modules/testcase/testcases';  // 用例审阅面板调用的用例 API

const PHASE_MESSAGES: Record<AgentPhase, string> = {
  idle: '',
  uploading: '上传并解析文件中…',
  understanding: '阅读文档、理解需求中…',
  strategizing: '分析测试范围、制定策略中…',
  executing: '执行测试任务中…',
  done: '任务完成',
  error: '处理失败',
};

/** 从 task 字段重建消息流（用于首次加载历史 task） */
function _rebuildMessages(task: TaskData): AgentMessage[] {
  const msgs: AgentMessage[] = [];
  msgs.push({
    role: 'user',
    content: task.intent || undefined,
    files: task.uploaded_files?.length ? task.uploaded_files : undefined,
  });
  if (task.context?.summary) {
    msgs.push({ role: 'agent', card: 'understand', taskId: task.id, content: task.context.summary });
  }
  if (task.strategies && task.strategies.length > 0) {
    msgs.push({ role: 'agent', card: 'strategies', taskId: task.id });
  }
  const finishedStatuses = ['done', 'failed', 'cancelled'];
  if (finishedStatuses.includes(task.status)) {
    msgs.push({ role: 'agent', card: 'result', taskId: task.id });
  }
  return msgs;
}

/** 后端 Message 格式（来自 /tasks/{id}/messages） */
interface DbMessage {
  role: string;
  content: string;
  task_id?: number | null;
  created_at?: string | null;
}

/** 从后端加载任务的持久化消息（chat 类消息，用于补充卡片之间的对话历史） */
async function loadTaskMessages(taskId: number): Promise<DbMessage[]> {
  const r = await fetch(`/api/modules/ai/tasks/${taskId}/messages`);
  if (!r.ok) return [];
  const data = await r.json();
  return data.messages || [];
}

/** 将 DB 消息中属于 chat 交互的（非结构性卡片）转为 AgentMessage 补充到消息流中 */
function _supplementChatMessages(existing: AgentMessage[], dbMessages: DbMessage[]): AgentMessage[] {
  // 只取 user 和纯 assistant 消息（不含结构性内容的），过滤掉与已有卡片重复的
  const result = [...existing];
  for (const m of dbMessages) {
    // 跳过已在 _rebuildMessages 中覆盖的结构性消息（understand, strategies, result）
    const content = (m.content || '').trim();
    if (content.startsWith('【需求理解】') || content.startsWith('【测试策略建议】') ||
        content.startsWith('选择策略：') || content.includes('任务执行完成') || content.includes('任务执行失败')) {
      continue;
    }
    // 检查是否与已有消息重复
    const isDuplicate = existing.some(e => e.content === m.content && e.role === (m.role === 'assistant' ? 'agent' : 'user'));
    if (!isDuplicate) {
      result.push({
        role: (m.role === 'assistant' ? 'agent' : 'user') as 'user' | 'agent',
        content: m.content || undefined,
        card: 'chat' as const,
        taskId: m.task_id ?? undefined,
      });
    }
  }
  return result;
}

export const useTaskStore = create<TaskState>((set, get) => ({
  messagesByTask: {},
  messages: [],
  currentTask: null,
  tasks: [],
  pendingFiles: [],
  pendingFileNames: [],
  stepLogs: [],
  phase: 'idle',
  phaseMessage: '',
  selectedStrategy: null,
  streamingThinking: null,
  streamingMessage: null,
  thinkingLevel: 'off',
  kbMode: 'off',
  selectedDocIds: [],
  abortCtrl: null,
  review: {} as Record<number, ReviewState>,
  trace: {} as Record<number, Record<number, TraceEntry[]>>,
  rca: {} as Record<number, TaskRca | null>,

  addPendingFiles: (files: File[]) => {
    set((s) => ({
      pendingFiles: [...s.pendingFiles, ...files],
      pendingFileNames: [...s.pendingFileNames, ...files.map((f) => f.name)],
    }));
  },

  setThinkingLevel: (level) => set({ thinkingLevel: level }),
  setKbMode: (mode) => set({ kbMode: mode }),
  setSelectedDocIds: (ids) => set({ selectedDocIds: ids }),

  stopStreaming: () => {
    get().abortCtrl?.abort();
  },

  removePendingFile: (index: number) => {
    set((s) => ({
      pendingFiles: s.pendingFiles.filter((_, i) => i !== index),
      pendingFileNames: s.pendingFileNames.filter((_, i) => i !== index),
    }));
  },

  sendIntent: async (text: string) => {
    const { pendingFiles, pendingFileNames, thinkingLevel, kbMode, selectedDocIds, currentTask } = get();
    const { currentProjectId, currentVersionId } = useProjectStore.getState();
    const hasFiles = pendingFiles.length > 0;
    const hasText = text.trim().length > 0;
    if (!hasFiles && !hasText) return;

    // KB模式 → use_kb flag
    const useKb = kbMode !== 'off';
    // 手动档：用用户勾选的文档ID；自动档：null（让RAG自己检索）
    const effectiveDocIds = kbMode === 'manual' && selectedDocIds.length > 0 ? selectedDocIds : undefined;

    // 继承上一任务的 document_ids 和 conversation_id（统一管道：由LLM做意图识别）
    const inheritedDocIds: number[] = (!hasFiles && currentTask?.context?.document_ids)
      ? currentTask.context.document_ids : [];

    // 添加用户消息
    set((s) => {
      const tid = s.currentTask?.id;
      const newMsgs = [...s.messages, {
        role: 'user' as const,
        content: hasText ? text : undefined,
        files: hasFiles ? pendingFileNames : undefined,
      }];
      return {
        messages: newMsgs,
        messagesByTask: tid ? { ...s.messagesByTask, [tid]: newMsgs } : s.messagesByTask,
        pendingFiles: [],
        pendingFileNames: [],
      };
    });

    // 有文件时先上传
    let uploadedFiles: { filename: string; content: string }[] = [];
    let docIds: number[] = [];
    if (hasFiles) {
      set({ phase: 'uploading', phaseMessage: PHASE_MESSAGES.uploading });
      const formData = new FormData();
      for (const f of pendingFiles) formData.append('files', f);
      const uploadRes = await fetch(`${BASE}/upload`, { method: 'POST', body: formData });
      if (uploadRes.ok) {
        const data = await uploadRes.json();
        uploadedFiles = data.files || [];
        docIds = data.document_ids || [];
      }
    }

    const finalDocIds = hasFiles ? docIds : [...(docIds.length ? docIds : inheritedDocIds)];
    // 手动档：合并用户选择的文档ID
    const allDocIds = effectiveDocIds
      ? [...new Set([...finalDocIds, ...effectiveDocIds])]
      : finalDocIds;
    const convId = currentTask?.conversation_id ?? undefined;
    await get()._sendTask(text, uploadedFiles, currentProjectId, currentVersionId, thinkingLevel, useKb, allDocIds, convId);
  },

  // 统一任务管道：所有消息走 understand → strategize → execute（LLM 做意图识别）
  _sendTask: async (text: string, uploadedFiles: { filename: string; content: string }[], currentProjectId: number | null, currentVersionId: number | null, thinkingLevel: string, useKb: boolean, documentIds?: number[], conversationId?: number) => {
    try {
      // understand + strategize（流式 SSE）
      set({ phase: 'understanding', phaseMessage: PHASE_MESSAGES.understanding, streamingThinking: '' });
      const abortCtrl = new AbortController();
      set({ abortCtrl });

      const r = await fetch(`${BASE}/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          intent: text || '请分析我上传的文档并生成测试用例',
          project_id: currentProjectId,
          version_id: currentVersionId,
          files: uploadedFiles,
          thinking_level: thinkingLevel,
          use_kb: useKb,
          document_ids: documentIds ?? [],  // 贯穿全链路的文档ID
          conversation_id: conversationId ?? undefined,  // 关联已有会话（修复拆分问题）
        }),
        signal: abortCtrl.signal,
      });

      if (!r.ok || !r.body) {
        if (r.status === 404 || r.status === 501 || r.status === 405) {
          await get()._sendIntentSync(text || '请分析我上传的文档并生成测试用例', uploadedFiles, currentProjectId, currentVersionId, documentIds, conversationId);
          return;
        }
        const errText = await r.text().catch(() => '');
        const parsed = parseLLMError(errText || `HTTP ${r.status}`, r.status);
        toast.error(parsed.message);
        set((s) => {
          const tid = s.currentTask?.id;
          const newMsgs = [...s.messages, { role: 'agent' as const, content: parsed.message }];
          return {
            phase: 'error' as const, phaseMessage: parsed.message, streamingThinking: null, streamingMessage: null, abortCtrl: null,
            messages: newMsgs,
            messagesByTask: tid ? { ...s.messagesByTask, [tid]: newMsgs } : s.messagesByTask,
          };
        });
        return;
      }

      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let task: TaskData | null = null;

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

          if (type === 'phase') {
            const p = data.phase as AgentPhase;
            set({ phase: p, phaseMessage: PHASE_MESSAGES[p] || '' });
          }
          if (type === 'thinking') {
            set((s) => ({ streamingThinking: (s.streamingThinking || '') + (data.text || '') }));
          }
          if (type === 'understand_done') {
            set((s) => {
              const tid = s.currentTask?.id;
              const newMsgs = [...s.messages, { role: 'agent' as const, card: 'understand' as const, content: data.summary }];
              return {
                streamingThinking: null,
                messages: newMsgs,
                messagesByTask: tid ? { ...s.messagesByTask, [tid]: newMsgs } : s.messagesByTask,
              };
            });
          }
          if (type === 'done') {
            task = data.task as TaskData;
            set((s) => {
              const tid = task!.id;
              const hasStrategies = task!.strategies && task!.strategies.length > 0;
              const newMsgs: AgentMessage[] = hasStrategies
                ? [...s.messages, { role: 'agent', card: 'strategies', taskId: task!.id }]
                : s.messages;
              return {
                currentTask: task,
                phase: 'idle' as const, phaseMessage: '', streamingThinking: null, streamingMessage: null, abortCtrl: null,
                messages: newMsgs,
                messagesByTask: hasStrategies ? { ...s.messagesByTask, [tid]: newMsgs } : s.messagesByTask,
              };
            });
            get().loadTasks();
          }
          if (type === 'error') {
            const parsed = parseLLMError(data.message);
            toast.error(parsed.message);
            set((s) => {
              const tid = s.currentTask?.id;
              const newMsgs = [...s.messages, { role: 'agent' as const, content: parsed.message }];
              return {
                phase: 'error' as const, phaseMessage: parsed.message,
                streamingThinking: null, streamingMessage: null, abortCtrl: null,
                messages: newMsgs,
                messagesByTask: tid ? { ...s.messagesByTask, [tid]: newMsgs } : s.messagesByTask,
              };
            });
            // 后端已删除失败任务 -> 刷新列表让 currentTask 失效，避免切换 tab 后出现重复会话
            get().loadTasks();
          }
        }
      }
    } catch (e: any) {
      if (e.name === 'AbortError') {
        set((s) => {
          const tid = s.currentTask?.id;
          const newMsgs = [...s.messages, { role: 'agent' as const, content: '（已取消）' }];
          return {
            phase: 'idle' as const, phaseMessage: '已取消', streamingThinking: null, streamingMessage: null, abortCtrl: null,
            messages: newMsgs,
            messagesByTask: tid ? { ...s.messagesByTask, [tid]: newMsgs } : s.messagesByTask,
          };
        });
      } else {
        const parsed = parseLLMError((e as Error)?.message);
        toast.error(parsed.message);
        set((s) => {
          const tid = s.currentTask?.id;
          const newMsgs = [...s.messages, { role: 'agent' as const, content: parsed.message }];
          return {
            phase: 'error' as const, phaseMessage: parsed.message,
            streamingThinking: null, streamingMessage: null, abortCtrl: null,
            messages: newMsgs,
            messagesByTask: tid ? { ...s.messagesByTask, [tid]: newMsgs } : s.messagesByTask,
          };
        });
        // 失败任务可能已持久化但执行异常 -> 刷新列表同步状态
        get().loadTasks();
      }
    }
  },

  // 降级路径：流式端点不可用时回退到同步 POST /tasks（旧逻辑）
  _sendIntentSync: async (intent: string, uploadedFiles: { filename: string; content: string }[], projectId: number | null, versionId: number | null, documentIds?: number[], conversationId?: number) => {
    set({ phase: 'understanding', phaseMessage: PHASE_MESSAGES.understanding });
    const r = await fetch(`${BASE}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        intent,
        project_id: projectId,
        version_id: versionId,
        files: uploadedFiles,
        document_ids: documentIds ?? [],
        conversation_id: conversationId ?? undefined,
      }),
    });
    if (!r.ok) {
      const msg = await r.text();
      set((s) => {
        const tid = s.currentTask?.id;
        const newMsgs = [...s.messages, { role: 'agent' as const, content: `处理失败: ${msg}` }];
        return {
          phase: 'error' as const, phaseMessage: `处理失败: ${msg}`,
          messages: newMsgs,
          messagesByTask: tid ? { ...s.messagesByTask, [tid]: newMsgs } : s.messagesByTask,
        };
      });
      return;
    }
    const task: TaskData = await r.json();
    set((s) => {
      const tid = task.id;
      const newMsgs = [...s.messages, {
        role: 'agent' as const, card: 'understand' as const, taskId: task.id,
        content: task.context?.summary,
      }];
      return {
        currentTask: task,
        phase: 'idle' as const, phaseMessage: '',
        messages: newMsgs,
        messagesByTask: { ...s.messagesByTask, [tid]: newMsgs },
      };
    });
    if (task.strategies && task.strategies.length > 0) {
      set((s) => {
        const tid = task.id;
        const newMsgs = [...s.messages, { role: 'agent' as const, card: 'strategies' as const, taskId: task.id }];
        return {
          messages: newMsgs,
          messagesByTask: { ...s.messagesByTask, [tid]: newMsgs },
        };
      });
    }
    get().loadTasks();
  },

  // 加载历史 Task 到工作台：_rebuildMessages 构建结构性卡片 + DB消息补充chat历史
  selectTask: async (id: number) => {
    const { tasks, phase, messagesByTask } = get();
    if (phase !== 'idle' && phase !== 'done' && phase !== 'error') return;
    const task = tasks.find((t) => t.id === id);
    if (!task) return;

    // 从分桶缓存恢复，或重建（结构性卡片始终由 _rebuildMessages 保证）
    let msgs: AgentMessage[] = messagesByTask[id] ?? [];
    if (msgs.length === 0) {
      msgs = _rebuildMessages(task);
      // 补充 DB 中的 chat 历史（不覆盖结构性卡片）
      try {
        const dbMessages = await loadTaskMessages(id);
        if (dbMessages.length > 0) {
          msgs = _supplementChatMessages(msgs, dbMessages);
        }
      } catch { /* 静默降级 */ }
    }

    const finishedStatuses = ['done', 'failed', 'cancelled'];
    set({
      currentTask: task,
      messages: msgs,
      messagesByTask: { ...messagesByTask, [id]: msgs },
      stepLogs: [],
      phase: finishedStatuses.includes(task.status) ? (task.status === 'done' ? 'done' : 'idle') : 'idle',
      phaseMessage: '',
      selectedStrategy: task.selected_strategy,
      streamingThinking: null,
      streamingMessage: null,
      
      abortCtrl: null,
    });
  },

  selectStrategy: async (strategyId: string) => {
    const { currentTask } = get();
    if (!currentTask) return;
    const { currentProjectId, currentVersionId } = useProjectStore.getState();
    set({ selectedStrategy: strategyId, phase: 'executing', phaseMessage: PHASE_MESSAGES.executing });

    // Agent 执行进度卡片
    set((s) => {
      const tid = currentTask.id;
      const newMsgs = [...s.messages, { role: 'agent' as const, card: 'progress' as const, taskId: currentTask.id }];
      return {
        messages: newMsgs,
        messagesByTask: { ...s.messagesByTask, [tid]: newMsgs },
        stepLogs: [],
      };
    });

    try {
      const r = await fetch(`${BASE}/${currentTask.id}/select`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategy_id: strategyId,
          project_id: currentProjectId,
          version_id: currentVersionId,
        }),
      });
      if (!r.ok) {
        const msg = await r.text();
        set((s) => {
          const tid = currentTask.id;
          const newMsgs = [...s.messages, { role: 'agent' as const, content: `执行失败: ${msg}` }];
          return {
            phase: 'error' as const, phaseMessage: `执行失败: ${msg}`,
            messages: newMsgs,
            messagesByTask: { ...s.messagesByTask, [tid]: newMsgs },
          };
        });
        return;
      }
      const task: TaskData = await r.json();
      set({ currentTask: task });
      get().streamTask(currentTask.id);
    } catch (e) {
      set({
        phase: 'error', phaseMessage: `网络错误: ${(e as Error).message}`,
      });
    }
  },

  // 内部：SSE 流式监听
  streamTask: async (taskId: number) => {
    try {
      const res = await fetch(`${BASE}/${taskId}/stream`);
      if (!res.body) return;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

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

          if (type === 'step_start') {
            set((s) => ({
              phaseMessage: `${data.current}/${data.total}: ${data.desc}`,
              stepLogs: [...s.stepLogs, {
                step_index: data.step_index, type: 'step_start',
                skill: data.skill, desc: data.desc, current: data.current, total: data.total,
              }],
            }));
          }
          if (type === 'step_done') {
            set((s) => ({
              stepLogs: s.stepLogs.map((log) =>
                log.step_index === data.step_index && log.type === 'step_start'
                  ? { ...log, type: 'step_done', result: data.result } : log
              ),
            }));
          }
          if (type === 'step_error') {
            set((s) => ({
              stepLogs: s.stepLogs.map((log) =>
                log.step_index === data.step_index && log.type === 'step_start'
                  ? { ...log, type: 'step_error', error: data.error } : log
              ),
            }));
          }
          // 进度事件（批量生成时实时更新进度文案）
          if (type === 'progress') {
            set({ phaseMessage: data.message || '处理中…' });
          }
          // ReAct Agent 事件：action / observation / reflection / decision / aborted
          if (type === 'action') {
            const { step_index, iteration, skill, desc, params } = data;
            set((s) => {
              const taskTrace = s.trace[taskId] || {};
              const stepEntries = taskTrace[step_index] ? [...taskTrace[step_index]] : [];
              while (stepEntries.length <= iteration) stepEntries.push({} as TraceEntry);
              stepEntries[iteration] = {
                ...(stepEntries[iteration] || {}),
                step_index, iteration,
                action: { skill, desc, params: params || {} },
                observation: {}, reflection: null, decision: 'continue',
              };
              return { trace: { ...s.trace, [taskId]: { ...taskTrace, [step_index]: stepEntries } } };
            });
          }
          if (type === 'observation') {
            const { step_index, iteration } = data;
            set((s) => {
              const taskTrace = s.trace[taskId] || {};
              const stepEntries = taskTrace[step_index] ? [...taskTrace[step_index]] : [];
              while (stepEntries.length <= iteration) stepEntries.push({} as TraceEntry);
              stepEntries[iteration] = {
                ...(stepEntries[iteration] || {}),
                observation: { status: data.status, failures: data.failures, ...data },
              };
              return { trace: { ...s.trace, [taskId]: { ...taskTrace, [step_index]: stepEntries } } };
            });
          }
          if (type === 'reflection' && data.result) {
            const { step_index, iteration, result } = data;
            set((s) => {
              const taskTrace = s.trace[taskId] || {};
              const stepEntries = taskTrace[step_index] ? [...taskTrace[step_index]] : [];
              if (stepEntries[iteration]) {
                stepEntries[iteration] = { ...stepEntries[iteration], reflection: result };
              }
              return { trace: { ...s.trace, [taskId]: { ...taskTrace, [step_index]: [...stepEntries] } } };
            });
          }
          if (type === 'decision') {
            const { step_index, iteration, decision } = data;
            set((s) => {
              const taskTrace = s.trace[taskId] || {};
              const stepEntries = taskTrace[step_index] ? [...taskTrace[step_index]] : [];
              if (stepEntries[iteration]) {
                stepEntries[iteration] = { ...stepEntries[iteration], decision };
              }
              return { trace: { ...s.trace, [taskId]: { ...taskTrace, [step_index]: [...stepEntries] } } };
            });
          }
          if (type === 'aborted') {
            set((s) => ({
              rca: { ...s.rca, [taskId]: { step_index: data.step_index, reason: data.reason, rca: data.rca || {}, trace: data.trace || [] } },
            }));
          }
          if (type === 'done') {
            const tr = await fetch(`${BASE}/${taskId}`);
            const finalTask: TaskData = await tr.json();
            // 按 result 产物分支决定卡片类型：
            // - result.batch_id 存在 → 批量生成产物，弹 case_review 审阅卡片
            // - result.steps 含 extract_test_points 且产 test_points → 弹 test_points 确认卡片
            // - 否则 → 默认 result 卡片
            const result = (finalTask.result || {}) as Record<string, unknown>;
            const batchId = (result.batch_id as string | undefined) ?? null;
            let card: AgentMessage['card'] = 'result';
            let content: string | undefined;
            if (batchId) {
              card = 'case_review';
            } else {
              // step 字典里 skill 返回字段被展开到顶层（executor.py:108 / reactor.py:215），
              // 故 test_points 直接在 step 对象上，而非 step.result.test_points。
              const steps = Array.isArray(result.steps) ? result.steps as Array<Record<string, unknown>> : [];
              const tpStep = steps.find((st) => st?.skill === 'extract_test_points');
              const tps = tpStep?.test_points as unknown[] | undefined;
              if (tps && Array.isArray(tps) && tps.length > 0) {
                card = 'test_points';
                content = JSON.stringify(tps);
              }
            }
            set((s) => {
              const newMsgs = [...s.messages, { role: 'agent' as const, card, taskId, ...(content ? { content } : {}) }];
              return {
                currentTask: finalTask, phase: 'done' as const, phaseMessage: PHASE_MESSAGES.done,
                messages: newMsgs,
                messagesByTask: { ...s.messagesByTask, [taskId]: newMsgs },
              };
            });
            return;
          }
          if (type === 'error') {
            const tr = await fetch(`${BASE}/${taskId}`);
            const finalTask: TaskData = await tr.json();
            set((s) => {
              const newMsgs = [...s.messages, { role: 'agent' as const, card: 'result' as const, taskId }];
              return {
                currentTask: finalTask, phase: 'error' as const, phaseMessage: finalTask.error || '执行失败',
                messages: newMsgs,
                messagesByTask: { ...s.messagesByTask, [taskId]: newMsgs },
              };
            });
            return;
          }
          if (type === 'cancelled') {
            set({ phase: 'idle', phaseMessage: '已取消' });
            return;
          }
        }
      }
    } catch {
      set({ phase: 'error', phaseMessage: '连接中断' });
    }
  },

  // 两阶段生成闭环 · 阶段2：用户确认测试点范围后触发批量生成
  generateBatch: async (taskId, testPoints, projectId, versionId) => {
    set({ phase: 'executing', phaseMessage: '批量生成用例中…' });
    // project/version 优先用传入值，否则从全局 projectStore 读当前选中
    const ps = useProjectStore.getState();
    const pid = projectId !== undefined ? projectId : ps.currentProjectId;
    const vid = versionId !== undefined ? versionId : ps.currentVersionId;
    const res = await fetch(`${BASE}/${taskId}/generate-batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        test_points: testPoints,
        project_id: pid ?? null,
        version_id: vid ?? null,
      }),
    });
    if (!res.ok) {
      const msg = `批量生成请求失败（${res.status}）`;
      set({ phase: 'error', phaseMessage: msg });
      toast.error(msg);
      return;
    }
    const task: TaskData = await res.json();
    set({ currentTask: task });
    // 监听生成进度；done 事件处理器会按 result.batch_id 自动推 case_review 卡片
    await get().streamTask(task.id);
  },

  loadTasks: async () => {
    try {
      const { currentProjectId } = useProjectStore.getState();
      const q = currentProjectId !== null ? `?project_id=${currentProjectId}` : '';
      const r = await fetch(`${BASE}${q}`);
      if (!r.ok) return;
      const tasks: TaskData[] = await r.json();
      // 防御：API 返回空数组时不覆盖现有列表（避免会话列表闪烁消失）
      if (!Array.isArray(tasks)) return;
      set((s) => {
        // 验证 currentTask 仍在列表中
        if (s.currentTask && !tasks.some((t) => t.id === s.currentTask!.id)) {
          // task 被后端删除：保留 messages 供用户查看错误提示，但回到 idle
          return {
            tasks,
            phase: 'idle' as const,
            phaseMessage: '',
          };
        }
        return { tasks };
      });
    } catch {
      // 静默失败：网络异常不覆盖已有数据
    }
  },

  deleteTask: async (id: number) => {
    const r = await fetch(`${BASE}/${id}`, { method: 'DELETE' });
    if (!r.ok) return;  // API 失败时不更新本地状态（防止删除后恢复）
    set((s) => {
      const remaining = s.tasks.filter((t) => t.id !== id);
      const restMessages = { ...s.messagesByTask };
      delete restMessages[id];
      if (s.currentTask?.id === id) {
        return {
          tasks: remaining,
          messagesByTask: restMessages,
          currentTask: null,
          messages: [],
          pendingFiles: [],
          pendingFileNames: [],
          stepLogs: [],
          phase: 'idle',
          phaseMessage: '',
          selectedStrategy: null,
          streamingThinking: null,
          streamingMessage: null,
          
          abortCtrl: null,
        };
      }
      return { tasks: remaining, messagesByTask: restMessages };
    });
  },

  resetConversation: () => {
    set({
      messagesByTask: {},
      messages: [], currentTask: null, pendingFiles: [], pendingFileNames: [],
      stepLogs: [], phase: 'idle', phaseMessage: '', selectedStrategy: null,
      streamingThinking: null, streamingMessage: null, abortCtrl: null,
    });
  },

  // 用例审阅面板：加载某批次的用例到审阅状态
  loadBatchCases: async (taskId, batchId) => {
    try {
      const res = await fetch(`${CASE_BASE}/batch/${batchId}`);
      if (!res.ok) {
        set((s) => ({
          review: {
            ...s.review,
            [taskId]: {
              caseIds: [], cases: [], selectedIds: new Set(),
              editingId: null, targetVersionId: null, syncStatus: 'idle',
              batchId, loaded: true, loadError: `加载失败（${res.status}）`,
            },
          },
        }));
        return;
      }
      const cases: ReviewCase[] = await res.json();
      set((s) => ({
        review: {
          ...s.review,
          [taskId]: {
            caseIds: cases.map((c) => c.id),
            cases,
            selectedIds: new Set(cases.map((c) => c.id)),
            editingId: null,
            targetVersionId: null,
            syncStatus: 'idle',
            batchId,
            loaded: true,
            loadError: null,
          },
        },
      }));
    } catch {
      set((s) => ({
        review: {
          ...s.review,
          [taskId]: {
            caseIds: [], cases: [], selectedIds: new Set(),
            editingId: null, targetVersionId: null, syncStatus: 'idle',
            batchId, loaded: true, loadError: '网络错误',
          },
        },
      }));
    }
  },

  // 切换单条用例的选中态
  toggleSelect: (taskId, caseId) => {
    set((s) => {
      const r = s.review[taskId];
      if (!r) return {};
      const next = new Set(r.selectedIds);
      if (next.has(caseId)) next.delete(caseId);
      else next.add(caseId);
      return { review: { ...s.review, [taskId]: { ...r, selectedIds: next } } };
    });
  },

  // 全选 / 全不选
  toggleSelectAll: (taskId) => {
    set((s) => {
      const r = s.review[taskId];
      if (!r) return {};
      const allSelected = r.selectedIds.size === r.cases.length;
      return {
        review: {
          ...s.review,
          [taskId]: {
            ...r,
            selectedIds: allSelected ? new Set() : new Set(r.cases.map((c) => c.id)),
          },
        },
      };
    });
  },

  // 更新单条用例字段，并刷新该批次
  updateReviewCase: async (taskId, caseId, fields) => {
    await fetch(`${CASE_BASE}/${caseId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(fields),
    });
    const r = get().review[taskId];
    if (r?.batchId) {
      await get().loadBatchCases(taskId, r.batchId);
    }
  },

  // 将选中用例同步到指定版本（可选删除未选中）
  syncToVersion: async (taskId, versionId, deleteUnselected) => {
    const r = get().review[taskId];
    if (!r) return;
    set((s) => ({
      review: { ...s.review, [taskId]: { ...r, syncStatus: 'syncing' } },
    }));
    await fetch(`${CASE_BASE}/batch-sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        case_ids: Array.from(r.selectedIds),
        version_id: versionId,
        delete_unselected: deleteUnselected,
        batch_id: r.batchId,
      }),
    });
    set((s) => ({
      review: { ...s.review, [taskId]: { ...r, syncStatus: 'done' } },
    }));
  },
}));
