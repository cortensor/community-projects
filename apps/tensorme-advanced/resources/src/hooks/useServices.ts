import { useCallback } from 'react';
import { useService } from '@/context/ServiceContext';
import { TYPES } from '@/services/container/types';
import { ILogger, IEventBus, IHttpClient } from '@/services/interfaces';

// Logger hook
export function useLogger() {
  const logger = useService<ILogger>(TYPES.Logger);
  
  return {
    debug: useCallback((message: string, context?: any) => {
      logger.debug(message, context);
    }, [logger]),
    
    info: useCallback((message: string, context?: any) => {
      logger.info(message, context);
    }, [logger]),
    
    warn: useCallback((message: string, context?: any) => {
      logger.warn(message, context);
    }, [logger]),
    
    error: useCallback((message: string, error?: Error, context?: any) => {
      logger.error(message, error, context);
    }, [logger]),
  };
}

// Event bus hook
export function useEventBus() {
  const eventBus = useService<IEventBus>(TYPES.EventBus);
  
  return {
    emit: useCallback((event: string, data?: any) => {
      eventBus.emit(event, data);
    }, [eventBus]),
    
    on: useCallback((event: string, callback: (data?: any) => void) => {
      return eventBus.on(event, callback);
    }, [eventBus]),
    
    once: useCallback((event: string, callback: (data?: any) => void) => {
      return eventBus.once(event, callback);
    }, [eventBus]),
  };
}

// HTTP client hook
export function useHttpClient() {
  const httpClient = useService<IHttpClient>(TYPES.HttpClient);
  
  return {
    get: useCallback(async <T = any>(url: string, config?: RequestInit) => {
      return httpClient.get<T>(url, config);
    }, [httpClient]),
    post: useCallback(async <T = any>(url: string, data?: any, config?: RequestInit) => {
      return httpClient.post<T>(url, data, config);
    }, [httpClient]),
    
    put: useCallback(async <T = any>(url: string, data?: any, config?: RequestInit) => {
      return httpClient.put<T>(url, data, config);
    }, [httpClient]),
    del: useCallback(async <T = any>(url: string, config?: RequestInit) => {
      return httpClient.del<T>(url, config);
    }, [httpClient]),
  };
}