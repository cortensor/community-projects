export async function runAgent(
  prompt,
  sessionId,
  agentConfig,
  metadata, 
  onThinking,
  onDone
) {
  if (!prompt?.trim()) return;
  if (!sessionId) return;

  const { agentName, systemPrompt } = agentConfig;

  try {
    let formattedHistory = "";
    try {
      const historyRes = await fetch(`/api/chat?sessionId=${sessionId}`);
      if (historyRes.ok) {
        const history = await historyRes.json();

        const agentHistory = history.filter(
          (msg) => msg.agent === agentName
        );

        const recentHistory = agentHistory.slice(-10);

        formattedHistory = recentHistory
          .map((msg) => {
            const roleName = msg.role === "ai" ? "AI" : "User";
            return `${roleName}: ${msg.message}`;
          })
          .join("\n");
      }
    } catch (e) {
      console.error("Failed to retrieve history:", e);
    }

    await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sessionId,
        agent: agentName, 
        role: "user",
        message: prompt, 
      }),
    });

    if (onThinking) onThinking();

    const finalPrompt = `${systemPrompt}

${formattedHistory}
User: ${prompt}
AI:`;

    await fetch(process.env.NEXT_PUBLIC_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${process.env.NEXT_PUBLIC_API_KEY}`,
      },
      body: JSON.stringify({
        session_id: process.env.NEXT_PUBLIC_SESSION_ID,
        prompt: finalPrompt,
        stream: false,
        timeout: 60,
      }),
    });

    let attempts = 0;
    while (attempts < 30) {
      attempts++;
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_TASK}/${process.env.NEXT_PUBLIC_SESSION_ID}`,
        {
          headers: {
            Authorization: `Bearer ${process.env.NEXT_PUBLIC_API_KEY}`,
          },
        }
      );
      const data = await res.json();

      if (data?.tasks?.length > 0) {
        const last = data.tasks[data.tasks.length - 1];
        const valid = last.results.find((r) => r?.trim());

        if (valid) {
          let result = valid;
          const thinkTagIndex = result.lastIndexOf("</think>");
          const lastAiIndex = result.lastIndexOf("AI:");
          const splitIndex = Math.max(thinkTagIndex, lastAiIndex);
          if (splitIndex > -1) {
            let tagLength = splitIndex === thinkTagIndex ? 9 : 3;
            result = result.substring(splitIndex + tagLength);
          }

          const lastTagIndex = result.lastIndexOf("<");
          const buffer = 25; 
          if (lastTagIndex > -1 && lastTagIndex > result.length - buffer) {
            result = result.substring(0, lastTagIndex);
          }
          result = result.replaceAll("<｜end of sentence｜>", "");
          result = result.replaceAll("<|end of sentence|>", "");
          result = result.replace(/<[^>]*end of sentence[^>]*>/gi, "");
          result = result.replace(/<\/s>/gi, "");
          result = result.replace(/<\/think>/gi, "");

          let finalResult = result.trim();
          finalResult = finalResult.replace(/^[a-zA-Z0-9_-]+:\s*/, "").trim();

          const messageData = {
            content: finalResult,
            metadata:
              agentName === "🔄 Format Converter" && metadata ? metadata : null,
          };

          await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              sessionId,
              agent: agentName,
              role: "ai",
              message: JSON.stringify(messageData),
            }),
          });

          if (onDone) onDone(finalResult); 
          return;
        }
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
    if (onDone) onDone("⚠️ Timeout.");
  } catch (error) {
    console.error(`[Error di ${agentName}]`, error);
    if (onDone) onDone(`⚠️ Error: ${error.message}`); 
  }
}