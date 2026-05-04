'use client'

import type { ApprovalRequest } from '@/store/agent-store'
import { Button } from '@/components/ui/button'
import { AlertTriangle, AlertCircle, Info, Check, X } from 'lucide-react'

interface ApprovalBannerProps {
  approval: ApprovalRequest
  onApprove: (id: string) => void
  onReject: (id: string) => void
}

const riskConfig = {
  low: { icon: Info, color: 'bg-blue-50 border-blue-200 text-blue-800' },
  medium: { icon: AlertTriangle, color: 'bg-yellow-50 border-yellow-200 text-yellow-800' },
  high: { icon: AlertCircle, color: 'bg-red-50 border-red-200 text-red-800' },
}

export function ApprovalBanner({ approval, onApprove, onReject }: ApprovalBannerProps) {
  const config = riskConfig[approval.riskLevel]
  const Icon = config.icon

  return (
    <div className={`p-4 border rounded-lg ${config.color}`}>
      <div className="flex items-start gap-3">
        <Icon className="h-5 w-5 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-sm">Action Approval Required</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-white/50">
              {approval.riskLevel.toUpperCase()} RISK
            </span>
          </div>
          <p className="text-sm mb-2">
            <span className="font-mono font-medium">{approval.action}</span>
          </p>
          <p className="text-sm opacity-80">{approval.reason}</p>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <Button
            size="sm"
            variant="outline"
            className="bg-white hover:bg-gray-100"
            onClick={() => onReject(approval.id)}
          >
            <X className="h-4 w-4 mr-1" />
            Reject
          </Button>
          <Button
            size="sm"
            className="bg-primary hover:bg-primary/90 text-white"
            onClick={() => onApprove(approval.id)}
          >
            <Check className="h-4 w-4 mr-1" />
            Approve
          </Button>
        </div>
      </div>
    </div>
  )
}
