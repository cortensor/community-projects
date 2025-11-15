// api/createchaplin.js
import { withMiddleware } from "../lib/withMiddleware.js";
import { withCors } from "../lib/withCors.js";
import { db } from "../lib/firebase.js";
import { validatePersona, validateResponseFormat, validateWorkgroup } from "../lib/validators.js";
import { uploadToImgBB } from "../lib/imageUploader.js";

class ValidationError extends Error {
  constructor(message) {
    super(message);
    this.name = "ValidationError";
  }
}

async function createChaplinHandler(req, res) {
  try {
    const {
      name, category, imagebase64, instructions, description,
      responseformat, workgroup
    } = req.body;
    
    // Em um ambiente de produção, o middleware de autenticação anexaria o usuário ao `req`.
    // Ex: export const requireAuth = (req) => { req.user = await verifyToken(req.headers.authorization); }
    const creator_id = req.user?.id || "anonymous_user"; // Usando "anonymous" como fallback
    let image_url = null;
    let thumb_url = null;
    if (imagebase64) {
      // imagebase64 pode vir como 'data:image/png;base64,AAA...'
      const match = imagebase64.match(/base64,(.*)$/);
      const pureBase64 = match ? match[1] : imagebase64;
      try {
        const uploaded = await uploadToImgBB(pureBase64);
        image_url = uploaded.url;
        thumb_url = uploaded.thumb;
      } catch (err) {
        console.error("Image upload failed:", err);
        // opcional: retornar 400 ou persistir sem imagem; aqui eu retorno 500
        return res.status(500).json({ error: "Image upload failed", detail: err.message });
      }
    }


    validatePersona({ name, category, description, instructions });
    validateResponseFormat(responseformat);
    validateWorkgroup(workgroup);
    if (!instructions) throw new ValidationError("Missing required field: instructions");

    const newChaplinRef = db.ref('chaplin_full').push();
    const chaplin_id = newChaplinRef.key;

    const now = new Date().toISOString();

    const fullChaplinData = {
      name,
      category,
      image_url,   // salva URL em vez de base64
      thumb_url,
      instructions,
      description,
      responseformat,
      workgroup,
      creator_id,
      visibility: 'public',
      created_at: now
    };


    const simpleChaplinData = {
      name,
      category,
      image_url, // opcional aqui: pode omitir para listar sem imagem
      instructions,
      creator_id
    };

    const userChaplinEntry = { [chaplin_id]: true };

    const updates = {};
    updates[`/chaplin_full/${chaplin_id}`] = fullChaplinData;
    updates[`/chaplins/${chaplin_id}`] = simpleChaplinData;
    updates[`/users/${creator_id}/chaplins/${chaplin_id}`] = true;

    // Executa a atualização atômica
    await db.ref().update(updates);

    return res.status(201).json({ 
      message: "Chaplin created successfully",
      chaplin_id: chaplin_id 
    });

  } catch (err) {
    if (err.name === "ValidationError") {
      return res.status(400).json({ error: err.message });
    }
    console.error("createChaplinHandler error:", err);
    return res.status(500).json({ error: "Internal server error", detail: err.message });
  }
}

export default withCors(withMiddleware(createChaplinHandler, {
  allowedMethods: ["POST"],
  requireJson: true,
  parseJson: true,
  maxBodyBytes: 500 * 1024,

}));