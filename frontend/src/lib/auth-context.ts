import { createContext } from 'react'
import type { Session, User } from '@supabase/supabase-js'

export type AuthContextValue = {
  isAuthenticated: boolean
  isLoading: boolean
  session: Session | null
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  signUp: (email: string, password: string) => Promise<boolean>
  user: User | null
}

export const AuthContext = createContext<AuthContextValue | null>(null)
