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
          backgroundColor: currentLanguage === 'zh-CN' ? '#0062ff' : 'transparent',
          color: currentLanguage === 'zh-CN' ? '#ffffff' : '#888888',
          border: currentLanguage === 'zh-CN' ? '1px solid #0062ff' : '1px solid #333333',
          borderRadius: '4px',
          cursor: 'pointer',
          transition: 'all 0.2s',
        }}
        onMouseEnter={(e) => {
          if (currentLanguage !== 'zh-CN') {
            e.currentTarget.style.backgroundColor = '#333333';
            e.currentTarget.style.color = '#e0e6ed';
          }
        }}
        onMouseLeave={(e) => {
          if (currentLanguage !== 'zh-CN') {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = '#888888';
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
          backgroundColor: currentLanguage === 'en-US' ? '#0062ff' : 'transparent',
          color: currentLanguage === 'en-US' ? '#ffffff' : '#888888',
          border: currentLanguage === 'en-US' ? '1px solid #0062ff' : '1px solid #333333',
          borderRadius: '4px',
          cursor: 'pointer',
          transition: 'all 0.2s',
        }}
        onMouseEnter={(e) => {
          if (currentLanguage !== 'en-US') {
            e.currentTarget.style.backgroundColor = '#333333';
            e.currentTarget.style.color = '#e0e6ed';
          }
        }}
        onMouseLeave={(e) => {
          if (currentLanguage !== 'en-US') {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = '#888888';
          }
        }}
      >
        EN
      </button>
    </div>
  );
}
