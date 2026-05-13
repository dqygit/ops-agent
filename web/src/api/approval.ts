import { requestJson } from './client'

export type ApprovalPolicy = {
  permissions: {
    allow: string[]
    deny: string[]
  }
}

export async function getApprovalPolicy(): Promise<ApprovalPolicy> {
  return requestJson<ApprovalPolicy>('/api/approval/policy')
}

export async function updateApprovalPolicy(policy: ApprovalPolicy): Promise<void> {
  await requestJson<{ message: string }>('/api/approval/policy', {
    method: 'PUT',
    body: JSON.stringify(policy),
  })
}
