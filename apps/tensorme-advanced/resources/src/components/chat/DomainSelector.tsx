"use client";
import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Sparkles } from 'lucide-react';
import { DomainConfig } from '@/lib/domains';

interface DomainSelectorProps {
  domains: DomainConfig[];
  selectedDomain: DomainConfig | undefined;
  onSelectDomain: (domainId: string) => void;
}

const DomainSelector: React.FC<DomainSelectorProps> = ({
  domains,
  selectedDomain,
  onSelectDomain,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const currentDomain = selectedDomain || domains[0];

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 backdrop-blur-sm bg-white/5 border border-white/10 rounded-xl text-sm font-medium text-white/80 hover:bg-white/10 hover:text-white"
      >
        <Sparkles size={16} className="text-yellow-400" />
        <span className="hidden md:inline">{currentDomain.icon} {currentDomain.name}</span>
        <span className="md:hidden">{currentDomain.icon}</span>
        <ChevronDown size={14} className={`transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 backdrop-blur-xl bg-black/80 border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50">
          <div className="p-2">
            <div className="text-xs font-semibold text-white/40 px-3 py-2 uppercase tracking-wider">
              Select Domain
            </div>
            {domains.map((domain) => (
              <button
                key={domain.id}
                onClick={() => {
                  onSelectDomain(domain.id);
                  setIsOpen(false);
                }}
                className={`w-full text-left px-3 py-3 rounded-lg hover:bg-white/10 group ${
                  currentDomain.id === domain.id ? 'bg-white/10' : ''
                }`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-2xl">{domain.icon}</span>
                  <div className="flex-1">
                    <div className="font-medium text-white/90 mb-1">
                      {domain.name}
                    </div>
                    <div className="text-xs text-white/50">
                      {domain.description}
                    </div>
                    {currentDomain.id === domain.id && (
                      <div className="mt-2 flex items-center gap-1">
                        <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                        <span className="text-xs text-green-400">Active</span>
                      </div>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
          
          <div className="border-t border-white/10 p-3">
            <div className="text-xs text-white/40">
              Domains provide specialized knowledge and context for better responses
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DomainSelector;