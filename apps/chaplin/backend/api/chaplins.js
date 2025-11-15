// api/chaplins.js (modificado)
import { withMiddleware } from "../lib/withMiddleware.js";
import { withCors } from "../lib/withCors.js";
import { db } from "../lib/firebase.js";

async function getChaplinsHandler(req, res) {
  try {
    const chaplinsRef = db.ref('chaplins');
    const snapshot = await chaplinsRef.once('value');
    const chaplins = snapshot.val() || {};

    // Mapear e remover qualquer imagebase64 pesado — assumir que agora usamos image_url
    const light = Object.entries(chaplins).reduce((acc, [id, item]) => {
      acc[id] = {
        name: item.name,
        category: item.category,
        instructions: item.instructions,
        // inclua image_url pequeno/thumbnail se existir; não inclua base64
        image_url: item.image_url || null,
        // quaisquer outros campos leves que você realmente precisa...
      };
      return acc;
    }, {});

    return res.status(200).json(light);
  } catch (err) {
    console.error("getChaplinsHandler error:", err);
    return res.status(500).json({ error: "Failed to fetch Chaplins.", detail: err.message });
  }
}

export default withCors(withMiddleware(getChaplinsHandler, {
  allowedMethods: ["GET"],
}));