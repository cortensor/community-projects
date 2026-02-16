import request from 'supertest';
import app from '../index';

describe('Health Endpoint', () => {
  it('should return healthy status', async () => {
    const response = await request(app)
      .get('/api/health')
      .expect(200);

    expect(response.body).toMatchObject({
      success: true,
      message: expect.stringContaining('healthy'),
      version: expect.any(String),
      timestamp: expect.any(String)
    });
  });
});

describe('Analysis Status Endpoint', () => {
  it('should return analysis status', async () => {
    const response = await request(app)
      .get('/api/analysis/status')
      .expect(200);

    expect(response.body).toMatchObject({
      success: true,
      data: {
        cortensorConnected: expect.any(Boolean),
        availableMiners: expect.any(Number),
        lastHealthCheck: expect.any(String)
      }
    });
  });
});
