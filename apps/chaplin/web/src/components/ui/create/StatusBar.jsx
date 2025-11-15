// src/components/ui/create/StatusBar.jsx

import React from 'react';

function StatusBar({ text, maxLength }) {
    const chars = text.length;

    // Lógica para feedback visual quando o limite de caracteres é atingido
    const isLimitReached = maxLength && chars >= maxLength;

    return (
        <div className="w-full border-t border-[#6C6C6C] mt-4 pt-3 flex items-center justify-start text-xs text-[#A3A3A3]">
            {/* Apenas o contador de caracteres, com a classe condicional para a cor */}
            <span className={isLimitReached ? 'font-semibold text-red-400' : ''}>
                Caracteres: {chars}{maxLength ? `/${maxLength}` : ''}
            </span>
        </div>
    );
}

export default StatusBar;