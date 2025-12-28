/**
 * Environment configuration
 * Loads and validates all environment variables
 */

import dotenv from 'dotenv';

// Load .env file
dotenv.config();

export interface Config {
  // Server
  PORT: number;
  NODE_ENV: 'development' | 'production' | 'test';

  // Blockchain
  BLOCKCHAIN_RPC_URL: string;
  JUSTICE_CONTRACT_ADDRESS: string;
  REPUTATION_REGISTRY_ADDRESS: string;
  COR_TOKEN_ADDRESS: string;
  VALIDATOR_PRIVATE_KEY: string;
  VALIDATOR_ADDRESS: string;
  NETWORK: 'base' | 'arbitrum' | 'localhost';

  // Cortensor API
  CORTENSOR_API_URL: string;
  CORTENSOR_API_KEY: string;

  // Vector DB (Pinecone)
  PINECONE_API_KEY: string;
  PINECONE_ENVIRONMENT: string;
  PINECONE_INDEX_NAME: string;

  // IPFS (Pinata)
  PINATA_API_KEY: string;
  PINATA_API_SECRET: string;
  PINATA_GATEWAY_URL: string;

  // Redis
  REDIS_URL: string;
  REDIS_HOST: string;
  REDIS_PORT: number;

  // Judge Configuration
  CHALLENGE_WINDOW_DURATION: number;      // In seconds
  MIN_SIMILARITY_THRESHOLD: number;        // 0-1
  MIN_BOND_AMOUNT: string;                 // In wei
  MAX_BOND_AMOUNT: string;                 // In wei
  SLASH_PERCENTAGE: number;
  CHALLENGER_REWARD_PERCENTAGE: number;

  // Monitoring
  LOG_LEVEL: 'debug' | 'info' | 'warn' | 'error';
  METRICS_ENABLED: boolean;

  // Security
  CORS_ORIGIN: string;
  API_RATE_LIMIT: number;
}

function getEnvVar(name: string, defaultValue?: string): string {
  const value = process.env[name];
  if (!value) {
    if (defaultValue !== undefined) {
      return defaultValue;
    }
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function getEnvNumber(name: string, defaultValue?: number): number {
  const value = getEnvVar(name, defaultValue?.toString());
  const num = Number(value);
  if (isNaN(num)) {
    throw new Error(`Invalid number for ${name}: ${value}`);
  }
  return num;
}

export function loadConfig(): Config {
  return {
    PORT: getEnvNumber('PORT', 3001),
    NODE_ENV: (getEnvVar('NODE_ENV', 'development') as any),

    BLOCKCHAIN_RPC_URL: getEnvVar('BLOCKCHAIN_RPC_URL'),
    JUSTICE_CONTRACT_ADDRESS: getEnvVar('JUSTICE_CONTRACT_ADDRESS'),
    REPUTATION_REGISTRY_ADDRESS: getEnvVar('REPUTATION_REGISTRY_ADDRESS'),
    COR_TOKEN_ADDRESS: getEnvVar('COR_TOKEN_ADDRESS'),
    VALIDATOR_PRIVATE_KEY: getEnvVar('VALIDATOR_PRIVATE_KEY'),
    VALIDATOR_ADDRESS: getEnvVar('VALIDATOR_ADDRESS'),
    NETWORK: (getEnvVar('NETWORK', 'base') as any),

    CORTENSOR_API_URL: getEnvVar('CORTENSOR_API_URL'),
    CORTENSOR_API_KEY: getEnvVar('CORTENSOR_API_KEY', ''),

    PINECONE_API_KEY: getEnvVar('PINECONE_API_KEY'),
    PINECONE_ENVIRONMENT: getEnvVar('PINECONE_ENVIRONMENT'),
    PINECONE_INDEX_NAME: getEnvVar('PINECONE_INDEX_NAME', 'cortensor-judge'),

    PINATA_API_KEY: getEnvVar('PINATA_API_KEY'),
    PINATA_API_SECRET: getEnvVar('PINATA_API_SECRET'),
    PINATA_GATEWAY_URL: getEnvVar('PINATA_GATEWAY_URL', 'https://gateway.pinata.cloud'),

    REDIS_URL: getEnvVar('REDIS_URL', 'redis://localhost:6379'),
    REDIS_HOST: getEnvVar('REDIS_HOST', 'localhost'),
    REDIS_PORT: getEnvNumber('REDIS_PORT', 6379),

    CHALLENGE_WINDOW_DURATION: getEnvNumber('CHALLENGE_WINDOW_DURATION', 300), // 5 mins
    MIN_SIMILARITY_THRESHOLD: getEnvNumber('MIN_SIMILARITY_THRESHOLD') / 100 || 0.95,
    MIN_BOND_AMOUNT: getEnvVar('MIN_BOND_AMOUNT', '100000000000000000'), // 0.1 COR
    MAX_BOND_AMOUNT: getEnvVar('MAX_BOND_AMOUNT', '10000000000000000000'), // 10 COR
    SLASH_PERCENTAGE: getEnvNumber('SLASH_PERCENTAGE', 20),
    CHALLENGER_REWARD_PERCENTAGE: getEnvNumber('CHALLENGER_REWARD_PERCENTAGE', 50),

    LOG_LEVEL: (getEnvVar('LOG_LEVEL', 'info') as any),
    METRICS_ENABLED: getEnvVar('METRICS_ENABLED', 'true') === 'true',

    CORS_ORIGIN: getEnvVar('CORS_ORIGIN', '*'),
    API_RATE_LIMIT: getEnvNumber('API_RATE_LIMIT', 100),
  };
}

export const config = loadConfig();
