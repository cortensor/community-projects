// lib/workgroupEngine.js

import { generateText } from "./aiProvider.js";
import { buildAgentExecutionPrompt } from "../prompts/runWorkgroupPrompt.js";
import buildHardcodedIntegratorPrompt from "../prompts/integrator.js";

function normName(name) {
  return String(name || "").trim().toLowerCase();
}

// Esta função também precisa ser corrigida para consistência
export async function runAgentsSequentially({ input, workgroup, workgroupResponseMap = {}, options = {} }) {
  const { stopAtAgentName = null, maxTokens = 800, temperature = 0.7, executorJobId = null, onProgress = null } = options;

  const normalizedMap = {};
  Object.keys(workgroupResponseMap || {}).forEach(k => {
    normalizedMap[normName(k)] = workgroupResponseMap[k];
  });

  const updatedMap = { ...workgroupResponseMap };
  const generated = [];
  const perAgent = [];

  const stopNorm = stopAtAgentName ? normName(stopAtAgentName) : null;

  for (let i = 0; i < workgroup.length; i++) {
    const agent = workgroup[i];
    const agentNorm = normName(agent.name);

    if (normalizedMap[agentNorm]) {
      const out = normalizedMap[agentNorm];
      perAgent.push({ name: agent.name, output: out, source: "prefilled" });
      const existingKey = Object.keys(workgroupResponseMap || {}).find(k => normName(k) === agentNorm) || agent.name;
      updatedMap[existingKey] = out;
      if (stopNorm && agentNorm === stopNorm) {
        return { updatedWorkgroupResponse: updatedMap, generated, perAgent };
      }
      continue;
    }

    const agentPrompt = buildAgentExecutionPrompt({
      agent,
      input,
      previousOutputs: perAgent.map(p => p.output)
    });

    // <<< CORREÇÃO AQUI TAMBÉM >>>
    const generateOpts = {
        executorJobId,
        agentName: agent.name,
        onProgress, // Passa o callback
    };
    const out = await generateText({ prompt: agentPrompt, maxTokens, temperature }, generateOpts);

    updatedMap[agent.name] = out;
    normalizedMap[agentNorm] = out;

    generated.push({ name: agent.name, output: out });
    perAgent.push({ name: agent.name, output: out, source: "generated" });

    if (stopNorm && agentNorm === stopNorm) {
      break;
    }
  }

  return { updatedWorkgroupResponse: updatedMap, generated, perAgent };
}


export async function* executeWorkgroupStream({ input, description, instructions, workgroup, workgroupResponseMap = {}, responseformat, options = {} }) {
  const {
    maxTokens = 800, temperature = 0.7,
    integratorMaxAttempts = 3, integratorMaxTokens = 900, integratorTemperature = 0.5,
    executorJobId = null,
    onProgress = null
  } = options;

  let finalPerAgent = [];

  for (const agent of workgroup) {
    yield { type: 'agent_start', data: { name: agent.name }};

    const agentPrompt = buildAgentExecutionPrompt({ agent, input, previousOutputs: finalPerAgent.map(p => p.output) });

    // <<< CORREÇÃO PRINCIPAL AQUI >>>
    // Garante que 'onProgress' seja incluído nas opções para cada agente.
    const generateOpts = {
      executorJobId,
      agentName: agent.name,
      onProgress, // Passa o callback para a próxima camada
    };
    const output = await generateText({ prompt: agentPrompt, maxTokens, temperature }, generateOpts);

    const result = { name: agent.name, output, source: "generated" };
    finalPerAgent.push(result);
    
    yield { type: 'agent_result', data: result };
  }

  yield { type: 'integrator_start' };
  
  const outputsInOrder = finalPerAgent.map(p => p.output);
  let attempt = 0, lastRaw = null, finalParsed = null, validation = null;
  
  while (attempt < integratorMaxAttempts) {
    attempt++;
    const integratorPrompt = buildHardcodedIntegratorPrompt({ responseformat, outputs: outputsInOrder, workgroup, description, instructions, input });

    const integratorGenerateOpts = {
        executorJobId,
        agentName: "Integrator",
        attempt,
        maxAttempts: integratorMaxAttempts,
        sessionSize: 'big',
        onProgress,
    };
    lastRaw = await generateText({ prompt: integratorPrompt, maxTokens: integratorMaxTokens, temperature: integratorTemperature }, integratorGenerateOpts);
    
    let parsed = null;
    try {
      const firstBrace = lastRaw.indexOf("{");
      const lastBrace = lastRaw.lastIndexOf("}");
      if (firstBrace !== -1 && lastBrace > firstBrace) {
        parsed = JSON.parse(lastRaw.slice(firstBrace, lastBrace + 1));
      }
    } catch (e) {}

    if (parsed && typeof parsed === "object") {
      const parsedKeys = Object.keys(parsed).sort();
      const requiredKeys = Object.keys(responseformat || {}).sort();
      const missing = requiredKeys.filter(k => !parsedKeys.includes(k));
      const extras = parsedKeys.filter(k => !requiredKeys.includes(k));

      if (missing.length === 0 && extras.length === 0) {
        finalParsed = parsed;
        validation = { success: true, attempts: attempt };
        break;
      } else {
        validation = { missing_keys: missing, extra_keys: extras };
      }
    } else {
      validation = { parse_error: "Integrator output not parseable as JSON object." };
    }
  }
  
  const finalResult = {
    final: finalParsed || { error: "Integrator failed after all attempts.", raw: lastRaw },
    validation,
    attempts: attempt,
  };
  yield { type: 'integrator_result', data: finalResult };
}

