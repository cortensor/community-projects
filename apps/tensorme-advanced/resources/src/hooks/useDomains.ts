"use client";
import { useState, useEffect } from 'react';
import { DOMAIN_CONFIGS, getDomainConfig, getDefaultDomain, DomainConfig } from '@/lib/domains';

const STORAGE_KEY = 'selected-domain';

export const useDomains = () => {
  const [selectedDomain, setSelectedDomain] = useState<DomainConfig | undefined>(undefined);
  const [domains] = useState<DomainConfig[]>(DOMAIN_CONFIGS);

  useEffect(() => {
    // Load saved domain from localStorage
    const savedDomainId = localStorage.getItem(STORAGE_KEY);
    if (savedDomainId) {
      const domain = getDomainConfig(savedDomainId);
      if (domain) {
        setSelectedDomain(domain);
      } else {
        setSelectedDomain(getDefaultDomain());
      }
    } else {
      setSelectedDomain(getDefaultDomain());
    }
  }, []);

  const selectDomain = (domainId: string) => {
    const domain = getDomainConfig(domainId);
    if (domain) {
      setSelectedDomain(domain);
      localStorage.setItem(STORAGE_KEY, domainId);
    }
  };

  return {
    domains,
    selectedDomain,
    selectDomain,
  };
};