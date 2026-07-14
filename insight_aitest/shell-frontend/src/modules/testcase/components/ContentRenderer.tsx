import { useTranslation } from 'react-i18next';

/** API/性能/UI 用例只读视图（首版预埋，待对应子系统就绪后激活编辑器）。 */
export function ContentRenderer({ type, content }: {
  type: string; content: Record<string, unknown>;
}) {
  const { t } = useTranslation();
  return (
    <div style={{ padding: 12, background: 'var(--bg-base)', borderRadius: 6, color: "var(--text-secondary)", fontSize: 13 }}>
      <div style={{ marginBottom: 8, color: "var(--text-muted)" }}>
        {t('testcase.readonlyTypePreview', { type })}
      </div>
      <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 12, color: "var(--text-secondary)" }}>
        {JSON.stringify(content, null, 2)}
      </pre>
    </div>
  );
}
