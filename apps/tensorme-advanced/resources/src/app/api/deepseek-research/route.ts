import { NextRequest, NextResponse } from 'next/server';
import { researchService } from '@/services/research/ResearchService';
import { deepseekClientService } from '@/promptService/client/deepseekClientService';
import { ResearchOptions } from '@/types/research';
import { Message } from '@/types';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { messages, persona, chatId } = body;

    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      return NextResponse.json(
        { error: 'Messages array is required' },
        { status: 400 }
      );
    }

    // Get the user's query from the last message
    const userQuery = messages[messages.length - 1]?.content;
    if (!userQuery) {
      return NextResponse.json(
        { error: 'No user query found' },
        { status: 400 }
      );
    }

    // Start research with DeepSeek-optimized options
    const researchOptions: ResearchOptions = {
      mode: 'standard',
      maxAgents: 2,
      timeout: 45000, // 45 seconds
      domains: [],
      includeCode: false,
      maxDepth: 2
    };

    const { sessionId, estimatedTime } = await researchService.startResearch(
      userQuery,
      researchOptions
    );

    // Create a readable stream that will synthesize research with DeepSeek format
    const stream = new ReadableStream({
      async start(controller) {
        let researchFindings = '';
        let isComplete = false;
        let hasStarted = false;

        // Set up research event listener
        const eventSource = researchService.createStream(sessionId);
        const reader = eventSource.getReader();

        const processResearchEvents = async () => {
          try {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              const text = new TextDecoder().decode(value);
              const lines = text.split('\n');

              for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                
                try {
                  const eventData = JSON.parse(line.substring(6));
                  
                  if (eventData.type === 'finding') {
                    // Accumulate research findings
                    const finding = eventData.data.finding;
                    researchFindings += `${finding.content} (Source: ${finding.sources[0]?.title || 'Unknown'}, Confidence: ${Math.round(finding.confidence * 100)}%) `;
                  } else if (eventData.type === 'final_report') {
                    // Research is complete, now synthesize with DeepSeek
                    isComplete = true;
                    break;
                  }
                } catch (e) {
                  console.error('Error parsing research event:', e);
                }
              }

              if (isComplete) break;
            }

            // Now create DeepSeek prompt with research findings
            const enhancedMessages: Message[] = [
              ...messages.slice(0, -1),
              {
                id: 'research-context',
                role: 'user',
                content: `Context from research: ${researchFindings}\n\nOriginal question: ${userQuery}`
              }
            ];

            // Call DeepSeek with enhanced context
            const deepseekResponse = await fetch('/api/completions', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                messages: enhancedMessages,
                persona,
                chatId
              })
            });

            if (!deepseekResponse.ok) {
              throw new Error('DeepSeek API call failed');
            }

            // Stream DeepSeek response
            const deepseekReader = deepseekResponse.body?.getReader();
            if (!deepseekReader) {
              throw new Error('No response body from DeepSeek');
            }

            while (true) {
              const { done, value } = await deepseekReader.read();
              if (done) break;

              // Forward DeepSeek stream chunks
              controller.enqueue(value);
            }

            controller.close();

          } catch (error) {
            console.error('Research-DeepSeek integration error:', error);
            
            // Send error in DeepSeek stream format
            const errorChunk = `data: ${JSON.stringify({
              choices: [{
                text: 'Research failed, providing direct response...\n\n',
                finish_reason: null
              }]
            })}\n\n`;
            
            controller.enqueue(new TextEncoder().encode(errorChunk));
            
            // Fall back to regular DeepSeek call
            try {
              const fallbackResponse = await fetch('/api/completions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ messages, persona, chatId })
              });

              if (fallbackResponse.ok && fallbackResponse.body) {
                const fallbackReader = fallbackResponse.body.getReader();
                while (true) {
                  const { done, value } = await fallbackReader.read();
                  if (done) break;
                  controller.enqueue(value);
                }
              }
            } catch (fallbackError) {
              console.error('Fallback also failed:', fallbackError);
            }
            
            controller.close();
          }
        };

        processResearchEvents();
      }
    });

    return new NextResponse(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });

  } catch (error) {
    console.error('DeepSeek Research API error:', error);
    return NextResponse.json(
      { error: 'Failed to process research request' },
      { status: 500 }
    );
  }
}