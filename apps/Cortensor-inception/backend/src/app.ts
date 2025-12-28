import express from "express";
import validateRouter from "./api/validate.controller";

const app = express();

app.use(express.json());

app.get("/health", (_, res) => res.json({ ok: true }));

app.use("/validate", validateRouter);

export default app;
