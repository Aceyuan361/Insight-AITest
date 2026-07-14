import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useTaskStore } from '../../store/taskStore';
import { glassPanelStrong, text, RADIUS } from '../agentStyles';
import { ReviewTable } from '../review/ReviewTable';
import { BatchSyncBar } from '../review/BatchSyncBar';

/** 用例审阅面板（阶段 3）：容器卡片，挂载时按 batch_id 加载用例，
 *  渲染表头 + ReviewTable + BatchSyncBar。
 *  batch_id 取自 currentTask.result.batch_id（agent 执行结果产物）。 */
export function CaseReviewCard({ taskId }: { taskId: number }) {
  const currentTask = useTaskStore((s) => s.currentTask);
  const loadBatchCases = useTaskStore((s) => s.loadBatchCases);
  const toggleSelect = useTaskStore((s) => s.toggleSelect);
  const toggleSelectAll = useTaskStore((s) => s.toggleSelectAll);
  const syncToVersion = useTaskStore((s) => s.syncToVersion);
  const reviewState = useTaskStore((s) => s.review[taskId]);

  // 从任务结果取 batch_id
  const batchId = (currentTask?.result?.batch_id as string | undefined) ?? null;
  // 避免重复加载：记录已请求过的 batchId
  const loadedKey = useRef<string | null>(null);

  useEffect(() => {
    if (batchId && loadedKey.current !== batchId) {
      loadedKey.current = batchId;
      loadBatchCases(taskId, batchId);
    }
  }, [batchId, taskId, loadBatchCases]);

  const cases = reviewState?.cases ?? [];
  const selectedIds = reviewState?.selectedIds ?? new Set<number>();
  const loaded = reviewState?.loaded ?? false;
  const loadError = reviewState?.loadError ?? null;
  const { t } = useTranslation();
  // 从结果取生成统计（全失败时用于空状态提示）
  const stats = (currentTask?.result?.stats as { failed?: number; generated?: number } | undefined) ?? null;

  if (!reviewState || (!loaded && cases.length === 0)) {
    // 未加载完（无 reviewState 或 batch 仍在请求中）
    return (
      <div
        style={{
          ...glassPanelStrong,
          padding: 24,
          borderRadius: RADIUS.lg,
          textAlign: 'center',
          color: text.muted,
          fontSize: 13,
        }}
      >
        {t('ai.loadingCases')}
      </div>
    );
  }

  if (loadError) {
    return (
      <div
        style={{
          ...glassPanelStrong,
          padding: 24,
          borderRadius: RADIUS.lg,
          textAlign: 'center',
          color: text.danger,
          fontSize: 13,
        }}
      >
        {t('ai.loadCasesFailed', { error: loadError })}
      </div>
    );
  }

  if (cases.length === 0) {
    // 已加载完但批次为空（生成全部失败）
    const failedHint = stats?.failed ? t('ai.genFailedHint', { count: stats.failed }) : t('ai.genAllFailedHint');
    return (
      <div
        style={{
          ...glassPanelStrong,
          padding: 24,
          borderRadius: RADIUS.lg,
          textAlign: 'center',
          color: text.muted,
          fontSize: 13,
        }}
      >
        {t('ai.noUsableCases', { hint: failedHint })}
      </div>
    );
  }

  return (
    <div
      style={{
        ...glassPanelStrong,
        borderRadius: RADIUS.lg,
        borderLeft: '3px solid rgba(91,140,123,0.5)',
        overflow: 'hidden',
      }}
    >
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ fontSize: 11, color: text.accent, fontWeight: 600, letterSpacing: '0.04em' }}>
          {t('ai.caseReviewTitle')}
        </div>
        <div style={{ fontSize: 12, color: text.muted, marginTop: 4 }}>
          {t('ai.caseReviewHint', { total: cases.length, selected: selectedIds.size })}
        </div>
      </div>

      <ReviewTable
        cases={cases}
        selectedIds={selectedIds}
        onToggle={(caseId) => toggleSelect(taskId, caseId)}
        onToggleAll={() => toggleSelectAll(taskId)}
        onSaved={() => {
          // 保存后若仍持有 batchId，则重新拉取该批次刷新
          if (reviewState.batchId) loadBatchCases(taskId, reviewState.batchId);
        }}
      />

      <BatchSyncBar
        selectedCount={selectedIds.size}
        totalCount={cases.length}
        syncStatus={reviewState.syncStatus}
        onSync={(versionId, deleteUnselected) =>
          syncToVersion(taskId, versionId, deleteUnselected)
        }
      />
    </div>
  );
}
