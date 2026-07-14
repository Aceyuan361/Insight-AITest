/**
 * 语言切换组件
 * 支持中文和英文切换
 */
import { useTranslation } from 'react-i18next';

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
  };

  const currentLanguage = i18n.language;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
      }}
    >
      <button
        onClick={() => changeLanguage('zh-CN')}
        style={{
          padding: '6px 10px',
          fontSize: '13px',
          backgroundColor: currentLanguage === 'zh-CN' ? "var(--chart-5)" : 'transparent',
          color: currentLanguage === 'zh-CN' ? "var(--text-primary)" : "var(--text-secondary)",
          border: currentLanguage === 'zh-CN' ? '1px solid var(--chart-5)' : '1px solid var(--border-strong)',
          borderRadius: '4px',
          cursor: 'pointer',
          transition: 'all 0.2s',
        }}
        onMouseEnter={(e) => {
          if (currentLanguage !== 'zh-CN') {
            e.currentTarget.style.backgroundColor = 'var(--border-strong)';
            e.currentTarget.style.color = "var(--text-primary)";
          }
        }}
        onMouseLeave={(e) => {
          if (currentLanguage !== 'zh-CN') {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = "var(--text-secondary)";
          }
        }}
      >
        中
      </button>
      <button
        onClick={() => changeLanguage('en-US')}
        style={{
          padding: '6px 10px',
          fontSize: '13px',
          backgroundColor: currentLanguage === 'en-US' ? "var(--chart-5)" : 'transparent',
          color: currentLanguage === 'en-US' ? "var(--text-primary)" : "var(--text-secondary)",
          border: currentLanguage === 'en-US' ? '1px solid var(--chart-5)' : '1px solid var(--border-strong)',
          borderRadius: '4px',
          cursor: 'pointer',
          transition: 'all 0.2s',
        }}
        onMouseEnter={(e) => {
          if (currentLanguage !== 'en-US') {
            e.currentTarget.style.backgroundColor = 'var(--border-strong)';
            e.currentTarget.style.color = "var(--text-primary)";
          }
        }}
        onMouseLeave={(e) => {
          if (currentLanguage !== 'en-US') {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = "var(--text-secondary)";
          }
        }}
      >
        EN
      </button>
    </div>
  );
}
