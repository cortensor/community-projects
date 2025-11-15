// lib/firebase.js
import admin from "firebase-admin";

try {
  if (!admin.apps.length) {
    // Suporta JSON cru ou Base64 (útil se você preferir enviar a chave base64 como env var)
    const raw = process.env.FIREBASE_SERVICE_ACCOUNT || process.env.GOOGLE_SERVICE_ACCOUNT_JSON;
    let serviceAccount = null;

    if (raw) {
      try {
        if (raw.trim().startsWith("{")) {
          // JSON direto
          serviceAccount = JSON.parse(raw);
        } else {
          // tenta tratar como base64
          const decoded = Buffer.from(raw, "base64").toString("utf8");
          serviceAccount = JSON.parse(decoded);
        }
      } catch (e) {
        console.error("Falha ao parsear FIREBASE_SERVICE_ACCOUNT:", e.message);
        throw new Error("Formato inválido em FIREBASE_SERVICE_ACCOUNT (esperado JSON ou base64(JSON)).");
      }

      admin.initializeApp({
        credential: admin.credential.cert(serviceAccount),
        databaseURL: process.env.FIREBASE_DATABASE_URL,
      });
    } else {
      // fallback: Application Default (só funciona se o runtime fornecer ADC)
      admin.initializeApp({
        credential: admin.credential.applicationDefault(),
        databaseURL: process.env.FIREBASE_DATABASE_URL,
      });
    }
  }
} catch (error) {
  console.error("Firebase Admin Initialization Error:", error.message);
  throw new Error("Could not initialize Firebase Admin SDK. Check your credentials and database URL.");
}

export const db = admin.database();
