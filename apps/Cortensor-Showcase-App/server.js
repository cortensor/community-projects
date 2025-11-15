// Simple Express server to handle image uploads to database/images
const express = require('express');
const multer = require('multer');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const bodyParser = require('body-parser');

const app = express();
const ENV_PORT = process.env.PORT;
let PORT = Number(ENV_PORT) || 3000;

app.use(cors());
app.use(bodyParser.json({ limit: '2mb' }));

// Basic security headers (lightweight alternative to helmet to avoid extra deps)
app.use((req,res,next) => {
  res.setHeader('X-Content-Type-Options','nosniff');
  res.setHeader('X-Frame-Options','DENY');
  res.setHeader('Referrer-Policy','strict-origin-when-cross-origin');
  res.setHeader('Permissions-Policy','camera=(), microphone=(), geolocation=()');
  // Very relaxed CSP (adjust if you harden later)
  res.setHeader('Content-Security-Policy', "default-src 'self' data: blob: https:; script-src 'self' 'unsafe-inline' https:; style-src 'self' 'unsafe-inline' https:; img-src 'self' data: blob: https:; connect-src 'self' https:; font-src 'self' https: data:; object-src 'none'; frame-ancestors 'none';");
  next();
});

// Simple in-memory rate limiter & brute force shield
const RATE_LIMIT_WINDOW_MS = 60_000; // 1 minute
const RATE_LIMIT_UPLOAD = 30;        // (disabled) max upload attempts/min per IP
const RATE_LIMIT_PUBLISH = 20;       // (disabled) max publish attempts/min per IP
const ENABLE_RATE_LIMIT = false;     // toggle off to remove limits
const rateBuckets = Object.create(null); // key -> { count, reset }

function rateCheck(key, limit){
  const now = Date.now();
  let bucket = rateBuckets[key];
  if (!bucket || now > bucket.reset){
    bucket = rateBuckets[key] = { count:0, reset: now + RATE_LIMIT_WINDOW_MS };
  }
  bucket.count++;
  return bucket.count <= limit;
}

// Brute-force protection for PIN (per IP)
const failedPins = Object.create(null); // ip -> { fails, blockedUntil }
const MAX_PIN_FAILS = 5;
const BLOCK_TIME_MS = 10 * 60_000; // 10 minutes

function checkBlocked(ip){
  const rec = failedPins[ip];
  if (!rec) return false;
  if (rec.blockedUntil && Date.now() < rec.blockedUntil) return true;
  if (rec.blockedUntil && Date.now() >= rec.blockedUntil){ delete failedPins[ip]; }
  return false;
}
function recordFail(ip){
  const rec = failedPins[ip] || (failedPins[ip] = { fails:0, blockedUntil:0 });
  rec.fails++;
  if (rec.fails >= MAX_PIN_FAILS){ rec.blockedUntil = Date.now() + BLOCK_TIME_MS; }
}
function recordSuccess(ip){ if (failedPins[ip]) delete failedPins[ip]; }

app.set('trust proxy', true); // allow req.ip behind reverse proxy

// No-cache for config files
app.get('/env.local.json', (req, res, next) => {
  res.set('Cache-Control', 'no-cache, no-store, must-revalidate');
  res.set('Pragma', 'no-cache');
  res.set('Expires', '0');
  next();
});

// Ensure upload dir exists
const imagesDir = path.join(__dirname, 'database', 'images');
fs.mkdirSync(imagesDir, { recursive: true });

// Load optional config for simple auth
let ADMIN_PIN = '';
try {
  const cfgPath = path.join(__dirname, 'env.local.json');
  if (fs.existsSync(cfgPath)) {
    const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
    if (cfg && cfg.ADMIN_PIN) ADMIN_PIN = String(cfg.ADMIN_PIN);
  }
} catch {}

