

import GeminiBase from "./GeminiBase.js";

export default class GeminiFlashLiteModel extends GeminiBase {
  constructor(opts = {}) {
    super({ ...opts, modelName: opts.modelName || process.env.GEMINI_FLASH_MODEL || "gemini-2.5-flash-lite" });
    this.key = opts.key || "geminiflashlite";
  }


}
