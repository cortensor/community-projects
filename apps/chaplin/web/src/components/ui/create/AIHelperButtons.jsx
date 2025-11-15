// src/components/ui/create/AIHelperButtons.jsx

import React from 'react';
import { WandSparkles } from 'lucide-react';

// Ícone simples para "New Prompt" para não precisar de uma nova dependência
const NewPromptIcon = () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 3V13M3 8H13" stroke="#9E9EA0" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
);

function AIHelperButtons() {
    return (
        <div className="flex items-center gap-2">
            <button className="flex items-center gap-2.5 text-sm font-medium text-white bg-[#3A3A3A] hover:bg-[#4a4a4a] transition-colors px-3 py-2 rounded-lg">
                <NewPromptIcon />
                New Prompt
            </button>
            <button className="flex items-center gap-2.5 text-sm font-medium text-white bg-[#3A3A3A] hover:bg-[#4a4a4a] transition-colors px-3 py-2 rounded-lg">
                <WandSparkles size={14} color="#D9D3D3" />
                Enhance Text
            </button>
        </div>
    );
}

export default AIHelperButtons;