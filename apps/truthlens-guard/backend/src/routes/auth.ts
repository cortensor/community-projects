import { Router } from 'express';
import { z } from 'zod';
import { logger } from '../utils/logger';
import { DatabaseService } from '../services/database';

const router = Router();

// Validation schemas
const userSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
  name: z.string().min(2)
});

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1)
});

// POST /api/auth/register
router.post('/register', async (req, res) => {
  try {
    const { email, password, name } = userSchema.parse(req.body);

    // Check if user exists
    const existingUser = DatabaseService.getUserByEmail(email);
    if (existingUser) {
      return res.status(400).json({
        success: false,
        error: 'User already exists'
      });
    }

    // Create user (in production, hash password!)
    const user = {
      id: Date.now().toString(),
      email,
      password, // WARNING: Never store plain passwords in production!
      name,
      createdAt: new Date().toISOString()
    };

    DatabaseService.saveUser(user);

    // Return user without password
    const { password: _, ...userWithoutPassword } = user;

    res.json({
      success: true,
      data: {
        user: userWithoutPassword,
        token: 'demo-token-' + user.id // Replace with JWT in production
      }
    });
  } catch (error) {
    logger.error('Registration failed', { error });
    res.status(400).json({
      success: false,
      error: 'Invalid registration data'
    });
  }
});

// POST /api/auth/login
router.post('/login', async (req, res) => {
  try {
    const { email, password } = loginSchema.parse(req.body);

    const user = DatabaseService.getUserByEmail(email);
    if (!user || user.password !== password) {
      return res.status(401).json({
        success: false,
        error: 'Invalid credentials'
      });
    }

    // Return user without password
    const { password: _, ...userWithoutPassword } = user;

    res.json({
      success: true,
      data: {
        user: userWithoutPassword,
        token: 'demo-token-' + user.id
      }
    });
  } catch (error) {
    logger.error('Login failed', { error });
    res.status(400).json({
      success: false,
      error: 'Invalid login data'
    });
  }
});

// GET /api/auth/me
router.get('/me', async (req, res) => {
  // In production, verify JWT token from Authorization header
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) {
    return res.status(401).json({
      success: false,
      error: 'No token provided'
    });
  }

  // Find user by token (simplified for demo)
  const userId = token.replace('demo-token-', '');
  const user = DatabaseService.getUserById(userId);

  if (!user) {
    return res.status(401).json({
      success: false,
      error: 'Invalid token'
    });
  }

  const { password: _, ...userWithoutPassword } = user;
  res.json({
    success: true,
    data: { user: userWithoutPassword }
  });
});

// GET /api/user/fact-checks
router.get('/user/fact-checks', async (req, res) => {
  // In production, get user ID from JWT token
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) {
    return res.status(401).json({
      success: false,
      error: 'No token provided'
    });
  }

  const userId = token.replace('demo-token-', '');
  const userFactChecks = DatabaseService.getFactChecksByUser(userId);

  res.json({
    success: true,
    data: userFactChecks
  });
});

// POST /api/user/fact-checks
router.post('/user/fact-checks', async (req, res) => {
  // In production, get user ID from JWT token
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) {
    return res.status(401).json({
      success: false,
      error: 'No token provided'
    });
  }

  const userId = token.replace('demo-token-', '');
  const factCheck = {
    ...req.body,
    userId,
    id: Date.now().toString(),
    createdAt: new Date().toISOString()
  };

  DatabaseService.saveFactCheck(factCheck);

  res.json({
    success: true,
    data: factCheck
  });
});

export { router as authRouter };
