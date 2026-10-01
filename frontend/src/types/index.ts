export type User = { id: number; name: string; email: string; role: string; business_id: number }
export type DashboardSummary = {
  total_calls: number
  ai_calls: number
  human_calls: number
  appointments_today: number
  new_leads: number
  pending_follow_ups: number
  missed_calls: number
  open_escalations: number
}
export type Appointment = {
  id: number
  customer_id: number
  doctor_id: number
  service_id: number
  starts_at: string
  ends_at: string
  status: string
  notes: string | null
}
export type Customer = { id: number; name: string; phone: string; email: string | null; notes: string | null }
export type Doctor = { id: number; name: string; specialization: string; status: string; consultation_fee: number | null }
export type ClinicService = { id: number; name: string; duration_minutes: number; price: number | null; status: string }
export type ClinicCall = { id: number; caller_number: string | null; status: string; detected_intent: string | null; language: string | null; started_at: string; handled_by: string }
