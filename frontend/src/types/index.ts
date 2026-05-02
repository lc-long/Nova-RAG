export interface DocItem {
  id: string
  name: string
  size?: string
  status?: string
  date?: string
}

export interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface Reference {
  index: number
  doc_id: string
  source_doc?: string
  page_number?: number
  content: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  reasoning: string
  thoughts: string[]
  references?: Reference[]
}

export interface ChatMessage {
  role: string
  content: string
}

export interface SSEEvent {
  type?: 'thought' | 'reasoning' | 'answer' | 'error'
  content?: string
  done?: boolean
  references?: Reference[]
  conversation_id?: string
}
