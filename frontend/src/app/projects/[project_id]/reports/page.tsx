import { FileText } from 'lucide-react'

export default function ReportsPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center p-8">
      <div className="p-4 bg-primary/10 rounded-full mb-4">
        <FileText className="h-8 w-8 text-primary" />
      </div>
      <h2 className="text-xl font-semibold mb-2">Report Studio</h2>
      <p className="text-muted-foreground max-w-md">
        Generate and manage analysis reports.
      </p>
    </div>
  )
}
