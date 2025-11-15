// src/index.ts

const corsHeaders = {
  'Access-Control-Allow-Origin': '*', 
  'Access-Control-Allow-Methods': 'GET, HEAD, POST, OPTIONS', 
  'Access-Control-Allow-Headers': 'Content-Type', 
};

var index_default = {
  async fetch(request, env) {

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: corsHeaders,
      });
    }

    const url = new URL(request.url);
    const prompt = url.searchParams.get("prompt") || "cyberpunk cat";

    const pastelColors = [
      "pastel pink",
      "pastel blue",
      "pastel green",
      "pastel yellow",
      "pastel purple",
      "pastel orange",
      "pastel mint",
      "pastel peach",
      "pastel lilac",
      "pastel turquoise"
    ];

    const randomColor = pastelColors[Math.floor(Math.random() * pastelColors.length)];

    const new_prompt = `Claymorphic design of ${prompt} with ${randomColor} background, high quality`;

    const inputs = { prompt: new_prompt, steps: 1, width: 512, height: 512 };

    const response = await env.AI.run(
      "@cf/black-forest-labs/flux-1-schnell",
      inputs
    );

    const binaryString = atob(response.image);
    const img = Uint8Array.from(binaryString, (m) => m.codePointAt(0));

    return new Response(img, {
      headers: {
        "Content-Type": "image/jpeg",
        ...corsHeaders,
      },
      
    });
  },
};

export {
  index_default as default,
};