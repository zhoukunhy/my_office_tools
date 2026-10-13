/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{vue,ts,tsx,js,jsx}'],
  theme: {
    extend: {
      colors: {
        // 主题主色 - 围绕 #4f6eff 的蓝靛色阶
        primary: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c4d0ff',
          300: '#9bb2ff',
          400: '#7a96ff',
          500: '#4f6eff',
          600: '#3f5ce6',
          700: '#3449b8',
          800: '#2a3c91',
          900: '#1f2a6b',
          DEFAULT: 'var(--c-primary)'
        },
        // 语义色 - 通过 CSS 变量映射，支持深色模式切换
        bg: 'var(--c-bg)',
        'bg-soft': 'var(--c-bg-soft)',
        surface: 'var(--c-surface)',
        'surface-soft': 'var(--c-surface-soft)',
        border: 'var(--c-border)',
        'border-soft': 'var(--c-border-soft)',
        text: 'var(--c-text)',
        'text-soft': 'var(--c-text-soft)',
        'text-mute': 'var(--c-text-mute)'
      },
      fontFamily: {
        sans: [
          'var(--font-sans)',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'PingFang SC',
          'Microsoft YaHei',
          'sans-serif'
        ],
        mono: ['var(--font-mono)', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace']
      },
      borderRadius: {
        DEFAULT: 'var(--r-md)',
        sm: 'var(--r-sm)',
        md: 'var(--r-md)',
        lg: 'var(--r-lg)',
        xl: 'var(--r-xl)',
        '2xl': 'var(--r-2xl)'
      },
      boxShadow: {
        xs: 'var(--sh-xs)',
        sm: 'var(--sh-sm)',
        md: 'var(--sh-md)',
        lg: 'var(--sh-lg)'
      },
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem'
      },
      transitionTimingFunction: {
        out: 'cubic-bezier(0.22, 1, 0.36, 1)'
      }
    }
  },
  plugins: []
}
