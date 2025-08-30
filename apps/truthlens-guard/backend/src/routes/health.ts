import { Router } from 'express';

const router = Router();

router.get('/', (req, res) => {
  res.json({
    success: true,
    message: 'TruthLens Backend API is healthy',
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

export { router as healthRouter };
