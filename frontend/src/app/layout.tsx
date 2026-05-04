import type { Metadata } from 'next'
import './globals.css'
import { Sidebar } from '@/features/layout/sidebar'
import { Header } from '@/features/layout/header'

export const metadata: Metadata = {
  title: 'Business Analysis Companion',
  description: 'AI-powered business analysis workspace',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto bg-background">
          {children}
        </main>
      </div>
    </div>
  )
}
