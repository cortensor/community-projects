"use client";
import { ReactNode } from 'react';
import { Provider } from 'react-redux';
import { store } from '@/store';
import { ServiceProvider } from '@/context/ServiceContext';
import { ErrorBoundary } from '@/components/ErrorBoundary';

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary>
      <Provider store={store}>
        <ServiceProvider>
          {children}
        </ServiceProvider>
      </Provider>
    </ErrorBoundary>
  );
}