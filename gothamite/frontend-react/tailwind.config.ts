import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        base: 'var(--bg-base)',
        surface: {
          DEFAULT: 'var(--bg-surface)',
          raised: 'var(--bg-surface-raised)',
        },
        border: {
          DEFAULT: 'var(--border)',
          subtle: 'var(--border-subtle)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          tertiary: 'var(--text-tertiary)',
        },
        accent: {
          primary: 'var(--accent-primary)',
          cyan: 'var(--accent-cyan)',
        },
        score: {
          weak: 'var(--score-weak)',
          moderate: 'var(--score-moderate)',
          strong: 'var(--score-strong)',
          veryStrong: 'var(--score-very-strong)',
        },
        evidence: {
          supporting: 'var(--evidence-supporting)',
          contradicting: 'var(--evidence-contradicting)',
        },
        status: {
          proposed: 'var(--status-proposed)',
          confirmed: 'var(--status-confirmed)',
          rejected: 'var(--status-rejected)',
        },
        source: {
          alpha: '#3498db',
          beta: '#e67e22',
          gamma: '#2ecc71',
        },
      },
      fontFamily: {
        display: ['var(--font-display)'],
        body: ['var(--font-body)'],
        mono: ['var(--font-mono)'],
      },
    },
  },
  plugins: [],
} satisfies Config;
