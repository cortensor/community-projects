import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import authRouter from "./routes/auth";
import escrowRouter from "./routes/escrow";
import validateRouter from "./api/validate.controller";
import testRouter from "./routes/test";
import claimsRouter from "./api/claims.controller";
import riskRouter from "./api/risk.controller";

dotenv.config();

const app = express();

app.use(cors());
app.use(express.json());

app.get("/health", (_, res) => res.json({ ok: true }));

app.use("/auth", authRouter);
app.use("/", escrowRouter);
app.use("/validate", validateRouter);
app.use("/test", testRouter);
app.use("/api/claims", claimsRouter);
app.use("/api", riskRouter);

export default app;
