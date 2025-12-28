/**
 * ThemeToggle - Dark/Light mode toggle switch
 */

import { useState, useEffect } from 'react';

export const ThemeToggle = () => {
    const [isDark, setIsDark] = useState(() => {
        // Check localStorage or system preference
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('theme');
            if (saved) return saved === 'dark';
            return window.matchMedia('(prefers-color-scheme: dark)').matches;
        }
        return true;
    });

    useEffect(() => {
        const root = document.documentElement;
        if (isDark) {
            root.classList.add('dark');
            localStorage.setItem('theme', 'dark');
        } else {
            root.classList.remove('dark');
            localStorage.setItem('theme', 'light');
        }
    }, [isDark]);

    return (
        <button
            onClick={() => setIsDark(!isDark)}
            className="relative w-14 h-7 rounded-full transition-colors duration-300"
            style={{ background: 'var(--color-border)' }}
            aria-label="Toggle theme"
        >
            {/* Track */}
            <div className="absolute inset-0.5 rounded-full overflow-hidden">
                {/* Icons */}
                <div className="absolute inset-0 flex items-center justify-between px-1.5">
                    <span className={`text-xs transition-opacity ${isDark ? 'opacity-100' : 'opacity-30'}`}>🌙</span>
                    <span className={`text-xs transition-opacity ${!isDark ? 'opacity-100' : 'opacity-30'}`}>☀️</span>
                </div>
            </div>

            {/* Thumb */}
            <div
                className="absolute top-0.5 w-6 h-6 rounded-full transition-all duration-300"
                style={{
                    background: 'var(--color-bg-secondary)',
                    boxShadow: 'var(--shadow-sm)',
                    left: isDark ? '2px' : 'calc(100% - 26px)',
                }}
            />
        </button>
    );
};

export default ThemeToggle;
