import fs from "fs";
import crypto from "crypto";

const outKey = process.argv[2] || process.env.OUT_KEY || "attestor.key";
const outPub = process.argv[3] || process.env.OUT_PUB || "attestor.pub";

function gen() {
  const { publicKey, privateKey } = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });

  const privatePem = privateKey.export({ type: "pkcs1", format: "pem" }).toString();
  const publicPem = publicKey.export({ type: "pkcs1", format: "pem" }).toString();

  fs.writeFileSync(outKey, privatePem);
  fs.writeFileSync(outPub, publicPem);

  console.log(`Wrote private key to ${outKey}`);
  console.log(`Wrote public key to ${outPub}`);
}

try {
  gen();
} catch (err) {
  console.error(err);
  process.exit(1);
}
