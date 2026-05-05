'use client'

import type { JobStatus } from '@/store/agent-store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CheckCircle, Circle, Loader2 } from 'lucide-react'

const PIPELINE_STEPS = [
  'Data Intake',
  'Schema & Quality',
  'Panel Build',
  'Descriptive Diagnostics',
  'Causal Direction',
  'Increment Decomposition',
  'Dose Response',
  'Uplift & Strategy',
]

interface JobProgressIndicatorProps {
  job: JobStatus | null
  jobs: Record<string, JobStatus>
}

export function JobProgressIndicator({ job, jobs }: JobProgressIndicatorProps) {
  const activeJob = job || Object.values(jobs)[0]

  if (!activeJob) {
    return null
  }

  const currentStepIndex = Math.floor(activeJob.progress * PIPELINE_STEPS.length)

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Analysis Pipeline</CardTitle>
          <span className="text-xs text-muted-foreground">
            {Math.round(activeJob.progress * 100)}%
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-1">
          {PIPELINE_STEPS.map((step, index) => {
            const isComplete = index < currentStepIndex
            const isCurrent = index === currentStepIndex

            return (
              <div key={step} className="flex items-center gap-2">
                {isComplete ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : isCurrent ? (
                  <Loader2 className="h-4 w-4 text-primary animate-spin" />
                ) : (
                  <Circle className="h-4 w-4 text-muted-foreground/30" />
                )}
                <span
                  className={`text-sm ${
                    isCurrent
                      ? 'font-medium text-foreground'
                      : isComplete
                      ? 'text-muted-foreground'
                      : 'text-muted-foreground/50'
                  }`}
                >
                  {step}
                </span>
              </div>
            )
          })}
        </div>

        {activeJob.message && (
          <p className="text-xs text-muted-foreground pt-2 border-t">
            {activeJob.message}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
