"use client"

import { Button } from "./ui/button"
import { ChatExport } from "./chat-export"
import { appConfig } from "@/lib/app-config"
import type { ChatSession } from "@/lib/storage"
import { IconTrash } from "./ui/icons" // Asumsi Anda punya file ini, jika tidak, hapus atau ganti

interface SessionHeaderProps {
  currentSession: ChatSession | undefined
  onDeleteSession: (sessionId: string) => void
}

export function SessionHeader({
  currentSession,
  onDeleteSession,
}: SessionHeaderProps) {
  if (!currentSession) return null

  // Asumsi dari file page.tsx Anda, Anda tidak menggunakan blockchainSessionId di sini.
  // Jika Anda membutuhkannya, tambahkan kembali.

  return (
    <div className="flex items-center justify-between p-4 border-b">
      <h2 className="text-lg font-semibold truncate">{currentSession.title}</h2>
      <div className="flex items-center space-x-2">
        {appConfig.chat.enableExport && <ChatExport session={currentSession} />}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onDeleteSession(currentSession.id)}
        >
          {/* Ganti dengan ikon yang benar jika IconTrash tidak ada */}
          <Trash2 className="h-4 w-4" /> 
        </Button>
      </div>
    </div>
  )
}
