"use client";
import React, { useState, useRef, useEffect } from 'react';
import { MessageCircleIcon, Trash2, Pencil, Lock, MoreVertical } from 'lucide-react';
import { ChatSession } from '@/types';

interface ChatListItemProps {
  session: ChatSession;
  userId: string | null;
  currentChatId: string | null;
  isSidebarOpen: boolean;
  onSelectChat: (chatId: string) => void;
  onDeleteChat: (chatId: string, event: React.MouseEvent<HTMLButtonElement>) => void;
  onRenameChat: (chatId: string, newName: string) => void;
}

const ChatListItem: React.FC<ChatListItemProps> = ({
  session,
  userId,
  currentChatId,
  isSidebarOpen,
  onSelectChat,
  onDeleteChat,
  onRenameChat,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(session.name);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const isOwner = session.owner === userId;

  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);


  const handleRename = () => {
    if (name.trim() && name.trim() !== session.name) {
      onRenameChat(session.id, name.trim());
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleRename();
    else if (e.key === 'Escape') {
      setName(session.name);
      setIsEditing(false);
    }
  };

  const isActive = currentChatId === session.id;

  return (
    <div className={`relative group flex items-center rounded-lg transition-colors duration-150 ${isActive ? 'bg-neutral-surface' : 'hover:bg-neutral-surface-hover'}`}>
      <button
        onClick={() => onSelectChat(session.id)}
        className="flex-grow flex items-center p-2.5 text-sm text-left truncate cursor-pointer"
        title={session.name}
      >
        <div className={`mr-2.5 flex-shrink-0 ${isActive ? 'text-brand-primary' : 'text-neutral-text-tertiary'}`}>
          {isOwner ? <MessageCircleIcon size={18} /> : <Lock size={18} />}
        </div>
        {isSidebarOpen && (
          isEditing ? (
            <input
              ref={inputRef}
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onBlur={handleRename}
              onKeyDown={handleKeyDown}
              className="bg-transparent text-neutral-text-primary outline-none w-full"
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <span className={`truncate flex-1 ${isActive ? 'text-neutral-text-primary font-medium' : 'text-neutral-text-secondary'}`}>{session.name}</span>
          )
        )}
      </button>

      {isSidebarOpen && isOwner && (
        <div ref={menuRef} className="relative mr-1">
          <button
            onClick={() => setIsMenuOpen(prev => !prev)}
            className="p-1.5 rounded-full text-neutral-text-secondary hover:bg-neutral-base cursor-pointer"
            title="More options"
          >
            <MoreVertical size={16} />
          </button>
          {isMenuOpen && (
            <div className="absolute top-full right-0 mt-1 w-40 bg-neutral-surface border border-neutral-border rounded-lg shadow-lg z-10 animate-menu-enter">
              <button
                onClick={() => { setIsEditing(true); setIsMenuOpen(false); }}
                className="w-full text-left flex items-center gap-2.5 p-2.5 text-sm text-neutral-text-primary hover:bg-neutral-surface-hover rounded-t-lg"
              >
                <Pencil size={14} /> Rename
              </button>
              <button
                onClick={(e) => { onDeleteChat(session.id, e); setIsMenuOpen(false); }}
                className="w-full text-left flex items-center gap-2.5 p-2.5 text-sm text-red-500 hover:bg-neutral-surface-hover rounded-b-lg"
              >
                <Trash2 size={14} /> Delete
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ChatListItem;