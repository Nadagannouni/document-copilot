import type { ChatMessage, MessageCitation } from '@/lib/api'

export type DisplayMessage = ChatMessage & {
  isStreaming?: boolean
}

export type SelectedCitation = {
  citation: MessageCitation
  message: DisplayMessage
}
