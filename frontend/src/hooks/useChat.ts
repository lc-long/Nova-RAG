import { useCallback, useRef } from 'react'
import type { Message, Reference } from '../types'
import { streamChat } from '../lib/api'
import { useAppStore } from '../store/useAppStore'

const STORAGE_KEY = 'nova_chat_history'

export function useChat() {
  const {
    messages, setMessages,
    conversationId, setConversationId,
  } = useAppStore()

  const requestInFlight = useRef(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  const cancelStream = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
  }, [])

  const sendMessage = useCallback(async (
    input: string,
    docIds: string[] | null,
  ) => {
    if (!input.trim() || requestInFlight.current) return

    requestInFlight.current = true

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input,
      reasoning: '',
      thoughts: [],
    }
    const assistantMessage: Message = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      reasoning: '',
      thoughts: [],
    }

    setMessages((prev) => [...prev, userMessage, assistantMessage])

    // Build conversation history
    const MAX_HISTORY = 10
    const recentMessages = messages.slice(-MAX_HISTORY).map((m) => ({
      role: m.role,
      content: m.content,
    }))
    recentMessages.push({ role: 'user', content: input })

    const controller = streamChat(recentMessages, docIds, conversationId, {
      onThought: (content) => {
        setMessages((prev) => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last && last.role === 'assistant') {
            updated[updated.length - 1] = { ...last, thoughts: [...last.thoughts, content] }
          }
          return updated
        })
      },
      onReasoning: (content) => {
        setMessages((prev) => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last && last.role === 'assistant') {
            updated[updated.length - 1] = { ...last, reasoning: last.reasoning + content }
          }
          return updated
        })
      },
      onAnswer: (content) => {
        setMessages((prev) => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last && last.role === 'assistant') {
            updated[updated.length - 1] = { ...last, content: last.content + content }
          }
          return updated
        })
      },
      onError: (content) => {
        setMessages((prev) => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last && last.role === 'assistant') {
            updated[updated.length - 1] = { ...last, content: last.content + '\n\n⚠️ ' + content }
          }
          return updated
        })
      },
      onDone: (references: Reference[], convId: string) => {
        setMessages((prev) => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last && last.role === 'assistant') {
            updated[updated.length - 1] = { ...last, references }
          }
          return updated
        })
        if (convId && !conversationId) {
          setConversationId(convId)
        }
      },
      onFatalError: () => {
        setMessages((prev) => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last && last.role === 'assistant') {
            updated[updated.length - 1] = { ...last, content: '错误：无法连接到后端服务' }
          }
          return updated
        })
      },
    })

    abortControllerRef.current = controller
    requestInFlight.current = false
  }, [messages, conversationId, setMessages, setConversationId])

  const clearMessages = useCallback(() => {
    cancelStream()
    setMessages([])
    localStorage.removeItem(STORAGE_KEY)
    setConversationId(null)
  }, [setMessages, setConversationId, cancelStream])

  const exportMarkdown = useCallback(() => {
    if (messages.length === 0) return
    const lines: string[] = ['# Nova-RAG 会话导出\n']
    for (const msg of messages) {
      if (msg.role === 'user') {
        lines.push(`### 用户提问\n\n${msg.content}\n\n`)
      } else {
        lines.push(`### AI 回答\n\n${msg.content}\n\n`)
        if (msg.references && msg.references.length > 0) {
          lines.push('**参考来源**：\n')
          for (const ref of msg.references) {
            lines.push(`- [${ref.index}] ${ref.doc_id}\n`)
          }
          lines.push('\n')
        }
      }
    }
    const blob = new Blob(lines, { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    a.href = url
    a.download = `Nova-RAG-会话导出-${ts}.md`
    a.click()
    URL.revokeObjectURL(url)
  }, [messages])

  return {
    messages,
    sendMessage,
    clearMessages,
    exportMarkdown,
    cancelStream,
  }
}
