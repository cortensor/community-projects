import assert from "assert";

export const PORT = process.env.PORT ? Number(process.env.PORT) : 4000;
export const CORTENSOR_API_KEY = process.env.CORTENSOR_API_KEY || "";

assert(PORT > 0, "PORT must be set");

export default {
  PORT,
  CORTENSOR_API_KEY,
};
