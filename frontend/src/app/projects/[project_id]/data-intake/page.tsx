import { Database } from 'lucide-react'

export default function DataIntakePage() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center p-8">
      <div className="p-4 bg-primary/10 rounded-full mb-4">
        <Database className="h-8 w-8 text-primary" />
      </div>
      <h2 className="text-xl font-semibold mb-2">Data Intake</h2>
      <p className="text-muted-foreground max-w-md">
        Upload your CSV files to begin analysis.
        Supported files: order_info.csv, exposure_info.csv, activity_timeline.csv
      </p>
    </div>
  )
}
