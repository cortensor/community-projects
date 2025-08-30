const config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'brand-primary': 'hsl(45, 100%, 51%)',
        'brand-primary-hover': 'hsl(45, 100%, 56%)',
        'neutral-base': '#101010',
        'neutral-surface': '#1a1a1a',
        'neutral-surface-hover': '#2a2a2a',
        'neutral-border': '#2f2f2f',
        'neutral-text-primary': '#ededed',
        'neutral-text-secondary': '#a0a0a0',
        'neutral-text-tertiary': '#666666',
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
  plugins: [require('@tailwindcss/typography')],
}
export default config