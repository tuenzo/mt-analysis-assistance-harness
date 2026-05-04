import { Clock } from 'lucide-react'

export default function TimelinePage() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center p-8">
      <div className="p-4 bg-primary/10 rounded-full mb-4">
        <Clock className="h-8 w-8 text-primary" />
      </div>
      <h2 className="text-xl font-semibold mb-2">Run Timeline</h2>
      <p className="text-muted-foreground max-w-md">
        View the history of analysis runs and their status.
      </p>
    </div>
  )
}
