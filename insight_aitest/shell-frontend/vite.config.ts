import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 80,
    proxy: {
      // 正则锚定 /api/ 前缀：若用字符串 '/api' 做前缀匹配，会把 /api-runner
      // （API 自动化模块的前端路由）也代理到后端，深链接/刷新直接 404 白屏
      '^/api/': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        secure: false,
        ws: true, // 模块 WebSocket 路径为 /api/modules/<id>/ws/*，需支持 ws 升级
      },
    },
  },
})
