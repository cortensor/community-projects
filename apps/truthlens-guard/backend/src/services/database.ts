import fs from 'fs';
import path from 'path';
import { logger } from '../utils/logger';

interface User {
  id: string;
  email: string;
  [key: string]: unknown;
}

interface FactCheck {
  userId: string;
  credibilityScore?: number;
  type: 'text' | 'url';
  [key: string]: unknown;
}

interface Analytics {
  totalFactChecks: number;
  totalUsers: number;
  averageCredibilityScore: number;
  factChecksByType: {
    text: number;
    url: number;
  };
  recentActivity: FactCheck[];
}

const DATA_DIR = path.join(process.cwd(), 'data');
const FACT_CHECKS_FILE = path.join(DATA_DIR, 'fact-checks.json');
const USERS_FILE = path.join(DATA_DIR, 'users.json');

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

// Initialize data files if they don't exist
if (!fs.existsSync(FACT_CHECKS_FILE)) {
  fs.writeFileSync(FACT_CHECKS_FILE, JSON.stringify([], null, 2));
}

if (!fs.existsSync(USERS_FILE)) {
  fs.writeFileSync(USERS_FILE, JSON.stringify([], null, 2));
}

export class DatabaseService {
  // Fact Checks
  static getFactChecks(): FactCheck[] {
    try {
      const data = fs.readFileSync(FACT_CHECKS_FILE, 'utf8');
      return JSON.parse(data);
    } catch (error) {
      logger.error('Failed to read fact checks', { error });
      return [];
    }
  }

  static saveFactCheck(factCheck: FactCheck): void {
    try {
      const factChecks = this.getFactChecks();
      factChecks.push(factCheck);
      fs.writeFileSync(FACT_CHECKS_FILE, JSON.stringify(factChecks, null, 2));
    } catch (error) {
      logger.error('Failed to save fact check', { error });
    }
  }

  static getFactChecksByUser(userId: string): FactCheck[] {
    const factChecks = this.getFactChecks();
    return factChecks.filter(fc => fc.userId === userId);
  }

  // Users
  static getUsers(): User[] {
    try {
      const data = fs.readFileSync(USERS_FILE, 'utf8');
      return JSON.parse(data);
    } catch (error) {
      logger.error('Failed to read users', { error });
      return [];
    }
  }

  static saveUser(user: User): void {
    try {
      const users = this.getUsers();
      users.push(user);
      fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 2));
    } catch (error) {
      logger.error('Failed to save user', { error });
    }
  }

  static getUserByEmail(email: string): User | undefined {
    const users = this.getUsers();
    return users.find(u => u.email === email);
  }

  static getUserById(id: string): User | undefined {
    const users = this.getUsers();
    return users.find(u => u.id === id);
  }

  // Analytics
  static getAnalytics(): Analytics {
    const factChecks = this.getFactChecks();
    const users = this.getUsers();

    return {
      totalFactChecks: factChecks.length,
      totalUsers: users.length,
      averageCredibilityScore: factChecks.length > 0
        ? factChecks.reduce((sum, fc) => sum + (fc.credibilityScore || 0), 0) / factChecks.length
        : 0,
      factChecksByType: {
        text: factChecks.filter(fc => fc.type === 'text').length,
        url: factChecks.filter(fc => fc.type === 'url').length
      },
      recentActivity: factChecks.slice(-10).reverse()
    };
  }
}
