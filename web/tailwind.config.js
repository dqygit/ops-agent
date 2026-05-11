/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        ops: {
          bg: '#0B0F19',
          panel: '#151B28',
          strong: '#1E293B',
          deep: '#05080f',
          border: 'rgba(51, 65, 85, 0.6)',
          text: '#F1F5F9',
          muted: '#94A3B8',
          green: '#10B981',
          cyan: '#06B6D4',
          warning: '#F59E0B',
          danger: '#EF4444',
        },
      },
      boxShadow: {
        glass: '0 8px 32px 0 rgba(0, 0, 0, 0.37), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
        glow: '0 0 20px rgba(6, 182, 212, 0.4)',
        input: '0 4px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
      },
      backgroundImage: {
        'ops-landscape': "radial-gradient(circle at top, rgba(6, 182, 212, 0.05), transparent 30%), linear-gradient(to bottom, #151B28, #0B0F19)",
      },
    },
  },
  plugins: [],
}
