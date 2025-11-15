// api/generateimage.js
import buildGenerateImagePrompt from "../prompts/generateImagePrompt.js";
import { generateText } from "../lib/aiProvider.js";
import fetch from "node-fetch";
import { withMiddleware } from "../lib/withMiddleware.js";
import { withCors } from "../lib/withCors.js";
import { validatePersona, validateWorkgroup } from "../lib/validators.js"; // <<< NOVO

async function handler(req, res) {
  try {
    const { name, description, instructions, category, workgroup = [] } = req.body || {};

    // <<< VALIDAÇÃO CENTRALIZADA >>>
    validatePersona({ name, description, category, instructions });
    validateWorkgroup(workgroup);

    // --- Lógica de Negócios ---
    const promptForImage = buildGenerateImagePrompt({
      name: name.trim(),
      description: description.trim(),
      category: category.trim(),
      workgroup
    });

    // A geração do prompt de imagem não precisa de retry de parse, pois espera uma string.
    const imagePrompt = (await generateText(
        { prompt: promptForImage, maxTokens: 200, temperature: 0.8 },
        { sessionSize: 'small' } // Passa a dica para o aiProvider
    )).trim();

    const url = process.env.IMAGE_WORKER_URL +`/?prompt=${encodeURIComponent(imagePrompt)}`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`Image worker failed with status ${resp.status}`);

    const buffer = await resp.arrayBuffer();
    const base64 = Buffer.from(buffer).toString("base64");
    const mime = resp.headers.get("content-type") || "image/png";

    res.status(200).json({ imagePrompt, mime, base64: `data:${mime};base64,${base64}` });

  } catch (err) {
    // <<< TRATAMENTO DE ERRO MELHORADO >>>
    if (err.name === "ValidationError") {
      return res.status(400).json({ error: err.message });
    }
    console.error("generateimage error:", err);
    if (!res.headersSent) {
      res.status(500).json({ error: "Internal server error", detail: err.message });
    }
  }
}

export default withCors(withMiddleware(handler, {
  allowedMethods: ["POST"],
  requireJson: true,
  parseJson: true,
  maxBodyBytes: 200 * 1024,
  rateLimit: { windowMs: 60_000, max: 20 }
}));