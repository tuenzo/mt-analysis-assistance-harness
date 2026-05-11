'use client'

import { ResultDashboardPage } from '@/features/dashboard/result-dashboard-page'
import { keemartDashboardSummary, keemartReportFacts } from '@/features/demo/keemart-demo-data'

export function KeemartDemoDashboardPage() {
  return (
    <ResultDashboardPage
      summary={keemartDashboardSummary}
      initialFilters={{
        timeRange: keemartReportFacts.timeRange,
        activityWindow: 'all',
        categoryLevel: 'all',
        calendarType: 'all',
      }}
      timeRangeLabel="2025.09.01~11.30"
      preserveLocalGap
      showcaseLayout
    />
  )
}
