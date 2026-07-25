import { env } from '@/lib/env'
import { http } from '@/lib/http'

export type ChatRole = 'user' | 'assistant' | 'system'

export type ChatThread = {
  id: string
  title: string
  createdAt: string
  updatedAt: string
}

export type MessageCitation = {
  id: string
  documentChunkId: string
  citationIndex: number
  excerpt: string
  metadata: Record<string, unknown>
}

export type ChatMessage = {
  id: string
  threadId: string
  role: ChatRole
  content: string
  createdAt: string
  messageJson: unknown
  citations: MessageCitation[]
}

export type CreateThreadRequest = {
  title?: string
}

export type ChatStreamRequest = {
  threadId: string
  messages: unknown[]
}

type ListThreadsResponse = {
  threads: ChatThreadWire[]
}

type ListMessagesResponse = {
  messages: ChatMessageWire[]
}

type ChatThreadWire = {
  id: string
  title: string
  created_at: string
  updated_at: string
}

type MessageCitationWire = {
  id: string
  document_chunk_id: string
  citation_index: number
  excerpt: string
  metadata: Record<string, unknown>
}

type ChatMessageWire = {
  id: string
  thread_id: string
  role: ChatRole
  content: string
  created_at: string
  message_json: unknown
  citations?: MessageCitationWire[]
}

function mapThread(thread: ChatThreadWire): ChatThread {
  return {
    id: thread.id,
    title: thread.title,
    createdAt: thread.created_at,
    updatedAt: thread.updated_at,
  }
}

function mapCitation(citation: MessageCitationWire): MessageCitation {
  return {
    id: citation.id,
    documentChunkId: citation.document_chunk_id,
    citationIndex: citation.citation_index,
    excerpt: citation.excerpt,
    metadata: citation.metadata,
  }
}

function mapMessage(message: ChatMessageWire): ChatMessage {
  return {
    id: message.id,
    threadId: message.thread_id,
    role: message.role,
    content: message.content,
    createdAt: message.created_at,
    messageJson: message.message_json,
    citations: message.citations?.map(mapCitation) ?? [],
  }
}

export const api = {
  createThread: (body: CreateThreadRequest = {}) =>
    http.post<ChatThreadWire>('/chat/threads', body).then(mapThread),
  listMessages: async (threadId: string) => {
    const response = await http.get<ListMessagesResponse>(
      `/chat/threads/${threadId}/messages`,
    )
    return response.messages.map(mapMessage)
  },
  listThreads: async () => {
    const response = await http.get<ListThreadsResponse>('/chat/threads')
    return response.threads.map(mapThread)
  },
  streamChatUrl: `${env.apiBaseUrl}/chat/stream`,
}
