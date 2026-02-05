import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMonitoringStore } from '@/store/monitoringStore';
import HelpDialog from '@/components/dialogs/HelpDialog';
import LanguageSwitcher from '@/components/widgets/LanguageSwitcher';

export default function MenuBar() {
  const { activeTab, setActiveTab } = useMonitoringStore();
  const [showHelp, setShowHelp] = useState(false);
  const { t } = useTranslation();

  return (
    <nav style={{
      backgroundColor: '#1e1e1e',
      borderBottom: '1px solid #333333',
      height: '36px',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '100%',
        padding: '0 16px',
      }}>
        {/* 左侧区域 */}
        <div style={{ display: 'flex', gap: '8px', flex: 1 }}>
          {/* 实时监控 Tab */}
          <button
            onClick={() => setActiveTab('monitor')}
            style={{
              fontSize: '13px',
              fontWeight: '500',
              color: activeTab === 'monitor' ? '#00d4ff' : '#ffffff',
              textDecoration: 'none',
              fontFamily: '"Microsoft YaHei UI", "Segoe UI", Arial, sans-serif',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '8px 12px',
              borderBottom: activeTab === 'monitor' ? '2px solid #00d4ff' : 'none',
              transition: 'all 0.2s',
            }}
          >
            {t('menu.realtimeMonitor')}
          </button>

          {/* 测试报告 Tab */}
          <button
            onClick={() => setActiveTab('report')}
            style={{
              fontSize: '13px',
              fontWeight: '500',
              color: activeTab === 'report' ? '#00d4ff' : '#ffffff',
              textDecoration: 'none',
              fontFamily: '"Microsoft YaHei UI", "Segoe UI", Arial, sans-serif',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '8px 12px',
              borderBottom: activeTab === 'report' ? '2px solid #00d4ff' : 'none',
              transition: 'all 0.2s',
            }}
          >
            {t('menu.testReport')}
          </button>
        </div>

        {/* 项目名称 - 居中显示 */}
        <div style={{
          fontSize: '15px',
          fontWeight: '600',
          color: '#00d4ff',
          fontFamily: '"Microsoft YaHei UI", "Segoe UI", Arial, sans-serif',
          position: 'absolute',
          left: '50%',
          transform: 'translateX(-50%)',
        }}>
          {t('menu.projectName')}
        </div>

        {/* 右侧区域 */}
        <div style={{ display: 'flex', gap: '12px', flex: 1, justifyContent: 'flex-end', alignItems: 'center' }}>
          {/* 语言切换器 */}
          <LanguageSwitcher />

          {/* 帮助 */}
          <button
            onClick={() => setShowHelp(true)}
            style={{
              fontSize: '13px',
              color: '#ffffff',
              textDecoration: 'none',
              fontFamily: '"Microsoft YaHei UI", "Segoe UI", Arial, sans-serif',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '8px 12px',
            }}
          >
            {t('menu.help')}
          </button>
        </div>
      </div>

      {/* 帮助对话框 */}
      {showHelp && <HelpDialog onClose={() => setShowHelp(false)} />}
    </nav>
  );
}
