// server/src/utils/withCors.js
const allowedOrigins = [
  'http://localhost:5173',
  'https://chaplins.netlify.app',
  'https://chaplin.lumitylabs.com',
  'https://web3museum.lumitylabs.com',
  'https://web3museum.netlify.app'
];


export const withCorsEdge = (handler) => {
  return async (req, context) => {
    const origin = req.headers.get('origin');
    const isAllowed = allowedOrigins.includes(origin);

    // Headers CORS
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Credentials': 'true',
      'Access-Control-Allow-Methods': 'GET,OPTIONS,PATCH,DELETE,POST,PUT',
      'Access-Control-Allow-Headers': 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization',
    };

    // Resposta para preflight
    if (req.method === 'OPTIONS') {
      return new Response(null, {
        status: 200, // Mudei de 204 para 200
        headers: corsHeaders,
      });
    }

    // Handler real
    try {
      const response = await handler(req, context);
      
      // Clonar response e adicionar headers CORS
      const newHeaders = new Headers(response.headers);
      Object.entries(corsHeaders).forEach(([key, value]) => {
        newHeaders.set(key, value);
      });

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: newHeaders,
      });
    } catch (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders,
        },
      });
    }
  };
};