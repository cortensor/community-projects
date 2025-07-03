"use client"

import { useState } from "react"
import { Button } from "./ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "./ui/dialog"
import { Textarea } from "./ui/textarea"
import { Download, Copy, Check } from "lucide-react"
import { type ChatSession } from "@/lib/storage"
import { appConfig } from "@/lib/app-config" // <-- Ini baris yang diperbaiki

interface ChatExportProps {
    session: ChatSession
}

export function ChatExport({ session }: ChatExportProps) {
  const [hasCopied, setHasCopied] = useState(false)
  const [isOpen, setIsOpen] = useState(false)

  const formatSession = (session: ChatSession) => {
    let text = `Chat Session with ${appConfig.app.assistant} \n`
    text += `Session ID: ${session.id}\n`
    text += `Created At: ${new Date(session.createdAt).toLocaleString()}\n`
    text += "------------------------------------\n\n"

    session.messages.forEach(message => {
      // Pastikan untuk menggunakan appConfig di sini juga
      const prefix = message.role === 'user' ? 'You' : appConfig.app.assistant;
      text += `[${new Date(message.timestamp).toLocaleTimeString()}] ${prefix}:\n`
      text += `${message.content}\n\n`
    })
    return text
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(formatSession(session))
    setHasCopied(true)
    setTimeout(() => setHasCopied(false), 2000)
  }

  const handleDownload = () => {
    const blob = new Blob([formatSession(session)], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `chat-session-${session.id}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  // Komponen ini tidak lagi menggunakan ChatStorage secara langsung
  // Jadi, impor ChatStorage bisa dihapus jika tidak digunakan di tempat lain
  if (!appConfig.chat.enableExport) {
    return null
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon">
          <Download className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Export Chat</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <Textarea
            readOnly
            value={formatSession(session)}
            rows={15}
            className="text-sm bg-muted/50"
          />
          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={handleCopy}>
              {hasCopied ? <Check className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}
              {hasCopied ? "Copied!" : "Copy"}
            </Button>
            <Button onClick={handleDownload}>
              <Download className="h-4 w-4 mr-2" />
              Download .txt
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
