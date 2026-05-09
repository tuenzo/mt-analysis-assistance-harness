import type { Metadata } from 'next'
import './globals.css'
import { Sidebar } from '@/features/layout/sidebar'
import { Header } from '@/features/layout/header'
import { MainContent } from '@/features/layout/main-content'

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
    <html lang="zh">
      <body>
        <div className="flex h-screen overflow-hidden bg-background">
          <Sidebar />
          <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
            <Header />
            <MainContent>
              {children}
            </MainContent>
          </div>
        </div>
      </body>
    </html>
  )
}
