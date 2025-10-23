import { NextResponse } from "next/server";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

export async function POST(req) {
  try {
    const body = await req.json();
    const { sessionId, agent, role, message } = body;
    if (!sessionId || !role || !message) {
      console.warn("⚠️ Missing fields:", { sessionId, role, message });
      return NextResponse.json(
        { error: "Missing required fields (sessionId, role, message)" },
        { status: 400 }
      );
    }

    const saved = await prisma.chatHistory.create({
      data: {
        sessionId,
        agent: agent || "generalAssistant",
        role,
        message,
      },
    });

    return NextResponse.json(saved);
  } catch (error) {
    console.error("❌ Error saving chat:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function GET(req) {
  const { searchParams } = new URL(req.url);
  const sessionId = searchParams.get("sessionId");

  if (!sessionId)
    return NextResponse.json({ error: "sessionId required" }, { status: 400 });

  try {
    const chats = await prisma.chatHistory.findMany({
      where: { sessionId },
      orderBy: { createdAt: "asc" },
    });

    return NextResponse.json(chats);
  } catch (error) {
    console.error("❌ Error fetching chat:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}