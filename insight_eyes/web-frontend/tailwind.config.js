/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 霓虹主题色
        neon: {
          cpu: '#00f2ff',
          memory: '#7000ff',
          fps: '#ffb400',
          networkUp: '#00ff87',
          networkDown: '#0062ff',
        },
        dark: {
          bg: '#0a0a0a',
          card: '#141414',
        }
      },
      fontFamily: {
        sans: ['"Microsoft YaHei UI"', 'Segoe UI', 'Arial', 'sans-serif'],
        mono: ['Consolas', 'Monaco', 'monospace'],
      },
    },
  },
  plugins: [],
}
