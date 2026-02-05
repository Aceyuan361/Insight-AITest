/**
 * 帮助对话框组件
 * Web 版专用，移除快捷键标签页避免与浏览器快捷键冲突
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

interface HelpDialogProps {
  onClose: () => void;
}

type HelpTab = 'usage' | 'about';

export default function HelpDialog({ onClose }: HelpDialogProps) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<HelpTab>('usage');

  const renderUsageTab = () => (
    <div style={{ padding: '20px' }}>
      <h2 style={{ color: '#00d4ff', marginBottom: '16px' }}>
        {t('help.about.description')} - {t('help.about.versionValue')}
      </h2>

      <h3 style={{ color: '#e0e6ed', marginBottom: '12px', fontSize: '16px' }}>
        {t('help.tabs.quickStart')}
      </h3>
      <ol style={{ color: '#94a3b8', lineHeight: '1.8' }}>
        <li>{t('help.quickStart.step1Desc')}</li>
        <li>{t('help.quickStart.step2Desc')}</li>
        <li>{t('help.quickStart.step3Desc')}</li>
        <li>{t('help.quickStart.step4Desc')}</li>
        <li>{t('help.quickStart.step5Desc')}</li>
      </ol>

      <h3 style={{ color: '#e0e6ed', marginBottom: '12px', marginTop: '20px', fontSize: '16px' }}>
        {t('help.tabs.metrics')}
      </h3>
      <div style={{ color: '#94a3b8', lineHeight: '1.8' }}>
        <p><b>{t('help.metrics.cpuTitle')}</b>：{t('help.metrics.cpuDesc')}</p>
        <p><b>{t('help.metrics.memoryTitle')}</b>：{t('help.metrics.memoryDesc')}</p>
        <p><b>{t('help.metrics.fpsTitle')}</b>：{t('help.metrics.fpsDesc')}</p>
        <p><b>{t('help.metrics.networkTitle')}</b>：{t('help.metrics.networkDesc')}</p>
        <p><b>{t('help.metrics.gpuTitle')}</b>：{t('help.metrics.gpuDesc')}</p>
        <p style={{ color: '#f59e0b', fontSize: '13px', marginTop: '8px' }}>
          <i>{t('help.metrics.gpuNote')}</i>
        </p>
      </div>

      <h3 style={{ color: '#e0e6ed', marginBottom: '12px', marginTop: '20px', fontSize: '16px' }}>
        {t('help.platformSupport.title')}
      </h3>
      <div style={{ color: '#94a3b8', lineHeight: '1.8' }}>
        <div style={{ marginBottom: '16px' }}>
          <p style={{ color: '#00d4ff', fontWeight: 'bold' }}>{t('help.platformSupport.android.title')}</p>
          <p style={{ marginLeft: '16px' }}>{t('help.platformSupport.android.osVersion')}</p>
          <p style={{ marginLeft: '16px' }}>{t('help.platformSupport.android.features')}</p>
          <p style={{ marginLeft: '16px', color: '#f59e0b' }}>{t('help.platformSupport.android.gpuStatus')}</p>
          <p style={{ marginLeft: '16px', fontSize: '13px' }}><i>{t('help.platformSupport.android.notes')}</i></p>
        </div>
        <div style={{ marginBottom: '16px' }}>
          <p style={{ color: '#00d4ff', fontWeight: 'bold' }}>{t('help.platformSupport.ios.title')}</p>
          <p style={{ marginLeft: '16px' }}>{t('help.platformSupport.ios.osVersion')}</p>
          <p style={{ marginLeft: '16px' }}>{t('help.platformSupport.ios.features')}</p>
          <p style={{ marginLeft: '16px', color: '#ef4444' }}>{t('help.platformSupport.ios.gpuStatus')}</p>
          <p style={{ marginLeft: '16px', fontSize: '13px' }}>
            <i>{t('help.platformSupport.ios.gpuReason')}</i>
          </p>
          <p style={{ marginLeft: '24px', fontSize: '12px' }}>{t('help.platformSupport.ios.gpuReason1')}</p>
          <p style={{ marginLeft: '24px', fontSize: '12px' }}>{t('help.platformSupport.ios.gpuReason2')}</p>
          <p style={{ marginLeft: '16px', fontSize: '13px' }}><i>{t('help.platformSupport.ios.notes')}</i></p>
        </div>
      </div>

      <h3 style={{ color: '#e0e6ed', marginBottom: '12px', marginTop: '20px', fontSize: '16px' }}>
        {t('help.tabs.alerts')}
      </h3>
      <div style={{ color: '#94a3b8', lineHeight: '1.8' }}>
        <p>{t('help.alertsFeature.description')}</p>
        <ul>
          <li>{t('help.alertsFeature.fpsAlert')}</li>
          <li>{t('help.alertsFeature.memoryAlert')}</li>
          <li>{t('help.alertsFeature.cpuAlert')}</li>
          <li>{t('help.alertsFeature.tempAlert')}</li>
        </ul>
      </div>

      <h3 style={{ color: '#e0e6ed', marginBottom: '12px', marginTop: '20px', fontSize: '16px' }}>
        {t('help.tabs.reports')}
      </h3>
      <div style={{ color: '#94a3b8', lineHeight: '1.8' }}>
        <p>{t('help.reports.description')}</p>
        <ul>
          <li>{t('help.reports.features.charts')}</li>
          <li>{t('help.reports.features.statistics')}</li>
          <li>{t('help.reports.features.export')}</li>
          <li>{t('help.reports.features.comparison')}</li>
        </ul>
      </div>
    </div>
  );

  const renderAboutTab = () => (
    <div style={{ padding: '20px' }}>
      <h2 style={{ color: '#00d4ff', marginBottom: '16px' }}>
        {t('help.tabs.about')} {t('help.about.projectName')}
      </h2>
      <div style={{ color: '#94a3b8', lineHeight: '1.8' }}>
        <p style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '8px' }}>
          {t('help.about.projectName')} {t('help.about.versionValue')}
        </p>
        <p><b>{t('help.about.description')}</b></p>
        <p>{t('help.about.author')}：<b>{t('help.about.authorValue')}</b></p>
        <p style={{ marginTop: '16px' }}>{t('help.about.featuresList')}</p>

        <h3 style={{ color: '#e0e6ed', marginBottom: '12px', marginTop: '20px', fontSize: '16px' }}>
          {t('help.about.features')}
        </h3>
        <div style={{ marginLeft: '16px', marginBottom: '16px' }}>
          <p style={{ color: '#00d4ff', fontWeight: 'bold' }}>{t('help.about.androidSection')}</p>
          <p>{t('help.about.androidVersion')}</p>
          <p>{t('help.about.androidFeatures')}</p>
          <p style={{ color: '#f59e0b' }}>{t('help.about.androidGpu')}</p>
        </div>
        <div style={{ marginLeft: '16px', marginBottom: '16px' }}>
          <p style={{ color: '#00d4ff', fontWeight: 'bold' }}>{t('help.about.iosSection')}</p>
          <p>{t('help.about.iosVersion')}</p>
          <p>{t('help.about.iosFeatures')}</p>
          <p style={{ color: '#ef4444' }}>{t('help.about.iosGpu')}</p>
          <p style={{ fontSize: '13px' }}><i>{t('help.about.iosGpuReason')}</i></p>
        </div>

        <h3 style={{ color: '#e0e6ed', marginBottom: '12px', marginTop: '20px', fontSize: '16px' }}>
          {t('help.about.architecture')}
        </h3>
        <p><b>Frontend</b>: React + TypeScript + Vite + ECharts</p>
        <p><b>Backend</b>: Python + FastAPI + WebSocket</p>
        <p><b>Database</b>: SQLite</p>
        <p style={{ marginTop: '16px' }}>{t('help.about.license')}: {t('help.about.licenseValue')}</p>
      </div>
    </div>
  );

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
          backgroundColor: '#1e1e1e',
          borderRadius: '12px',
          maxWidth: '700px',
          width: '90%',
          maxHeight: '80vh',
          border: '1px solid #333333',
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
          borderBottom: '1px solid #333333',
        }}>
          <h2 style={{ color: '#00d4ff', margin: 0, fontSize: '16px' }}>{t('help.title')}</h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              fontSize: '24px',
              cursor: 'pointer',
              padding: 0,
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>

        {/* Tab 切换按钮 */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid #333333',
        }}>
          <button
            onClick={() => setActiveTab('usage')}
            style={{
              flex: 1,
              padding: '12px',
              background: 'none',
              border: 'none',
              color: activeTab === 'usage' ? '#00d4ff' : '#94a3b8',
              borderBottom: activeTab === 'usage' ? '2px solid #00d4ff' : 'none',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            {t('help.tabs.quickStart')}
          </button>
          <button
            onClick={() => setActiveTab('about')}
            style={{
              flex: 1,
              padding: '12px',
              background: 'none',
              border: 'none',
              color: activeTab === 'about' ? '#00d4ff' : '#94a3b8',
              borderBottom: activeTab === 'about' ? '2px solid #00d4ff' : 'none',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            {t('help.tabs.about')}
          </button>
        </div>

        {/* 内容区域 */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {activeTab === 'usage' && renderUsageTab()}
          {activeTab === 'about' && renderAboutTab()}
        </div>
      </div>
    </div>
  );
}
