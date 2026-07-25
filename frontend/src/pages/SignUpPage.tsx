import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { UserPlus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/use-auth'

export function SignUpPage() {
  const navigate = useNavigate()
  const { isAuthenticated, signUp } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [isConfirmationRequired, setIsConfirmationRequired] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (isAuthenticated) {
    return <Navigate to="/chat" replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setIsConfirmationRequired(false)
    setIsSubmitting(true)

    const formData = new FormData(event.currentTarget)
    const email = String(formData.get('email') ?? '')
    const password = String(formData.get('password') ?? '')

    try {
      const confirmationRequired = await signUp(email, password)

      if (confirmationRequired) {
        setIsConfirmationRequired(true)
      } else {
        navigate('/chat', { replace: true })
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Sign up failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="grid min-h-svh place-items-center bg-background px-6 py-10">
      <section className="w-full max-w-sm rounded-lg border bg-card p-6 text-card-foreground shadow-sm">
        <div className="mb-6">
          <p className="text-sm font-medium text-muted-foreground">Document Copilot</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-normal">Create account</h1>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2 text-left">
            <label className="text-sm font-medium" htmlFor="email">
              Email
            </label>
            <input
              autoComplete="email"
              className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              id="email"
              name="email"
              required
              type="email"
            />
          </div>

          <div className="space-y-2 text-left">
            <label className="text-sm font-medium" htmlFor="password">
              Password
            </label>
            <input
              autoComplete="new-password"
              className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              id="password"
              minLength={6}
              name="password"
              required
              type="password"
            />
          </div>

          {error ? (
            <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-left text-sm text-destructive">
              {error}
            </p>
          ) : null}

          {isConfirmationRequired ? (
            <p className="rounded-md border bg-muted px-3 py-2 text-left text-sm text-muted-foreground">
              Check your email to confirm the account, then sign in.
            </p>
          ) : null}

          <Button className="w-full" disabled={isSubmitting} type="submit">
            <UserPlus aria-hidden="true" data-icon="inline-start" />
            {isSubmitting ? 'Creating...' : 'Create account'}
          </Button>
        </form>

        <p className="mt-5 text-center text-sm text-muted-foreground">
          Already have an account?{' '}
          <Link className="font-medium text-foreground underline-offset-4 hover:underline" to="/sign-in">
            Sign in
          </Link>
        </p>
      </section>
    </main>
  )
}
