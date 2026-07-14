/**
 * 帮助对话框组件
 * 单页结构：快速开始 + 监控指标 + 平台支持 + 告警 + 报告 + 关于信息
 */
import { useTranslation } from 'react-i18next';

interface HelpDialogProps {
  onClose: () => void;
}

export default function HelpDialog({ onClose }: HelpDialogProps) {
  const { t } = useTranslation();

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
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
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          borderBottom: '1px solid var(--border-strong)',
        }}>
          <h2 style={{ color: "var(--accent)", margin: 0, fontSize: '16px' }}>{t('help.title')}</h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: "var(--text-secondary)",
              fontSize: '24px',
              cursor: 'pointer',
              padding: 0,
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>

        {/* 内容区域（单页滚动） */}
        <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
          {/* 快速开始 */}
          <h3 style={{ color: "var(--text-primary)", marginBottom: '12px', fontSize: '16px' }}>
            {t('help.tabs.quickStart')}
          </h3>
          <ol style={{ color: "var(--text-secondary)", lineHeight: '1.8' }}>
            <li>{t('help.quickStart.step1Desc')}</li>
            <li>{t('help.quickStart.step2Desc')}</li>
            <li>{t('help.quickStart.step3Desc')}</li>
            <li>{t('help.quickStart.step4Desc')}</li>
            <li>{t('help.quickStart.step5Desc')}</li>
          </ol>

          {/* 监控指标说明 */}
          <h3 style={{ color: "var(--text-primary)", marginBottom: '12px', marginTop: '20px', fontSize: '16px' }}>
            {t('help.tabs.metrics')}
          </h3>
          <div style={{ color: "var(--text-secondary)", lineHeight: '1.8' }}>
            <p><b>{t('help.metrics.cpuTitle')}</b>：{t('help.metrics.cpuDesc')}</p>
            <p><b>{t('help.metrics.memoryTitle')}</b>：{t('help.metrics.memoryDesc')}</p>
            <p><b>{t('help.metrics.fpsTitle')}</b>：{t('help.metrics.fpsDesc')}</p>
            <p><b>{t('help.metrics.networkTitle')}</b>：{t('help.metrics.networkDesc')}</p>
            <p><b>{t('help.metrics.gpuTitle')}</b>：{t('help.metrics.gpuDesc')}</p>
            <p style={{ color: "var(--warning)", fontSize: '13px', marginTop: '8px' }}>
              <i>{t('help.metrics.gpuNote')}</i>
            </p>
          </div>

          {/* 平台支持 */}
          <h3 style={{ color: "var(--text-primary)", marginBottom: '12px', marginTop: '20px', fontSize: '16px' }}>
            {t('help.platformSupport.title')}
          </h3>
          <div style={{ color: "var(--text-secondary)", lineHeight: '1.8' }}>
            <div style={{ marginBottom: '16px' }}>
              <p style={{ color: "var(--accent)", fontWeight: 'bold' }}>{t('help.platformSupport.android.title')}</p>
              <p style={{ marginLeft: '16px' }}>{t('help.platformSupport.android.osVersion')}</p>
              <p style={{ marginLeft: '16px' }}>{t('help.platformSupport.android.features')}</p>
              <p style={{ marginLeft: '16px', color: "var(--warning)" }}>{t('help.platformSupport.android.gpuStatus')}</p>
              <p style={{ marginLeft: '16px', fontSize: '13px' }}><i>{t('help.platformSupport.android.notes')}</i></p>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <p style={{ color: "var(--accent)", fontWeight: 'bold' }}>{t('help.platformSupport.ios.title')}</p>
              <p style={{ marginLeft: '16px' }}>{t('help.platformSupport.ios.osVersion')}</p>
              <p style={{ marginLeft: '16px' }}>{t('help.platformSupport.ios.features')}</p>
              <p style={{ marginLeft: '16px', color: "var(--warning)" }}>{t('help.platformSupport.ios.fpsStatus')}</p>
              <p style={{ marginLeft: '16px', color: "var(--error)" }}>{t('help.platformSupport.ios.gpuStatus')}</p>
              <p style={{ marginLeft: '24px', fontSize: '12px' }}>{t('help.platformSupport.ios.gpuReason1')}</p>
              <p style={{ marginLeft: '24px', fontSize: '12px' }}>{t('help.platformSupport.ios.gpuReason2')}</p>
              <p style={{ marginLeft: '16px', fontSize: '13px' }}><i>{t('help.platformSupport.ios.notes')}</i></p>
              <p style={{ marginLeft: '16px', fontSize: '13px' }}><i>{t('help.platformSupport.ios.windowsNote')}</i></p>
            </div>
          </div>

          {/* 告警功能 */}
          <h3 style={{ color: "var(--text-primary)", marginBottom: '12px', marginTop: '20px', fontSize: '16px' }}>
            {t('help.tabs.alerts')}
          </h3>
          <div style={{ color: "var(--text-secondary)", lineHeight: '1.8' }}>
            <p>{t('help.alertsFeature.description')}</p>
            <ul>
              <li>{t('help.alertsFeature.fpsAlert')}</li>
              <li>{t('help.alertsFeature.memoryAlert')}</li>
              <li>{t('help.alertsFeature.cpuAlert')}</li>
              <li>{t('help.alertsFeature.tempAlert')}</li>
            </ul>
          </div>

          {/* 测试报告 */}
          <h3 style={{ color: "var(--text-primary)", marginBottom: '12px', marginTop: '20px', fontSize: '16px' }}>
            {t('help.tabs.reports')}
          </h3>
          <div style={{ color: "var(--text-secondary)", lineHeight: '1.8' }}>
            <p>{t('help.reports.description')}</p>
            <ul>
              <li>{t('help.reports.features.charts')}</li>
              <li>{t('help.reports.features.statistics')}</li>
              <li>{t('help.reports.features.export')}</li>
              <li>{t('help.reports.features.comparison')}</li>
            </ul>
          </div>

          {/* 关于信息（底部） */}
          <div style={{
            marginTop: '24px',
            paddingTop: '16px',
            borderTop: '1px solid var(--border-strong)',
            color: "var(--text-secondary)",
            fontSize: '13px',
            lineHeight: '1.8',
          }}>
            <p style={{ color: "var(--accent)", fontWeight: 'bold', fontSize: '15px' }}>
              {t('help.about.projectName')} <span style={{ color: "var(--text-secondary)" }}>v{t('help.about.versionValue')}</span>
            </p>
            <p>{t('help.about.description')}</p>
            <p>{t('help.about.author')}：{t('help.about.authorValue')}　·　{t('help.about.license')}：{t('help.about.licenseValue')}</p>
            <p style={{ fontSize: '12px' }}>Frontend: React + TypeScript + Vite + ECharts　·　Backend: Python + FastAPI + WebSocket　·　Database: SQLite</p>
          </div>
        </div>
      </div>
    </div>
  );
}
