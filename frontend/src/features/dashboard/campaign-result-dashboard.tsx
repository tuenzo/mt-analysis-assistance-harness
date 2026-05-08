import { ResultDashboardPage } from './result-dashboard-page'
import { buildDashboardSummary } from './dashboard-data'
import type { Artifact, LatestReport, ProjectState } from '@/lib/api-types'

type CampaignResultDashboardProps = {
  state: ProjectState | null
  artifacts: Artifact[]
  latestReport: LatestReport | null
}

export function CampaignResultDashboard({
  state,
  artifacts,
  latestReport,
}: CampaignResultDashboardProps) {
  return (
    <ResultDashboardPage
      summary={buildDashboardSummary({ state, artifacts, report: latestReport })}
    />
  )
}