// Multer storage
const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, imagesDir),
  filename: (_req, file, cb) => {
    const safe = file.originalname.replace(/[^a-zA-Z0-9._-]+/g, '_');
    cb(null, Date.now() + '_' + safe);
  },
});
const upload = multer({
  storage,
  limits: { fileSize: 3 * 1024 * 1024 }, // 3MB cap
  fileFilter: (_req, file, cb) => {
    if (!/^image\//.test(file.mimetype)) return cb(new Error('Only image uploads allowed'));
    cb(null, true);
  }
});

// Health check
app.get('/health', (_req, res) => res.json({ ok: true }));

// Upload endpoint
app.post('/api/upload', (req,res,next)=>{
  const ip = req.ip;
  if (ENABLE_RATE_LIMIT){
    if (!rateCheck(ip+':upload', RATE_LIMIT_UPLOAD)) return res.status(429).json({ ok:false, error:'Rate limit exceeded' });
    if (checkBlocked(ip)) return res.status(403).json({ ok:false, error:'Temporarily blocked' });
  }
  next();
}, upload.single('file'), (req, res) => {
  try{
    if (ADMIN_PIN) {
      const pin = req.header('x-admin-pin') || req.query.pin || '';
      if (String(pin) !== String(ADMIN_PIN)) {
        recordFail(req.ip);
        return res.status(401).json({ ok: false, error: 'Unauthorized' });
      }
    }
    recordSuccess(req.ip);
    if (!req.file) return res.status(400).json({ ok: false, error: 'No file' });
    const relPath = path.join('database', 'images', path.basename(req.file.filename));
    const url = '/' + relPath.replace(/\\/g, '/');
    return res.json({ ok: true, filename: req.file.filename, path: relPath, url });
  }catch(err){
    console.error('Upload error', err);
    return res.status(500).json({ ok: false, error: 'Upload failed' });
  }
});

// Publish endpoint: writes posted JSON (items, tags, updatedAt) to assets/data.json
app.post('/api/publish', (req,res,next)=>{
  const ip = req.ip;
  if (ENABLE_RATE_LIMIT){
    if (!rateCheck(ip+':publish', RATE_LIMIT_PUBLISH)) return res.status(429).json({ ok:false, error:'Rate limit exceeded' });
    if (checkBlocked(ip)) return res.status(403).json({ ok:false, error:'Temporarily blocked' });
  }
  next();
}, (req, res) => {
  try {
    if (ADMIN_PIN) {
      const pin = req.header('x-admin-pin') || req.query.pin || '';
      if (String(pin) !== String(ADMIN_PIN)) {
        recordFail(req.ip);
        return res.status(401).json({ ok: false, error: 'Unauthorized' });
      }
    }
    recordSuccess(req.ip);
    const payload = req.body || {};
    if (!payload.items || !Array.isArray(payload.items)) {
      return res.status(400).json({ ok: false, error: 'Invalid payload: items[] required' });
    }
    const out = {
      updatedAt: new Date().toISOString().slice(0,10),
      tags: Array.isArray(payload.tags) ? payload.tags : [],
      items: payload.items,
    };
    const dataPath = path.join(__dirname, 'assets', 'data.json');
    fs.writeFileSync(dataPath, JSON.stringify(out, null, 2));
    return res.json({ ok: true, path: 'assets/data.json', items: out.items.length });
  } catch (err) {
    console.error('Publish error', err);
    return res.status(500).json({ ok: false, error: 'Publish failed' });
  }
});

// Simple proxy to handle CORS for Cortensor API
app.use('/proxy', async (req, res) => {
  if (req.method === 'OPTIONS') {
    // Handle preflight
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept');
    res.header('Access-Control-Max-Age', '86400');
    return res.status(200).end();
  }

  // For actual requests, proxy to external API
  const targetUrl = 'http://69.164.253.134:5010' + req.url.replace('/proxy', '');
  console.log(`[proxy] ${req.method} ${targetUrl}`);
  
  try {
    const axios = require('axios');
    const config = {
      method: req.method.toLowerCase(),
      url: targetUrl,
      headers: {
        ...req.headers,
        'host': '69.164.253.134:5010'
      },
      data: req.body,
      validateStatus: () => true // Don't throw on HTTP errors
    };
    
    delete config.headers['host']; // Remove original host
    
    const response = await axios(config);
    
    // Forward response
    res.status(response.status);
    Object.keys(response.headers).forEach(key => {
      if (key.toLowerCase() !== 'access-control-allow-origin') {
        res.set(key, response.headers[key]);
      }
    });
    
    res.send(response.data);
    
  } catch (error) {
    console.error('[proxy] Error:', error.message);
    res.status(500).json({ error: 'Proxy failed', details: error.message });
  }
});

// Warn if weak admin pin
if (ADMIN_PIN && ADMIN_PIN.length < 4){
  console.warn('[security] ADMIN_PIN length < 4; consider using a stronger PIN.');
}

// Static hosting for the app (dev convenience)
app.use(express.static(__dirname));

function startServer(port, tries = 0){
  const server = app.listen(port, () => {
    console.log(`[server] listening on http://localhost:${port}`);
  });
  server.on('error', (err) => {
    if (err && err.code === 'EADDRINUSE'){
      // Only auto-bump when PORT not explicitly provided
      if (!ENV_PORT && tries < 10){
        const next = port + 1;
        console.warn(`[server] port ${port} in use, trying ${next}...`);
        startServer(next, tries + 1);
      } else {
        console.error(`[server] failed to bind on port ${port}. Set PORT to a free port.`);
        process.exit(1);
      }
    } else {
      console.error('[server] error:', err);
      process.exit(1);
    }
  });
}

startServer(PORT);
