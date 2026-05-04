import { LayoutDashboard } from 'lucide-react'

export default function DashboardPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center p-8">
      <div className="p-4 bg-primary/10 rounded-full mb-4">
        <LayoutDashboard className="h-8 w-8 text-primary" />
      </div>
      <h2 className="text-xl font-semibold mb-2">Results Dashboard</h2>
      <p className="text-muted-foreground max-w-md">
        View analysis results, charts, and metrics.
      </p>
    </div>
  )
}
