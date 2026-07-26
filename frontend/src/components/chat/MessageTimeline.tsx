import { AlertTriangle, Loader2, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { MessageCitation } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { DisplayMessage, SelectedCitation } from '@/components/chat/types'

type MessageTimelineProps = {
  error: string | null
  isLoading: boolean
  messages: DisplayMessage[]
  onCitationSelect: (selection: SelectedCitation) => void
  onRetry: () => void
}

export function MessageTimeline({
  error,
  isLoading,
  messages,
  onCitationSelect,
  onRetry,
}: MessageTimelineProps) {
  if (isLoading) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center text-sm text-muted-foreground">
        <Loader2 aria-hidden="true" className="mr-2 size-4 animate-spin" />
        Loading messages
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center px-6">
        <div className="max-w-md space-y-3 text-center">
          <p className="text-sm text-destructive">{error}</p>
          <Button onClick={onRetry} type="button" variant="outline">
            <RefreshCw aria-hidden="true" data-icon="inline-start" />
            Retry
          </Button>
        </div>
      </div>
    )
  }

  if (messages.length === 0) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center px-6">
        <div className="max-w-xl text-center">
          <p className="text-sm font-medium text-foreground">Ask a filing question to begin.</p>
          <p className="mt-2 text-sm text-muted-foreground">
            The assistant is stubbed in this phase; citations and grounded answers arrive after retrieval is connected.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
      <div className="mx-auto flex max-w-3xl flex-col gap-3">
        {messages.map((message) => (
          <article
            className={cn(
              'rounded-md border px-3 py-2 text-sm',
              message.role === 'user'
                ? 'ml-auto max-w-[82%] bg-primary text-primary-foreground'
                : 'mr-auto w-full bg-card text-card-foreground',
            )}
            key={message.id}
          >
            <div className="mb-1 flex items-center justify-between gap-3">
              <span className="text-xs font-medium opacity-75">
                {message.role === 'user' ? 'You' : 'Assistant'}
              </span>
              {message.isStreaming ? (
                <Loader2 aria-hidden="true" className="size-3.5 animate-spin opacity-70" />
              ) : null}
            </div>
            {isUnsupportedAnswer(message.content) ? (
              <div className="mb-2 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-2 text-destructive">
                <AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
                <span className="text-xs font-medium">Not enough evidence</span>
              </div>
            ) : null}
            <p className="whitespace-pre-wrap leading-6">{message.content || '...'}</p>
            {message.role === 'assistant' ? (
              <CitationChips
                citations={message.citations}
                message={message}
                onCitationSelect={onCitationSelect}
              />
            ) : null}
          </article>
        ))}
      </div>
    </div>
  )
}

function CitationChips({
  citations,
  message,
  onCitationSelect,
}: {
  citations: MessageCitation[]
  message: DisplayMessage
  onCitationSelect: (selection: SelectedCitation) => void
}) {
  if (citations.length === 0) {
    return <p className="mt-3 text-xs text-muted-foreground">No citations attached yet.</p>
  }

  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {citations.map((citation) => (
        <Button
          key={citation.id}
          onClick={() => onCitationSelect({ citation, message })}
          size="xs"
          type="button"
          variant="outline"
        >
          Source {citation.citationIndex + 1}
        </Button>
      ))}
    </div>
  )
}

function isUnsupportedAnswer(content: string): boolean {
  return content.toLowerCase().includes('not enough evidence')
}
