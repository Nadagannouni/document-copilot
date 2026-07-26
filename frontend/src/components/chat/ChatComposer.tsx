import { useState, type FormEvent } from 'react'
import { Loader2, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'

type ChatComposerProps = {
  disabled: boolean
  onSubmit: (message: string) => Promise<void>
}

export function ChatComposer({ disabled, onSubmit }: ChatComposerProps) {
  const [message, setMessage] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nextMessage = message.trim()
    if (!nextMessage || disabled) {
      return
    }

    setMessage('')
    await onSubmit(nextMessage)
  }

  return (
    <form className="border-t bg-background p-3" onSubmit={handleSubmit}>
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <textarea
          className="min-h-20 flex-1 resize-none rounded-md border bg-background px-3 py-2 text-sm leading-6 outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30 disabled:opacity-50"
          disabled={disabled}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Ask about revenue, margins, risk factors, or year-over-year changes..."
          value={message}
        />
        <Button disabled={disabled || !message.trim()} size="icon-lg" type="submit">
          {disabled ? <Loader2 aria-hidden="true" className="animate-spin" /> : <Send aria-hidden="true" />}
        </Button>
      </div>
    </form>
  )
}
