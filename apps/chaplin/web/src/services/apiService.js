// src/services/apiService.js
import { fetchEventSource } from '@microsoft/fetch-event-source';
const API_BASE_URL = import.meta.env.VITE_APP_API_BASE_URL;

async function handleResponse(response) {
  if (response.ok) {
    return response.json();
  }

  let errorDetail = `HTTP error! Status: ${response.status} - ${response.statusText}`;
  try {
    const errorBody = await response.json();
    errorDetail = errorBody.detail || errorBody.error || JSON.stringify(errorBody);
  } catch (e) {
    console.warn("Could not parse error response body as JSON.");
  }

  throw new Error(errorDetail);
}

export const createChaplin = async (chaplinData) => {
  if (!API_BASE_URL) {
    const errorMessage = "VITE_APP_API_BASE_URL is not defined in your .env file.";
    console.error(errorMessage);
    return { data: null, error: errorMessage };
  }

  try {
    const response = await fetch(`${API_BASE_URL}/createchaplin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(chaplinData),
    });

    const data = await handleResponse(response);
    return { data, error: null };

  } catch (error) {
    console.error("Failed to create chaplin in service:", error);
    return { data: null, error: error.message };
  }
};

export const startChaplinStream = (payload, { onData, onError, onClose } = {}) => {
  if (!API_BASE_URL) {
    const errorMessage = "VITE_APP_API_BASE_URL is not defined.";
    if (onError) onError(new Error(errorMessage));
    return { abort: () => {} };
  }

  const controller = new AbortController();

  fetchEventSource(`${API_BASE_URL}/usechaplin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: controller.signal,

    async onopen(response) {
      if (response.ok && response.headers.get('content-type')?.includes('text/event-stream')) {
        console.log("[startChaplinStream] Stream opened.");
        return;
      }
      const text = await response.text().catch(() => "<no body>");
      const err = new Error(`Failed to connect to stream: ${response.status} ${response.statusText} - ${text}`);
      if (onError) onError(err);
      throw err;
    },

    onmessage(event) {
      if (!event.data) return;
      if (event.data === '[DONE]') {
        return;
      }

      try {
        const jsonData = JSON.parse(event.data);
        if (onData) {
          try { onData(jsonData); } catch (e) { console.error("[startChaplinStream] onData handler failed:", e); }
        }
      } catch (parseErr) {
        console.warn("[startChaplinStream] Failed to parse event data as JSON, forwarding as raw:", parseErr?.message);
        if (onData) {
          try {
            onData({ _raw: true, raw: event.data });
          } catch (e) {
            console.error("[startChaplinStream] onData handler failed while forwarding raw:", e);
          }
        }
      }
    },

    onclose() {
      console.log("[startChaplinStream] Stream closed by server.");
      if (onClose) onClose();
    },

    onerror(err) {
      console.error("[startChaplinStream] stream error:", err?.message || err);
      if (onError) {
        try { onError(err); } catch (e) { console.error("[startChaplinStream] onError handler threw:", e); }
      }
      // A biblioteca tentará se reconectar por padrão, mas nossa lógica de visibilidade
      // no componente irá abortar a conexão antes que isso aconteça, nos dando controle.
    },
  });

  return {
    abort: () => {
      try { controller.abort(); } 
      catch (e) {
        console.error("[startChaplinStream] Failed to abort stream:", e);
      }
    }
  };
};




export const getChaplins = async () => {
  if (!API_BASE_URL) {
    const errorMessage = "VITE_APP_API_BASE_URL is not defined in your .env file.";
    console.error(errorMessage);
    return { data: null, error: errorMessage };
  }

  try {
    const response = await fetch(`${API_BASE_URL}/chaplins`, {
      method: 'GET',
    });
    const data = await handleResponse(response);
    return { data, error: null };
  } catch (error) {
    console.error("Failed to fetch chaplins in service:", error);
    return { data: null, error: error.message };
  }
};


export const generateWorkgroup = async ({ name, category, description, instructions, responseformat }) => {
  if (!API_BASE_URL) {
    const errorMessage = "VITE_APP_API_BASE_URL is not defined in your .env file.";
    console.error(errorMessage);
    return { data: null, error: errorMessage };
  }

  try {
    const response = await fetch(`${API_BASE_URL}/createworkgroup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        category,
        description,
        instructions,
        responseformat, 
        max_members: 3, 
      }),
    });

    const data = await handleResponse(response);
    return { data: data.workgroup || [], error: null };

  } catch (error) {
    console.error("Failed to generate workgroup in service:", error);
    return { data: null, error: error.message };
  }
};

export const generateImage = async ({ name, category, description, instructions }) => {
  if (!API_BASE_URL) {
    const errorMessage = "VITE_APP_API_BASE_URL is not defined in your .env file.";
    console.error(errorMessage);
    return { data: null, error: errorMessage };
  }

  try {
    const response = await fetch(`${API_BASE_URL}/generateimage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, category, description, instructions }),
    });
    const data = await handleResponse(response);
    return { data, error: null };

  } catch (error) {
    console.error("Failed to generate image in service:", error);
    return { data: null, error: error.message };
  }
};

export const runAgent = async ({ input, workgroup, workgroupresponse, targetAgentName }) => {
  if (!API_BASE_URL) {
    const errorMessage = "VITE_APP_API_BASE_URL is not defined in your .env file.";
    console.error(errorMessage);
    return { data: null, error: errorMessage };
  }
  try {
    const response = await fetch(`${API_BASE_URL}/runagent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input, workgroup, workgroupresponse, targetAgentName }),
    });
    const data = await handleResponse(response);
    return { data: data.updatedWorkgroupResponse || {}, error: null };
  } catch (error) {
    console.error("Failed to run agent in service:", error);
    return { data: null, error: error.message };
  }
};