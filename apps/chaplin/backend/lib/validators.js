// lib/validators.js
// Funções de validação reutilizáveis para os endpoints da API.

import { 
  NAME_MAX, DESCRIPTION_MAX, INSTRUCTION_MAX, CATEGORY_OPTIONS, RESPONSE_KEY_MAX, RESPONSE_DESC_MAX, 
  MAX_RESPONSE_PAIRS, MAX_WORKGROUP_MEMBERS, MAX_PREV 
} from "./constants.js";

// Erro customizado para diferenciar falhas de validação de outros erros do servidor.
class ValidationError extends Error {
  constructor(message) {
    super(message);
    this.name = "ValidationError";
  }
}

/**
 * Valida os campos principais da persona.
 * @param {{name: string, category: string, description: string, instruction:string}} personaData
 * @throws {ValidationError} Se a validação falhar.
 */
export function validatePersona({ name, category, description, instructions }) {

  if (!name || !category || !description || !instructions) throw new ValidationError("Missing required fields: name, category, description, instructions");
  if (typeof name !== "string" || typeof category !== "string" || typeof description !== "string" || typeof instructions !== "string") throw new ValidationError("name/category/description/instruction must be strings");
  if (name.length > NAME_MAX) throw new ValidationError(`Field 'name' exceeds the maximum length of ${NAME_MAX} characters.`);
  if (description.length > DESCRIPTION_MAX) throw new ValidationError(`Field 'description' exceeds the maximum length of ${DESCRIPTION_MAX} characters.`);
  if (instructions.length > INSTRUCTION_MAX) throw new ValidationError(`Field 'instructions' exceeds the maximum length of ${INSTRUCTION_MAX} characters.`);
  if (!CATEGORY_OPTIONS.includes(category)) throw new ValidationError(`Invalid 'category'. Must be one of: ${CATEGORY_OPTIONS.join(", ")}`);
}

/**
 * Valida o objeto responseformat.
 * @param {object | null} responseformat
 * @throws {ValidationError} Se a validação falhar.
 */
export function validateResponseFormat(responseformat) {
  if (!responseformat) return; // É opcional, então null/undefined é válido.
  
  if (typeof responseformat !== 'object' || responseformat === null || Array.isArray(responseformat)) throw new ValidationError("responseformat must be a JSON object.");
  
  const keys = Object.keys(responseformat);
  if (keys.length > MAX_RESPONSE_PAIRS) throw new ValidationError(`responseformat cannot have more than ${MAX_RESPONSE_PAIRS} keys.`);

  for (const key of keys) {
    if (key.length > RESPONSE_KEY_MAX) throw new ValidationError(`Key '${key}' in responseformat exceeds max length of ${RESPONSE_KEY_MAX}.`);
    const value = responseformat[key];
    if (typeof value !== 'string' || value.length > RESPONSE_DESC_MAX) throw new ValidationError(`Description for key '${key}' exceeds max length of ${RESPONSE_DESC_MAX}.`);
  }
}

/**
 * Valida um array de workgroup (ou previousWorkgroup).
 * @param {Array} workgroup
 * @param {{name: string, max: number}} options - Opções para personalizar a mensagem de erro.
 * @throws {ValidationError} Se a validação falhar.
 */
export function validateWorkgroup(workgroup, { name = 'workgroup', max = MAX_WORKGROUP_MEMBERS } = {}) {
  if (!Array.isArray(workgroup)) throw new ValidationError(`${name} must be an array.`);
  if (workgroup.length > max) throw new ValidationError(`${name} cannot have more than ${max} members.`);
}