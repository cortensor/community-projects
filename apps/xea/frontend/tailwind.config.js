/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'xea': {
                    bg: '#0a0a0f',
                    'bg-secondary': '#12121a',
                    card: '#1a1a24',
                    border: '#2a2a3a',
                    accent: '#6366f1',
                    'accent-hover': '#818cf8',
                },
                'verdict': {
                    supported: '#22c55e',
                    disputed: '#ef4444',
                    caution: '#f59e0b',
                }
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
            },
        },
    },
    plugins: [],
}
