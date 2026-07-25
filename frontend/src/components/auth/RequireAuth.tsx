import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/lib/use-auth'

export function RequireAuth() {
  const location = useLocation()
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <main className="grid min-h-svh place-items-center px-6">
        <p className="text-sm text-muted-foreground">Checking session...</p>
      </main>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/sign-in" replace state={{ from: location }} />
  }

  return <Outlet />
}
