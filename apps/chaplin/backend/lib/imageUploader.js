// lib/imageUploader.js
import fetch from "node-fetch";

export async function uploadToImgBB(base64Data) {
  if (!process.env.IMGBB_KEY) throw new Error("Missing IMGBB_KEY env var");
  // base64Data deve ser apenas a parte base64 (sem prefixo data:...;base64,)
  const url = `https://api.imgbb.com/1/upload?key=${process.env.IMGBB_KEY}`;
  const body = new URLSearchParams();
  body.append("image", base64Data);

  const resp = await fetch(url, { method: "POST", body });
  const json = await resp.json();
  if (!resp.ok || json.status !== 200) {
    throw new Error("ImgBB upload failed: " + JSON.stringify(json));
  }
  // retorna a URL pública
  return {
    url: json.data.url, // ou display_url / thumb?
    thumb: json.data.thumb?.url || null,
    delete_url: json.data.delete_url || null
  };
}