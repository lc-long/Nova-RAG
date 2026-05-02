import axios from 'axios'
import { API_BASE_URL } from '../config'
import type { DocItem, Conversation, Reference, SSEEvent } from '../types'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
})

// ── Documents API ──

export async function fetchDocs(): Promise<DocItem[]> {
  const res = await api.get('/docs')
  return res.data.map((d: { id: string; name: string; size?: string; status?: string }) => ({
    id: d.id,
    name: d.name,
    size: d.size,
    status: d.status,
  }))
}

export async function uploadDoc(file: File): Promise<DocItem> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await api.post('/docs/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
  return {
    id: res.data.id || Date.now().toString(),
    name: file.name,
    size: `${(file.size / 1024).toFixed(0)}KB`,
    status: 'processing',
  }
}

export async function deleteDoc(docId: string): Promise<void> {
  await api.delete(`/docs/${docId}`)
}

export async function batchDeleteDocs(docIds: string[]): Promise<void> {
  await api.post('/docs/batch-delete', { doc_ids: docIds })
}

// ── Conversations API ──

export async function fetchConversations(): Promise<Conversation[]> {
  const res = await api.get('/conversations')
  return res.data
}

interface ApiMessage {
  id: string
  role: string
  content: string
  reasoning: string
  sources: Reference[]
}

export async function fetchConversation(id: string): Promise<Conversation & { messages: ApiMessage[] }> {
  const res = await api.get(`/conversations/${id}`)
  return res.data
}

export async function deleteConversation(id: string): Promise<void> {
  await api.delete(`/conversations/${id}`)
}

// ── Chat SSE Streaming ──

export interface StreamCallbacks {
  onThought: (content: string) => void
  onReasoning: (content: string) => void
  onAnswer: (content: string) => void
  onError: (content: string) => void
  onDone: (references: Reference[], conversationId: string) => void
  onFatalError: (error: Error) => void
}

export function streamChat(
  messages: { role: string; content: string }[],
  docIds: string[] | null,
  conversationId: string | null,
  callbacks: StreamCallbacks,
): AbortController {
  const controller = new AbortController()

  const doFetch = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages,
          stream: true,
          doc_id: null,
          doc_ids: docIds,
          conversation_id: conversationId,
        }),
        signal: controller.signal,
      })

      if (!response.ok) throw new Error(`HTTP error ${response.status}`)

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) throw new Error('No reader available')

      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // Handle JSON that may span multiple chunks
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data:')) continue
          const data = line.slice(5).trim()
          if (data === '[DONE]') continue

          let parsed: SSEEvent
          try {
            parsed = JSON.parse(data)
          } catch {
            continue
          }

          if (parsed.type === 'thought' && parsed.content) callbacks.onThought(parsed.content)
          if (parsed.type === 'reasoning' && parsed.content) callbacks.onReasoning(parsed.content)
          if (parsed.type === 'answer' && parsed.content) callbacks.onAnswer(parsed.content)
          if (parsed.type === 'error' && parsed.content) callbacks.onError(parsed.content)
          if (parsed.done) {
            callbacks.onDone(parsed.references || [], parsed.conversation_id || '')
          }
        }
      }
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        callbacks.onFatalError(error as Error)
      }
    }
  }

  doFetch()
  return controller
}
