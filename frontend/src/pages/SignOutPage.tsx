import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/lib/use-auth'

export function SignOutPage() {
  const { signOut } = useAuth()
  const [isDone, setIsDone] = useState(false)

  useEffect(() => {
    async function endSession() {
      await signOut()
      setIsDone(true)
    }

    void endSession()
  }, [signOut])

  if (isDone) {
    return <Navigate to="/sign-in" replace />
  }

  return (
    <main className="grid min-h-svh place-items-center px-6">
      <p className="text-sm text-muted-foreground">Signing out...</p>
    </main>
  )
}
