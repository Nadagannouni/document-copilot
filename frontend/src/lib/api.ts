import { env } from '@/lib/env'
import { http } from '@/lib/http'
import { getAccessToken } from '@/lib/supabase'

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

export type ChatStreamHandlers = {
  onComplete?: (content: string) => void
  onDelta: (text: string) => void
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
  streamChat: (body: ChatStreamRequest, handlers: ChatStreamHandlers, signal?: AbortSignal) =>
    streamChat(body, handlers, signal),
  streamChatUrl: `${env.apiBaseUrl}/chat/stream`,
}

async function streamChat(
  body: ChatStreamRequest,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const token = await getAccessToken()
  const headers = new Headers({
    Accept: 'text/event-stream',
    'Content-Type': 'application/json',
  })

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(api.streamChatUrl, {
    body: JSON.stringify(body),
    headers,
    method: 'POST',
    signal,
  })

  if (!response.ok) {
    throw new Error(await response.text())
  }

  if (!response.body) {
    throw new Error('Chat stream did not include a response body')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''

    for (const event of events) {
      handleStreamEvent(event, handlers)
    }
  }

  if (buffer) {
    handleStreamEvent(buffer, handlers)
  }
}

function handleStreamEvent(eventText: string, handlers: ChatStreamHandlers): void {
  const lines = eventText.split('\n')
  const event = lines.find((line) => line.startsWith('event: '))?.slice(7)
  const dataLine = lines.find((line) => line.startsWith('data: '))
  const payload = parseStreamPayload(dataLine?.slice(6))

  if (event === 'delta' && typeof payload.text === 'string') {
    handlers.onDelta(payload.text)
  }

  if (event === 'complete' && typeof payload.content === 'string') {
    handlers.onComplete?.(payload.content)
  }

  if (event === 'error') {
    throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Chat stream failed')
  }
}

function parseStreamPayload(data: string | undefined): Record<string, unknown> {
  if (!data) {
    return {}
  }

  const parsed = JSON.parse(data)
  return parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : {}
}
