// CreateModal.jsx

import React, { useRef, useState, useEffect } from "react";
import { X, SquareCode, WandSparkles, Sparkles } from "lucide-react";
import 'simplebar-react/dist/simplebar.min.css';

function AiGenerateMenu() {
    const [isOpen, setIsOpen] = useState(false);
    const menuRef = useRef(null);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    return (
        <div className="relative" ref={menuRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                // MODIFICAÇÃO: Trocamos 'hover:bg-white/10' por uma cor sólida 'hover:bg-[#4A4C50]'
                className="flex items-center gap-1.5 text-xs text-white border border-[#6C6C6C] bg-[#37393D] rounded-full px-3 py-1 hover:bg-[#4A4C50] transition-colors cursor-pointer"
            >
                <WandSparkles size={12} />
                AI Generate
            </button>
            {isOpen && (
                <div className="absolute top-full right-0 mt-2 w-48 bg-[#2F2F32] rounded-lg drop-shadow-lg z-20 p-1">
                    <button
                        onClick={() => {
                            console.log("New Prompt clicked!");
                            setIsOpen(false);
                        }}
                        className="w-full text-left flex justify-between items-center text-xs px-3 py-2 text-[#FAFAFA] rounded-md hover:bg-[#3A3C40] cursor-pointer"
                    >
                        New Prompt <WandSparkles size={14} />
                    </button>
                    <button
                        onClick={() => {
                            console.log("Enhance Text clicked!");
                            setIsOpen(false);
                        }}
                        className="w-full text-left flex justify-between items-center text-xs px-3 py-2 text-[#FAFAFA] rounded-md hover:bg-[#3A3C40] cursor-pointer"
                    >
                        Enhance Text <Sparkles size={14} />
                    </button>
                </div>
            )}
        </div>
    );
}

function CreateModal({
    isOpen,
    onClose,
    onSave,
    config,
}) {
    const {
        initialText = "",
        readOnly = false,
        title = "Edit Content",
        subtitle,
        Icon = SquareCode,
        actionButtonText = "Save",
        showActionButton = true,
        maxLength = null,
        showAiHelper = false,
    } = config || {};

    const modalRef = useRef(null);
    const [currentText, setCurrentText] = useState(initialText);

    useEffect(() => {
        setCurrentText(initialText ?? "");
    }, [initialText]);

    useEffect(() => {
        const handleKeyDown = (event) => {
            if (event.key === 'Escape') {
                handleAttemptClose();
            }
        };
        if (isOpen) {
            document.addEventListener('keydown', handleKeyDown);
        }
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [isOpen, currentText, readOnly, initialText]);

    if (!isOpen) return null;

    const handleAttemptClose = () => {
        if (!readOnly && initialText !== currentText) {
            if (window.confirm("You have unsaved changes. Are you sure you want to close?")) {
                onClose();
            }
        } else {
            onClose();
        }
    };

    function handleClickOutside(e) {
        if (modalRef.current && !modalRef.current.contains(e.target)) {
            handleAttemptClose();
        }
    }

    function handleSave() {
        const textToSave = maxLength ? currentText.slice(0, maxLength) : currentText;
        onSave(textToSave);
        onClose();
    }

    const handleTextChange = (e) => {
        if (maxLength !== null && e.target.value.length > maxLength) {
            setCurrentText(e.target.value.slice(0, maxLength));
        } else {
            setCurrentText(e.target.value);
        }
    };

    const isAiHelperVisible = showAiHelper && !readOnly;

    return (
        <div
            className="bg-black/50 w-screen h-screen fixed z-50 top-0 left-0 backdrop-blur-sm flex items-center justify-center p-4"
            onClick={handleClickOutside}
        >
            <div
                ref={modalRef}
                className="w-full max-w-4xl max-h-[90vh] bg-[#26272B] rounded-3xl border border-[#6C6C6C] p-8 flex flex-col font-inter"
            >
                <div className="flex justify-between items-start">
                    <div className="flex gap-2 items-start">
                        <Icon size={20} className="text-white" />
                        <div className="flex flex-col gap-1">
                            <h2 className="text-sm font-semibold text-white select-none">{title}</h2>
                            {subtitle && <p className="text-sm text-[#AEAEAE]">{subtitle}</p>}
                        </div>
                    </div>
                    <button onClick={handleAttemptClose} className="cursor-pointer flex-shrink-0 ml-4">
                        <X size={22} color="#939393" />
                    </button>
                </div>

                <div
                    className="relative mt-6 w-full bg-[#37393D] border border-[#505050] rounded-2xl flex flex-col min-h-0 overflow-hidden"
                    style={{
                        height: 'clamp(300px, 50vh, 600px)',
                    }}
                >
                    {isAiHelperVisible && (
                        <div className="absolute top-2 right-2.5 z-10">
                            <AiGenerateMenu />
                        </div>
                    )}
                    <div className="flex-grow min-h-0">
                        <textarea
                            value={currentText}
                            onChange={handleTextChange}
                            readOnly={readOnly}
                            placeholder={readOnly ? "No response available." : "Enter your prompt here..."}
                            className={`create-modal-textarea w-full h-full bg-transparent text-white text-sm outline-none resize-none px-5 pb-5 box-border ${readOnly ? 'cursor-default' : ''} ${isAiHelperVisible ? 'pt-9' : 'pt-5'}`}
                            style={{
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                                lineHeight: 1.5,
                            }}
                        />
                    </div>

                    <div className="mt-auto flex-shrink-0">
                        <hr className="border-t border-[#505050]" />
                        <div className="flex justify-between items-center px-5 py-3">
                            {(maxLength !== null || readOnly) ? (
                                <span className="text-xs text-[#AEAEAE] select-none">
                                    {`Caracteres: ${currentText.length}${maxLength && !readOnly ? `/${maxLength}` : ''}`}
                                </span>
                            ) : (
                                <span></span>
                            )}
                        </div>
                    </div>
                </div>

                {showActionButton && (
                    <div className="flex justify-end mt-6 flex-shrink-0">
                        <button
                            onClick={handleSave}
                            className="bg-[#FAFAFA] text-[#26272B] font-medium py-2 px-6 rounded-full hover:bg-[#E4E4E5] text-sm cursor-pointer select-none transition duration-200 active:scale-95"
                        >
                            {actionButtonText}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

export default CreateModal;