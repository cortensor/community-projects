

import GeminiBase from "./GeminiBase.js";

export default class GeminiFlashModel extends GeminiBase {
  constructor(opts = {}) {
    super({ ...opts, modelName: opts.modelName || process.env.GEMINI_FLASH_MODEL || "gemini-flash-latest" });
    this.key = opts.key || "geminiflash";
  }


}
