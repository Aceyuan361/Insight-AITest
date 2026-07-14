import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import './shared/i18n'  // 初始化 i18n
import './shared/store/themeStore'  // 初始化主题（store 创建时同步应用 data-theme，避免 FOUC）

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
