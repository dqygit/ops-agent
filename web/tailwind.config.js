/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['IBM Plex Sans', 'Noto Sans SC', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['Cascadia Code', 'JetBrains Mono', 'SFMono-Regular', 'Consolas', 'monospace'],
      },
      colors: {
        ops: {
          bg: '#081012',
          panel: 'rgba(17, 27, 29, 0.78)',
          strong: 'rgba(20, 31, 34, 0.92)',
          deep: 'rgba(6, 12, 14, 0.82)',
          border: 'rgba(176, 218, 208, 0.16)',
          text: '#dce9e6',
          muted: '#8ea5a0',
          green: '#3fd6a5',
          cyan: '#67d8ff',
          warning: '#f0b35a',
          danger: '#ff6b6b',
        },
      },
      boxShadow: {
        glass: '0 24px 80px rgba(0, 0, 0, 0.34), inset 0 1px 0 rgba(255, 255, 255, 0.06)',
        glow: '0 0 24px rgba(63, 214, 165, 0.18)',
      },
      backgroundImage: {
        'ops-landscape': "radial-gradient(circle at 72% 22%, rgba(63, 214, 165, 0.16), transparent 30%), linear-gradient(rgba(8, 16, 18, 0.74), rgba(8, 16, 18, 0.88)), url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1600' height='900' viewBox='0 0 1600 900'%3E%3Cdefs%3E%3ClinearGradient id='s' x1='0' x2='1' y1='0' y2='1'%3E%3Cstop stop-color='%23233334'/%3E%3Cstop offset='1' stop-color='%23070b0c'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='1600' height='900' fill='url(%23s)'/%3E%3Cpath d='M0 655 C180 540 280 590 440 500 C620 400 740 470 900 350 C1080 220 1210 275 1600 120 L1600 900 L0 900Z' fill='%23162224'/%3E%3Cpath d='M0 710 C220 615 380 660 565 565 C770 460 960 530 1160 410 C1320 315 1440 330 1600 260 L1600 900 L0 900Z' fill='%230e181a'/%3E%3Cpath d='M0 770 C260 690 430 735 660 665 C930 585 1080 630 1600 510 L1600 900 L0 900Z' fill='%23081112'/%3E%3C/svg%3E\")",
      },
    },
  },
  plugins: [],
}
