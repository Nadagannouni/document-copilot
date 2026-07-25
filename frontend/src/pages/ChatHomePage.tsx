import { Link } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/use-auth'

export function ChatHomePage() {
  const { user } = useAuth()

  return (
    <main className="min-h-svh bg-background">
      <header className="border-b px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Document Copilot</p>
            <h1 className="text-xl font-semibold tracking-normal">Chat</h1>
          </div>
          <Button asChild variant="outline">
            <Link to="/sign-out">
              <LogOut aria-hidden="true" data-icon="inline-start" />
              Sign out
            </Link>
          </Button>
        </div>
      </header>

      <section className="mx-auto max-w-5xl px-6 py-8">
        <div className="rounded-lg border bg-card p-6 text-card-foreground">
          <p className="text-sm text-muted-foreground">{user?.email}</p>
          <h2 className="mt-2 text-lg font-semibold tracking-normal">Ready for chat routes</h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Thread loading and message rendering come next in Phase 6 once the backend chat endpoints are in place.
          </p>
        </div>
      </section>
    </main>
  )
}
