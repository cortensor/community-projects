// lib/constants.js

// Limites de input da Persona/Tarefa
export const NAME_MAX = 25;
export const DESCRIPTION_MAX = 500;
export const INSTRUCTION_MAX = 500;
export const CATEGORY_OPTIONS = [
  "Assistants", "Anime", "Creativity & Writing", "Entertainment & Gaming",
  "History", "Humor", "Learning",
];

// Limites do 'responseformat' (Step 2)
export const RESPONSE_KEY_MAX = 60;
export const RESPONSE_DESC_MAX = 100;
export const MAX_RESPONSE_PAIRS = 6;

// Limites do Workgroup (Agentes)
export const AGENT_NAME_MAX = 60;
export const AGENT_PROMPT_MAX = 3000;

// Limites do Servidor e da API
export const MAX_WORKGROUP_MEMBERS = 3;
export const MAX_PREV = 3;
export const MAX_FORMAT_BYTES = 2048;
export const LLM_MAX_ATTEMPTS = 3;

// Limites para runagent/runworkgroup
export const MAX_RESPONSE_ENTRIES = 6;