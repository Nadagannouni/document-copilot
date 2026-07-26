import { Navigate, Route, Routes } from 'react-router-dom'
import { RequireAuth } from '@/components/auth/RequireAuth'
import { AuthProvider } from '@/lib/auth'
import { ChatPage } from '@/pages/ChatPage'
import { SignInPage } from '@/pages/SignInPage'
import { SignOutPage } from '@/pages/SignOutPage'
import { SignUpPage } from '@/pages/SignUpPage'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<Navigate to="/chat" replace />} path="/" />
        <Route element={<SignInPage />} path="/sign-in" />
        <Route element={<SignUpPage />} path="/sign-up" />
        <Route element={<RequireAuth />}>
          <Route element={<ChatPage />} path="/chat" />
          <Route element={<ChatPage />} path="/chat/:threadId" />
          <Route element={<SignOutPage />} path="/sign-out" />
        </Route>
        <Route element={<Navigate to="/chat" replace />} path="*" />
      </Routes>
    </AuthProvider>
  )
}

export default App
