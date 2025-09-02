"use client";
import { createContext, useContext, ReactNode } from 'react';
import { Container } from 'inversify';
import { container } from '@/services/container';

const ServiceContext = createContext<Container | null>(null);

export function ServiceProvider({ children }: { children: ReactNode }) {
  return (
    <ServiceContext.Provider value={container}>
      {children}
    </ServiceContext.Provider>
  );
}

export function useService<T>(serviceIdentifier: symbol): T {
  const serviceContainer = useContext(ServiceContext);
  if (!serviceContainer) {
    throw new Error('useService must be used within ServiceProvider');
  }
  return serviceContainer.get<T>(serviceIdentifier);
}