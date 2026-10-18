export interface SubmitReportInput {
  title: string
  narrative: string
  observed_at: string
}

export interface ReportSubmission {
  report_id: string
  status: 'pending'
  submitted_at: string
  message: string
}
