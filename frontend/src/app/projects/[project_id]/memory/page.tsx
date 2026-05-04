import { Brain } from 'lucide-react'

export default function MemoryPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center p-8">
      <div className="p-4 bg-primary/10 rounded-full mb-4">
        <Brain className="h-8 w-8 text-primary" />
      </div>
      <h2 className="text-xl font-semibold mb-2">Memory Review</h2>
      <p className="text-muted-foreground max-w-md">
        Review and approve memory candidates for persistence.
      </p>
    </div>
  )
}
