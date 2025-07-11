
/**
 * Generates a unique ID using the Web Crypto API.
 */
export const generateId = (): string => crypto.randomUUID();

/**
 * Parses a JSON string without throwing an error.
 * @param jsonString The string to parse.
 * @returns The parsed object, or an object with the raw string if parsing fails.
 */
export function safeJsonParse<T>(jsonString: string): T | { raw: string } {
  try {
    return JSON.parse(jsonString) as T;
  } catch {
    return { raw: jsonString };
  }
}

export const cleanBotResponse = (text: string): string => {
  const assistantMarker = 'Assistant: ';
  const lastIndex = text.lastIndexOf(assistantMarker);

  let cleanedText = text;
  if (lastIndex !== -1) {
    cleanedText = text.substring(lastIndex + assistantMarker.length);
  }

  cleanedText = cleanedText.replace(/<[^>]*>/g, '').trim();
  const prefixes = ["Cortensor:", "Assistant:", "Eliza:"];
  for (const prefix of prefixes) {
    if (cleanedText.startsWith(prefix)) {
      cleanedText = cleanedText.substring(prefix.length).trim();
    }
  }

  return cleanedText;
};