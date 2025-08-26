// src/lib/debug-environment.ts
// This file is kept for development purposes only
// Remove or disable in production

export function debugEnvironmentConfig() {
  if (process.env.NODE_ENV !== 'development') return;
  
  console.group('🔧 Environment Configuration');
  console.log('Debug mode enabled in development only');
  console.groupEnd();
}

export function debugCurrentEnvironment() {
  if (process.env.NODE_ENV !== 'development') return;
  
  console.group('🎯 Current Environment Status');
  console.log('Development mode active');
  console.groupEnd();
}
