import { Link } from 'react-router-dom'
import { Loader2, MessageSquare, Plus, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { ChatThread } from '@/lib/api'
import { cn } from '@/lib/utils'

type ThreadListProps = {
  error: string | null
  isCreating: boolean
  isLoading: boolean
  onCreateThread: () => void
  onRetry: () => void
  selectedThreadId: string | null
  threads: ChatThread[]
}

export function ThreadList({
  error,
  isCreating,
  isLoading,
  onCreateThread,
  onRetry,
  selectedThreadId,
  threads,
}: ThreadListProps) {
  return (
    <aside className="flex min-h-0 flex-col border-r bg-sidebar">
      <div className="flex h-14 items-center justify-between gap-3 border-b px-3">
        <div>
          <p className="text-xs font-medium text-muted-foreground">Workspace</p>
          <p className="text-sm font-semibold text-foreground">Threads</p>
        </div>
        <Button
          aria-label="New thread"
          disabled={isCreating}
          onClick={onCreateThread}
          size="icon-sm"
          type="button"
        >
          {isCreating ? <Loader2 aria-hidden="true" className="animate-spin" /> : <Plus aria-hidden="true" />}
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <div className="flex items-center gap-2 px-2 py-3 text-sm text-muted-foreground">
            <Loader2 aria-hidden="true" className="size-4 animate-spin" />
            Loading threads
          </div>
        ) : null}

        {error ? (
          <div className="space-y-2 px-2 py-3">
            <p className="text-sm text-destructive">{error}</p>
            <Button onClick={onRetry} size="sm" type="button" variant="outline">
              <RefreshCw aria-hidden="true" data-icon="inline-start" />
              Retry
            </Button>
          </div>
        ) : null}

        {!isLoading && !error && threads.length === 0 ? (
          <div className="px-2 py-4 text-sm text-muted-foreground">
            No threads yet. Start one when you are ready to ask about filings.
          </div>
        ) : null}

        <nav className="space-y-1">
          {threads.map((thread) => (
            <Link
              className={cn(
                'flex min-h-11 items-center gap-2 rounded-md px-2 py-2 text-sm text-sidebar-foreground hover:bg-sidebar-accent',
                selectedThreadId === thread.id && 'bg-sidebar-accent text-sidebar-accent-foreground',
              )}
              key={thread.id}
              to={`/chat/${thread.id}`}
            >
              <MessageSquare aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
              <span className="min-w-0 flex-1 truncate">{thread.title}</span>
            </Link>
          ))}
        </nav>
      </div>
    </aside>
  )
}
