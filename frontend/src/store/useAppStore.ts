import { create } from 'zustand'
import type { DocItem, Conversation, Message } from '../types'
import * as api from '../lib/api'

interface AppState {
  // Documents
  docs: DocItem[]
  currentDoc: string | null
  previewDocId: string | null
  loadingDocs: boolean

  // Conversations
  conversations: Conversation[]
  conversationId: string | null
  loadingConversations: boolean

  // Messages
  messages: Message[]

  // Actions
  setCurrentDoc: (id: string | null) => void
  setPreviewDocId: (id: string | null) => void
  setConversationId: (id: string | null) => void
  setMessages: (msgs: Message[] | ((prev: Message[]) => Message[])) => void

  // Async actions
  loadDocs: () => Promise<void>
  loadConversations: () => Promise<void>
  loadConversationMessages: (id: string) => Promise<void>
  uploadDocuments: (files: File[]) => Promise<{ succeeded: number; failed: string[] }>
  removeDoc: (id: string) => Promise<void>
  removeDocs: (ids: string[]) => Promise<void>
  removeConversation: (id: string) => Promise<void>
}

export const useAppStore = create<AppState>((set) => ({
  // Initial state
  docs: [],
  currentDoc: null,
  previewDocId: null,
  loadingDocs: false,
  conversations: [],
  conversationId: null,
  loadingConversations: false,
  messages: [],

  // Sync actions
  setCurrentDoc: (id) => set({ currentDoc: id }),
  setPreviewDocId: (id) => set({ previewDocId: id }),
  setConversationId: (id) => set({ conversationId: id }),
  setMessages: (msgs) => set((state) => ({
    messages: typeof msgs === 'function' ? msgs(state.messages) : msgs,
  })),

  // Async actions
  loadDocs: async () => {
    set({ loadingDocs: true })
    try {
      const docs = await api.fetchDocs()
      set({ docs })
    } catch {
      // silent
    } finally {
      set({ loadingDocs: false })
    }
  },

  loadConversations: async () => {
    try {
      const conversations = await api.fetchConversations()
      set({ conversations })
    } catch {
      // silent
    }
  },

  loadConversationMessages: async (id: string) => {
    try {
      const data = await api.fetchConversation(id)
      const msgs: Message[] = data.messages.map((m) => ({
        id: m.id,
        role: m.role as 'user' | 'assistant',
        content: m.content,
        reasoning: m.reasoning || '',
        thoughts: [],
        references: m.sources || [],
      }))
      set({ messages: msgs })
    } catch {
      set({ messages: [] })
    }
  },

  uploadDocuments: async (files: File[]) => {
    const results = await Promise.allSettled(files.map((f) => api.uploadDoc(f)))
    const succeeded: DocItem[] = []
    const failed: string[] = []
    results.forEach((r, i) => {
      if (r.status === 'fulfilled') succeeded.push(r.value)
      else failed.push(files[i].name)
    })
    if (succeeded.length > 0) {
      set((state) => ({ docs: [...succeeded, ...state.docs] }))
    }
    return { succeeded: succeeded.length, failed }
  },

  removeDoc: async (id: string) => {
    await api.deleteDoc(id)
    set((state) => ({
      docs: state.docs.filter((d) => d.id !== id),
    }))
  },

  removeDocs: async (ids: string[]) => {
    await api.batchDeleteDocs(ids)
    const idSet = new Set(ids)
    set((state) => ({
      docs: state.docs.filter((d) => !idSet.has(d.id)),
    }))
  },

  removeConversation: async (id: string) => {
    await api.deleteConversation(id)
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== id),
      conversationId: state.conversationId === id ? null : state.conversationId,
    }))
  },
}))
