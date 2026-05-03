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
  score?: number
  score_type?: 'vector' | 'bm25' | 'combined' | 'rerank'
  vector_score?: number
  bm25_score?: number | null
  chunk_index?: number
  parent_chunk_index?: string
}

export interface ChunkPosition {
  index: number
  chunk_id: string
  content: string
  start_pos: number
  end_pos: number
  order: number
  page_number: number
}

export interface DocContent {
  doc_id: string
  name: string
  status: string
  content: string
  chunks: ChunkPosition[]
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
