import { Message } from '@/types';
import { getModelConfig } from '@/lib/models';
import { getPromptService } from '@/promptService/backend';
import { NextRequest } from 'next/server';
import taskService from '@/services/taskService';

export const runtime = 'edge';

export async function POST(request: NextRequest) {
  try {
    const { messages, persona, clientReference, userId, chatId, historySummary, modelId, domainId }: {
      messages: Message[],
      persona?: string,
      clientReference: string,
      userId: string,
      chatId: string,
      historySummary?: string,
      modelId?: string,
      domainId?: string
    } = await request.json();

    const CORTENSOR_API_URL = process.env.CORTENSOR_API_URL;
    const CORTENSOR_API_TOKEN = process.env.CORTENSOR_API_TOKEN;
    const ENABLE_STREAMING = process.env.ENABLE_STREAMING === 'true';

    if (!CORTENSOR_API_URL || !CORTENSOR_API_TOKEN) {
      return new Response('API configuration is missing.', { status: 500 });
    }

    const modelConfig = getModelConfig(modelId || 'deepseek-r1');
    if (!modelConfig) {
      return new Response('Invalid model specified.', { status: 400 });
    }

    const promptService = getPromptService(modelConfig.id);
    const CORTENSOR_SESSION_ID = promptService.getSessionId();

    const prompt = promptService.buildPrompt({
      messages,
      persona,
      domainContext: domainId,
      historySummary
    });

    const curlCommand = `
      curl -X POST ${CORTENSOR_API_URL}/completions/${CORTENSOR_SESSION_ID} \\
      -H "Content-Type: application/json" \\
      -H "Authorization: Bearer ${CORTENSOR_API_TOKEN}" \\
      -d '{
        "prompt": "${prompt}",
        "stream": ${ENABLE_STREAMING},
        "temperature": 0.3,
        "max_tokens": 4096,
        "prompt_template": "",
        "timeout": 240,
        "top_p": 0.9,
        "top_k": 40,
        "prompt_type": 1,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "client_reference": "${clientReference}test"
      }'
    `;

    console.log('Generated cURL command:', curlCommand);

    const routerNodeResponse = await fetch(`${CORTENSOR_API_URL}/completions/${CORTENSOR_SESSION_ID}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${CORTENSOR_API_TOKEN}`,
      },
      body: JSON.stringify({
        prompt: prompt,
        stream: ENABLE_STREAMING,
        temperature: 0.3,
        max_tokens: 4096,
        prompt_template: "",
        timeout: 240,
        top_p: 0.9,
        top_k: 40,
        prompt_type: 1,
        presence_penalty: 0,
        frequency_penalty: 0,
        client_reference: clientReference + 'test',
      }),
    });

    if (!routerNodeResponse.ok) {
      const errorBody = await routerNodeResponse.text();
      return new Response(`Error from external API: ${errorBody}`, { status: routerNodeResponse.status });
    }

    taskService.processChatListeners(CORTENSOR_SESSION_ID.toString(), clientReference, userId, chatId);

    if (ENABLE_STREAMING) {
      return new Response(routerNodeResponse.body, {
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
    } else {
      const responseData = await routerNodeResponse.json();
      const fullText = responseData.choices[0].text;
      const completionId = responseData.id;
      const created = responseData.created;
      
      const stream = new ReadableStream({
        start(controller) {
          const words = fullText.split(' ');
          let index = 0;
          
          const pushChunk = () => {
            if (index < words.length) {
              const word = words[index];
              const chunkData = {
                id: completionId,
                object: "text_completion",
                created: created,
                choices: [{
                  text: word + (index < words.length - 1 ? ' ' : ''),
                  index: 0,
                  logprobs: null,
                  finish_reason: null
                }],
                model: "default"
              };
              controller.enqueue(`data: ${JSON.stringify(chunkData)}\n\n`);
              index++;
              setTimeout(pushChunk, 50);
            } else {
              const finalChunk = {
                id: completionId,
                object: "text_completion",
                created: created,
                choices: [{
                  text: "",
                  index: 0,
                  logprobs: null,
                  finish_reason: "stop"
                }],
                model: "default"
              };
              controller.enqueue(`data: ${JSON.stringify(finalChunk)}\n\n`);
              controller.enqueue('data: [DONE]\n\n');
              controller.close();
            }
          };
          
          pushChunk();
        }
      });

      return new Response(stream, {
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
    }

  } catch (error) {
    console.error('Error in chat API route:', error);
    return new Response('An internal server error occurred.', { status: 500 });
  }
}