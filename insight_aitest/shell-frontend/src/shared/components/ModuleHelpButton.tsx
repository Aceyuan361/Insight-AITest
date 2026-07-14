/**
 * 模块帮助按钮 + 快速入门对话框。
 *
 * 用法：在任意模块的 header 右侧放置 <ModuleHelpButton namespace="ai" />，
 * 内容由 i18n 的 help.{namespace}.* 命名空间驱动。
 *
 * 结构（与 performance 模块 HelpDialog 一致）：标题 + 快速开始步骤 + 核心功能 + 关于。
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { HelpCircle } from 'lucide-react';

interface ModuleHelpButtonProps {
  /** i18n 命名空间，如 'ai' | 'kb' | 'testcase' | 'api' | 'ui' */
  namespace: string;
  /** 步骤数量（help.{ns}.steps.step1..stepN） */
  steps?: number;
}

export function ModuleHelpButton({ namespace, steps = 5 }: ModuleHelpButtonProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const ns = `help.${namespace}`;
  const helpLabel = t('menu.help');

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title={helpLabel}
        style={{
          background: 'none',
          border: 'none',
          color: 'var(--text-secondary)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          fontSize: 13,
          padding: '4px 8px',
        }}
        aria-label={helpLabel}
      >
        <HelpCircle size={15} strokeWidth={1.5} />
        <span style={{ fontSize: 13 }}>{helpLabel}</span>
      </button>
      {open && <ModuleHelpDialog namespace={ns} steps={steps} onClose={() => setOpen(false)} />}
    </>
  );
}

function ModuleHelpDialog({
  namespace,
  steps,
  onClose,
}: {
  namespace: string;
  steps: number;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const stepList = Array.from({ length: steps }, (_, i) => i + 1);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: 'var(--bg-card)',
          borderRadius: '12px',
          maxWidth: '700px',
          width: '90%',
          maxHeight: '80vh',
          border: '1px solid var(--border-strong)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 标题栏 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid var(--border-strong)' }}>
          <h2 style={{ color: 'var(--accent)', margin: 0, fontSize: '16px' }}>
            {t(`${namespace}.title`)}
          </h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', fontSize: '24px', cursor: 'pointer', padding: 0, lineHeight: 1 }}>
            ×
          </button>
        </div>

        {/* 内容 */}
        <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
          {/* 简介 */}
          <div style={{ color: 'var(--text-secondary)', lineHeight: '1.8', marginBottom: '8px' }}>
            {t(`${namespace}.intro`)}
          </div>

          {/* 快速开始 */}
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '12px', marginTop: '20px', fontSize: '16px' }}>
            {t('help.tabs.quickStart')}
          </h3>
          <ol style={{ color: 'var(--text-secondary)', lineHeight: '1.8' }}>
            {stepList.map((n) => (
              <li key={n}>{t(`${namespace}.steps.step${n}`)}</li>
            ))}
          </ol>

          {/* 核心功能 */}
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '12px', marginTop: '20px', fontSize: '16px' }}>
            {t(`${namespace}.features.title`)}
          </h3>
          <ul style={{ color: 'var(--text-secondary)', lineHeight: '1.8' }}>
            {stepList.map((_, i) => {
              const key = `${namespace}.features.item${i + 1}`;
              const val = t(key);
              // 未定义则跳过（i18next 返回 key 本身）
              if (val === key) return null;
              return <li key={i}>{val}</li>;
            })}
          </ul>

          {/* 提示 */}
          {t(`${namespace}.tip`) !== `${namespace}.tip` && (
            <p style={{ color: 'var(--warning)', fontSize: '13px', marginTop: '12px' }}>
              <i>{t(`${namespace}.tip`)}</i>
            </p>
          )}

          {/* 关于 */}
          <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid var(--border-strong)', color: 'var(--text-secondary)', fontSize: '13px', lineHeight: '1.8' }}>
            <p style={{ color: 'var(--accent)', fontWeight: 'bold', fontSize: '15px' }}>
              {t('help.about.projectName')} <span style={{ color: 'var(--text-secondary)' }}>v{t('help.about.versionValue')}</span>
            </p>
            <p>{t('help.about.description')}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ModuleHelpButton;
