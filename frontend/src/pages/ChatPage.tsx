import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { LogOut, PanelLeft, RefreshCw } from 'lucide-react'
import { ChatComposer } from '@/components/chat/ChatComposer'
import { MessageTimeline } from '@/components/chat/MessageTimeline'
import { SourcePanel } from '@/components/chat/SourcePanel'
import { ThreadList } from '@/components/chat/ThreadList'
import type { DisplayMessage, SelectedCitation } from '@/components/chat/types'
import { Button } from '@/components/ui/button'
import { api, type ChatMessage, type ChatThread } from '@/lib/api'
import { useAuth } from '@/lib/use-auth'

type RouteParams = {
  threadId?: string
}

export function ChatPage() {
  const { threadId = null } = useParams<RouteParams>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [threads, setThreads] = useState<ChatThread[]>([])
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [selectedCitation, setSelectedCitation] = useState<SelectedCitation | null>(null)
  const [threadError, setThreadError] = useState<string | null>(null)
  const [messageError, setMessageError] = useState<string | null>(null)
  const [sendError, setSendError] = useState<string | null>(null)
  const [isCreatingThread, setIsCreatingThread] = useState(false)
  const [isLoadingThreads, setIsLoadingThreads] = useState(true)
  const [isLoadingMessages, setIsLoadingMessages] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)

  const selectedThread = useMemo(
    () => threads.find((thread) => thread.id === threadId) ?? null,
    [threadId, threads],
  )

  const loadThreads = useCallback(async () => {
    setIsLoadingThreads(true)
    setThreadError(null)

    try {
      setThreads(await api.listThreads())
    } catch (error) {
      setThreadError(errorMessage(error, 'Could not load threads'))
    } finally {
      setIsLoadingThreads(false)
    }
  }, [])

  const loadMessages = useCallback(async (nextThreadId: string) => {
    setIsLoadingMessages(true)
    setMessageError(null)
    setSelectedCitation(null)

    try {
      setMessages(await api.listMessages(nextThreadId))
    } catch (error) {
      setMessageError(errorMessage(error, 'Could not load messages'))
    } finally {
      setIsLoadingMessages(false)
    }
  }, [])

  useEffect(() => {
    void loadThreads()
  }, [loadThreads])

  useEffect(() => {
    if (!threadId) {
      setMessages([])
      setMessageError(null)
      setSelectedCitation(null)
      return
    }

    void loadMessages(threadId)
  }, [loadMessages, threadId])

  async function createThread(title?: string): Promise<ChatThread> {
    setIsCreatingThread(true)
    setThreadError(null)

    try {
      const thread = await api.createThread({ title })
      setThreads((currentThreads) => [thread, ...currentThreads])
      navigate(`/chat/${thread.id}`)
      return thread
    } catch (error) {
      setThreadError(errorMessage(error, 'Could not create thread'))
      throw error
    } finally {
      setIsCreatingThread(false)
    }
  }

  async function handleCreateThread() {
    try {
      await createThread()
    } catch {
      return
    }
  }

  async function handleSend(content: string) {
    setSendError(null)

    let activeThread: ChatThread
    try {
      activeThread = selectedThread ?? (await createThread(titleFromMessage(content)))
    } catch (error) {
      setSendError(errorMessage(error, 'Could not create thread'))
      return
    }

    const userMessage = temporaryMessage(activeThread.id, 'user', content)
    const assistantMessage = temporaryMessage(activeThread.id, 'assistant', '', true)
    const outgoingMessages = [...messages, userMessage].map((message) => ({
      content: message.content,
      role: message.role,
    }))

    setMessages((currentMessages) => [...currentMessages, userMessage, assistantMessage])
    setIsStreaming(true)

    try {
      await api.streamChat(
        {
          messages: outgoingMessages,
          threadId: activeThread.id,
        },
        {
          onDelta: (text) => {
            setMessages((currentMessages) =>
              currentMessages.map((message) =>
                message.id === assistantMessage.id
                  ? { ...message, content: `${message.content}${text}` }
                  : message,
              ),
            )
          },
        },
      )
      await loadMessages(activeThread.id)
      void loadThreads()
    } catch (error) {
      setSendError(errorMessage(error, 'Could not send message'))
      setMessages((currentMessages) =>
        currentMessages.map((message) =>
          message.id === assistantMessage.id ? { ...message, isStreaming: false } : message,
        ),
      )
    } finally {
      setIsStreaming(false)
    }
  }

  return (
    <main className="grid h-svh grid-cols-1 overflow-hidden bg-background text-foreground lg:grid-cols-[18rem_1fr] xl:grid-cols-[18rem_1fr_22rem]">
      <ThreadList
        error={threadError}
        isCreating={isCreatingThread}
        isLoading={isLoadingThreads}
        onCreateThread={handleCreateThread}
        onRetry={loadThreads}
        selectedThreadId={threadId}
        threads={threads}
      />

      <section className="flex min-h-0 flex-col">
        <header className="flex h-14 items-center justify-between gap-3 border-b px-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <PanelLeft aria-hidden="true" className="size-4 text-muted-foreground lg:hidden" />
              <p className="truncate text-sm font-semibold text-foreground">
                {selectedThread?.title ?? 'Document Copilot'}
              </p>
            </div>
            <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
          </div>
          <div className="flex items-center gap-2">
            {threadId ? (
              <Button onClick={() => loadMessages(threadId)} size="icon-sm" type="button" variant="outline">
                <RefreshCw aria-hidden="true" />
              </Button>
            ) : null}
            <Button asChild size="sm" variant="outline">
              <Link to="/sign-out">
                <LogOut aria-hidden="true" data-icon="inline-start" />
                Sign out
              </Link>
            </Button>
          </div>
        </header>

        {threadId ? (
          <>
            <MessageTimeline
              error={messageError}
              isLoading={isLoadingMessages}
              messages={messages}
              onCitationSelect={setSelectedCitation}
              onRetry={() => loadMessages(threadId)}
            />
            {sendError ? (
              <div className="border-t bg-destructive/10 px-4 py-2 text-sm text-destructive">{sendError}</div>
            ) : null}
            <ChatComposer disabled={isStreaming || isLoadingMessages} onSubmit={handleSend} />
          </>
        ) : (
          <div className="flex min-h-0 flex-1 items-center justify-center px-6">
            <div className="max-w-lg text-center">
              <p className="text-sm font-medium text-foreground">Select a thread or start a new one.</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Phase 6 connects the chat surface to the stubbed backend stream so the full workflow can be exercised.
              </p>
              <Button className="mt-4" disabled={isCreatingThread} onClick={handleCreateThread} type="button">
                Start thread
              </Button>
            </div>
          </div>
        )}
      </section>

      <SourcePanel onClose={() => setSelectedCitation(null)} selection={selectedCitation} />
    </main>
  )
}

function temporaryMessage(
  threadId: string,
  role: ChatMessage['role'],
  content: string,
  isStreaming = false,
): DisplayMessage {
  return {
    citations: [],
    content,
    createdAt: new Date().toISOString(),
    id: `temp-${crypto.randomUUID()}`,
    isStreaming,
    messageJson: null,
    role,
    threadId,
  }
}

function titleFromMessage(message: string): string {
  return message.length > 64 ? `${message.slice(0, 61)}...` : message
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback
}
