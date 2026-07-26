import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { SelectedCitation } from '@/components/chat/types'

type SourcePanelProps = {
  onClose: () => void
  selection: SelectedCitation | null
}

export function SourcePanel({ onClose, selection }: SourcePanelProps) {
  return (
    <aside
      className={
        selection
          ? 'fixed inset-x-3 bottom-3 z-20 flex max-h-[70svh] flex-col rounded-md border bg-background shadow-lg xl:static xl:inset-auto xl:z-auto xl:max-h-none xl:rounded-none xl:border-y-0 xl:border-r-0 xl:shadow-none'
          : 'hidden min-h-0 border-l bg-background xl:flex xl:flex-col'
      }
    >
      <div className="flex h-14 items-center justify-between gap-3 border-b px-3">
        <div>
          <p className="text-xs font-medium text-muted-foreground">Evidence</p>
          <p className="text-sm font-semibold text-foreground">Source passage</p>
        </div>
        {selection ? (
          <Button aria-label="Close source" onClick={onClose} size="icon-sm" type="button" variant="ghost">
            <X aria-hidden="true" />
          </Button>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {!selection ? (
          <p className="text-sm text-muted-foreground">
            Select a citation chip to inspect filing metadata and the supporting excerpt.
          </p>
        ) : (
          <div className="space-y-4">
            <div>
              <p className="text-xs font-medium uppercase text-muted-foreground">Excerpt</p>
              <p className="mt-2 whitespace-pre-wrap rounded-md border bg-muted/40 p-3 text-sm leading-6">
                {selection.citation.excerpt}
              </p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase text-muted-foreground">Metadata</p>
              <dl className="mt-2 space-y-2 text-sm">
                {Object.entries(selection.citation.metadata).map(([key, value]) => (
                  <div className="grid grid-cols-[7rem_1fr] gap-2" key={key}>
                    <dt className="truncate text-muted-foreground">{key}</dt>
                    <dd className="min-w-0 break-words text-foreground">{formatMetadata(value)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}

function formatMetadata(value: unknown): string {
  if (typeof value === 'string') {
    return value
  }

  return JSON.stringify(value)
}
