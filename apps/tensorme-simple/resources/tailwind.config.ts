import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'brand-primary': 'hsl(48, 95%, 57%)', // A more vibrant yellow
        'brand-primary-hover': 'hsl(48, 100%, 62%)',
        'neutral-base': '#111111',
        'neutral-surface': '#1C1C1C',
        'neutral-surface-hover': '#242424',
        'neutral-border': '#333333',
        'neutral-text-primary': '#F5F5F5',
        'neutral-text-secondary': '#A3A3A3',
        'neutral-text-tertiary': '#6B6B6B',
      },
      keyframes: {
        'fade-in-slide-up': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'menu-enter': {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'menu-leave': {
          '0%': { opacity: '1', transform: 'scale(1)' },
          '100%': { opacity: '0', transform: 'scale(0.95)' },
        }
      },
      animation: {
        'fade-in-slide-up': 'fade-in-slide-up 0.3s ease-out forwards',
        'menu-enter': 'menu-enter 0.1s ease-out forwards',
        'menu-leave': 'menu-leave 0.075s ease-in forwards',
      },
    },
  },
  plugins: [],
}
export default config