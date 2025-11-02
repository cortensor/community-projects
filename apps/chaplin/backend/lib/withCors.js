// lib/withCors.js — versão para Node runtime (Express-like)
const allowedOrigins = [
  'http://localhost:5173',
  'https://chaplin-xlb1.onrender.com',
  'https://chaplin.lumitylabs.com',
  'https://web3museum.lumitylabs.com',
  'https://web3museum.onrender.com'
];

export const withCors = (handler) => {
  return async (req, res, context) => {
    const origin = req.headers.origin;
    if (allowedOrigins.includes(origin)) {
      res.setHeader('Access-Control-Allow-Origin', origin);
    }

    res.setHeader('Access-Control-Allow-Credentials', 'true');
    res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
    res.setHeader('Access-Control-Allow-Headers',
      'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization'
    );

    if (req.method === 'OPTIONS') {
      res.status(204).end();
      return;
    }

    return handler(req, res, context);
  };
};
