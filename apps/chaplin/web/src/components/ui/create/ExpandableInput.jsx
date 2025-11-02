// src/components/ui/general/ExpandableInput.jsx

import React from "react";
import { Scan } from "lucide-react";

function ExpandableInput({
    value,
    onChange,
    placeholder,
    maxLength,
    onOpenModal,
}) {
    return (
        <div className="relative w-full">
            <input
                type="text"
                value={value}
                onChange={onChange}
                placeholder={placeholder}
                maxLength={maxLength}
                // O padding à direita (pr-12) garante que o texto não passe por baixo do botão
                className="w-full bg-transparent border border-[#3A3A3A] text-white text-sm rounded-xl px-4 py-4 pr-12 outline-none focus:ring-1 focus:ring-[#fafafa]"
            />
            <button
                type="button"
                onClick={onOpenModal}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg hover:bg-[#2C2C30] transition duration-200 active:scale-95 cursor-pointer"
                aria-label="Expand and edit in modal"
            >
                <Scan size={16} color="#A3A3A3" />
            </button>
        </div>
    );
}

export default ExpandableInput;