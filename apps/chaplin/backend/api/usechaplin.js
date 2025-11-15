// /api/usechaplin.js
import { Redis } from "@upstash/redis";
import { Client } from "@upstash/qstash";
import crypto from "crypto";
import { withCorsEdge } from "../lib/withCorsEdge.js";
import { db } from "../lib/firebase.js"; 

const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL,
  token: process.env.UPSTASH_REDIS_REST_TOKEN,
});

const qstash = new Client({
  token: process.env.QSTASH_TOKEN,
});

const encoder = new TextEncoder();

async function* pollRedisForUpdates(jobId, signal) {
  // ... (esta função permanece a mesma)
  const jobKey = `job:${jobId}`;
  let lastProgressIndex = 0;

  while (!signal.aborted) {
    const jobData = await redis.json.get(jobKey, "$");
    const job = jobData && jobData.length > 0 ? jobData[0] : null;

    if (!job) {
      yield { type: 'error', data: { message: 'Job not found or expired.' } };
      return;
    }

    const progress = job.progress || [];
    if (progress.length > lastProgressIndex) {
      for (let i = lastProgressIndex; i < progress.length; i++) {
        yield progress[i];
      }
      lastProgressIndex = progress.length;
    }

    if (job.status === 'done' || job.status === 'failed') {
      const finalResult = progress.find(p => p.type === 'integrator_result');
      if (finalResult) yield finalResult;
      
      yield { type: 'done', data: { status: job.status, error: job.error || null } };
      return;
    }

    await new Promise(resolve => setTimeout(resolve, 1500));
  }
}

async function handler(req) {
  try {
    const body = await req.json().catch(() => ({}));
    // Renomeia jobId vindo da requisição para evitar conflito
    const { chaplin_id, input, jobId: requestedJobId, chaplinData: reqChaplinData } = body;

    let jobId = requestedJobId;

    // <<< CORREÇÃO PRINCIPAL: LÓGICA DE CRIAÇÃO VS REANEXAÇÃO >>>
    if (!jobId) {
      // --- Cenário 1: CRIAR um novo job ---
      let finalChaplinData = reqChaplinData;

      if (chaplin_id && !finalChaplinData) {
        const chapSnap = await db.ref(`chaplin_full/${chaplin_id}`).once("value");
        if (!chapSnap.exists()) {
          return new Response(JSON.stringify({ error: "Chaplin not found" }), { status: 404 });
        }
        finalChaplinData = chapSnap.val();
      }

      if (!finalChaplinData || !finalChaplinData.workgroup) {
         return new Response(JSON.stringify({ error: "Invalid Chaplin data: missing workgroup definition." }), { status: 400 });
      }

      // Gera um novo ID para o job que estamos criando
      jobId = crypto.randomBytes(12).toString('hex');
      const jobKey = `job:${jobId}`;

      const jobPayload = {
        jobId,
        status: "queued",
        input: input || null,
        chaplinData: finalChaplinData, 
        chaplin_id: chaplin_id || null,
        createdAt: Date.now(),
        progress: [],
      };

      const p = redis.pipeline();
      p.json.set(jobKey, "$", jobPayload);
      p.expire(jobKey, 3600);
      await p.exec();

      await qstash.publishJSON({
        url: `${process.env.BACKEND_URL}/api/process-job`,
        body: { jobId },
        delay: 1, 
      });
    }
    // --- Cenário 2: REANEXAR a um job existente ---
    // Se um 'jobId' foi fornecido, não fazemos nada. Apenas pulamos para a fase de polling.
    // A validação se o job existe será feita pelo próprio poller.
    console.log(`[usechaplin] ${requestedJobId ? 'Re-attaching to' : 'Creating'} job: ${jobId}`);
    
    const abortController = new AbortController();

    const stream = new ReadableStream({
      async start(controller) {
        // Envia o start event com o ID do job (seja ele novo ou existente)
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "start", jobId })}\n\n`));

        const poller = pollRedisForUpdates(jobId, abortController.signal);
        
        try {
            for await (const chunk of poller) {
                if (abortController.signal.aborted) break;
                controller.enqueue(encoder.encode(`data: ${JSON.stringify(chunk)}\n\n`));
            }
        } catch (err) {
            console.error(`[usechaplin] Error during polling for job ${jobId}:`, err);
        } finally {
            if (!controller.closed) {
                controller.close();
            }
        }
      },
      cancel(reason) {
        console.log(`[usechaplin] Stream for job ${jobId} cancelled by client. Reason:`, reason);
        abortController.abort();
      }
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
      },
    });

  } catch (err) {
    console.error("[usechaplin] Setup error:", err);
    return new Response(JSON.stringify({ error: err.message }), { status: 500 });
  }
}

export const OPTIONS = withCorsEdge(async () => new Response(null, { status: 204 }));
export const POST = withCorsEdge(handler);