// A função runWorkgroupAndIntegrate também precisa da mesma correção
export async function runWorkgroupAndIntegrate({ input, workgroup, workgroupResponseMap = {}, responseformat, options = {} }) {
  const {
    maxTokens = 800,
    temperature = 0.7,
    integratorMaxAttempts = 3,
    integratorMaxTokens = 900,
    integratorTemperature = 0.5,
    executorJobId = null,
    onProgress = null
  } = options;

  const runResult = await runAgentsSequentially({
    input,
    workgroup,
    workgroupResponseMap,
    options: { maxTokens, temperature, executorJobId, onProgress }
  });

  const perAgent = runResult.perAgent;
  const generated = runResult.generated;
  const updatedMap = runResult.updatedWorkgroupResponse;
  const outputsInOrder = perAgent.map(p => p.output);
  const requiredKeys = Object.keys(responseformat || {}).map(String).sort();

  let attempt = 0;
  let lastRaw = null;
  let finalParsed = null;
  let validation = null;

  while (attempt < integratorMaxAttempts) {
    attempt++;
    const integratorPrompt = buildHardcodedIntegratorPrompt({
      responseformat,
      outputs: outputsInOrder,
      workgroup
    });

    const integratorGenerateOpts = {
        ...(executorJobId && { executorJobId, agentName: "Integrator", attempt, maxAttempts: integratorMaxAttempts }),
        sessionSize: 'big',
        onProgress
    };

    const finalRaw = await generateText({
      prompt: integratorPrompt,
      maxTokens: integratorMaxTokens,
      temperature: integratorTemperature
    }, integratorGenerateOpts);

    lastRaw = finalRaw;

    let parsed = null;
    try {
      parsed = JSON.parse(finalRaw);
    } catch (err) {
      const firstBrace = finalRaw.indexOf("{");
      const lastBrace = finalRaw.lastIndexOf("}");
      if (firstBrace !== -1 && lastBrace > firstBrace) {
        try {
          parsed = JSON.parse(finalRaw.slice(firstBrace, lastBrace + 1));
        } catch (err2) {
          parsed = null;
        }
      }
    }

    if (!parsed || typeof parsed !== "object") {
      validation = { parse_error: "Integrator output not parseable as JSON" };
      if (attempt >= integratorMaxAttempts) {
        finalParsed = { parse_error: "Integrator failed to produce valid JSON after attempts", raw: lastRaw };
        break;
      }
      continue;
    }

    const parsedKeys = Object.keys(parsed).map(String).sort();
    const missing = requiredKeys.filter(k => !parsedKeys.includes(k));
    const extras = parsedKeys.filter(k => !requiredKeys.includes(k));

    if (missing.length === 0 && extras.length === 0) {
      finalParsed = parsed;
      validation = { success: true, attempts: attempt };
      break;
    } else {
      validation = { missing_keys: missing, extra_keys: extras };
      if (attempt >= integratorMaxAttempts) {
        finalParsed = { ...parsed, _validation: validation, raw: lastRaw };
        break;
      }
    }
  }

  return {
    perAgent,
    generated,
    updatedWorkgroupResponse: updatedMap,
    final: finalParsed,
    validation,
    attempts: attempt,
    lastRaw
  };
}