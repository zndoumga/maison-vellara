import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        gold: { DEFAULT: '#B8924A', light: '#D4AF70', dim: '#9A7A3A' },
        ink: { DEFAULT: '#1C1A17', muted: '#6B6560', faint: '#9A8E7E' },
        paper: { DEFAULT: '#F7F5F0', card: '#FFFFFF', border: '#E8E3D8', hover: '#FAF8F4' },
        nav: '#1C1A17',
      },
      fontFamily: {
        display: ['var(--font-cormorant)', 'Georgia', 'serif'],
        mono: ['var(--font-dm-mono)', 'Menlo', 'monospace'],
      },
      animation: {
        'pulse-dot': 'pulse-dot 2s ease-in-out infinite',
        'slide-in': 'slide-in 0.35s ease-out',
        'fade-up': 'fade-up 0.5s ease-out both',
      },
      keyframes: {
        'pulse-dot': { '0%,100%': { opacity: '1' }, '50%': { opacity: '0.3' } },
        'slide-in': { '0%': { opacity: '0', transform: 'translateY(-6px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        'fade-up': { '0%': { opacity: '0', transform: 'translateY(12px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}
export default config
