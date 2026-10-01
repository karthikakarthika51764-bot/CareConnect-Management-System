import { useQuery } from '@tanstack/react-query'
import { ArrowRight, ArrowUpRight, CalendarClock, CircleAlert, Phone, Sparkles, Users, UserRoundCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { MetricCard } from '../components/MetricCard'
import { apiGet } from '../services/api'
import type { Appointment, ClinicCall, Customer, DashboardSummary, Doctor, ClinicService } from '../types'

const dashboardToday = new Date()
const dashboardDateLabel = new Intl.DateTimeFormat('en-IN', { weekday: 'long', day: 'numeric', month: 'long' }).format(dashboardToday).toUpperCase()
const dashboardDateKey = dashboardToday.toISOString().slice(0, 10)
const formatTime = (value: string) => new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit' }).format(new Date(value))

export function DashboardPage() {
  const summary = useQuery({ queryKey: ['summary'], queryFn: () => apiGet<DashboardSummary>('/api/v1/dashboard/summary') })
  const appointments = useQuery({ queryKey: ['appointments'], queryFn: () => apiGet<Appointment[]>('/api/v1/appointments') })
  const customers = useQuery({ queryKey: ['customers'], queryFn: () => apiGet<Customer[]>('/api/v1/customers?limit=100') })
  const doctors = useQuery({ queryKey: ['doctors'], queryFn: () => apiGet<Doctor[]>('/api/v1/doctors') })
  const services = useQuery({ queryKey: ['services'], queryFn: () => apiGet<ClinicService[]>('/api/v1/services') })
  const calls = useQuery({ queryKey: ['calls'], queryFn: () => apiGet<ClinicCall[]>('/api/v1/calls') })
  const data = summary.data
  const customerNames = new Map(customers.data?.map((item) => [item.id, item.name]))
  const doctorNames = new Map(doctors.data?.map((item) => [item.id, item.name]))
  const serviceNames = new Map(services.data?.map((item) => [item.id, item.name]))
  const todayAppointments = (appointments.data ?? []).filter((item) => item.starts_at.slice(0, 10) === dashboardDateKey && item.status !== 'CANCELLED').slice(0, 5)
  const latestCalls = (calls.data ?? []).slice(0, 4)
  const languageCounts = {
    ta: (calls.data ?? []).filter((call) => call.language === 'ta' || call.language === 'Tamil').length,
    en: (calls.data ?? []).filter((call) => call.language === 'en' || call.language === 'English').length,
    tanglish: (calls.data ?? []).filter((call) => call.language === 'ta-en' || call.language === 'Tanglish').length,
  }
  const knownLanguageCalls = Math.max(Object.values(languageCounts).reduce((total, count) => total + count, 0), 1)
  const languageShare = (count: number) => `${Math.round(count / knownLanguageCalls * 100)}%`
  const queryError = summary.error || appointments.error || calls.error

  return (
    <div className="dashboard-page page-enter">
      <section className="welcome-row"><div><div className="eyebrow"><span className="eyebrow-dot" /> {dashboardDateLabel}</div><h1>Your clinic, <em>in good hands.</em></h1><p>Here is what's happening across your front desk today.</p></div><Link to="/appointments" className="primary-button"><CalendarClock size={16} /> Manage appointments</Link></section>
      {queryError && <div className="notice error-notice" role="alert"><CircleAlert size={17} /> Could not load all live clinic data. Check the API connection and retry.</div>}
      <section className="metric-grid" aria-label="Clinic metrics">
        <MetricCard label="Calls handled" value={data?.total_calls ?? '—'} note={`${data?.ai_calls ?? 0} by AI · ${data?.human_calls ?? 0} by team`} icon={Phone} tone="mint" />
        <MetricCard label="Today's appointments" value={data?.appointments_today ?? '—'} note="Confirmed and pending" icon={CalendarClock} tone="coral" />
        <MetricCard label="New leads" value={data?.new_leads ?? '—'} note="Awaiting first contact" icon={Users} tone="gold" />
        <MetricCard label="Needs attention" value={data?.open_escalations ?? '—'} note={`${data?.pending_follow_ups ?? 0} follow-ups pending`} icon={CircleAlert} tone="blue" />
      </section>
      <section className="dashboard-grid">
        <article className="surface appointment-surface">
          <div className="surface-heading"><div><span className="section-kicker">SCHEDULE</span><h2>Today's appointments</h2></div><Link to="/appointments" className="text-link">Full schedule <ArrowRight size={15} /></Link></div>
          {appointments.isLoading ? <div className="loading-row">Loading schedule…</div> : todayAppointments.length ? <div className="appointment-list">{todayAppointments.map((appointment) => <div className="appointment-row" key={appointment.id}><div className="appointment-time">{formatTime(appointment.starts_at)}</div><span className="appointment-rule" /><span className="patient-initial">{(customerNames.get(appointment.customer_id) ?? 'P').slice(0, 1)}</span><div className="appointment-detail"><strong>{customerNames.get(appointment.customer_id) ?? `Patient #${appointment.customer_id}`}</strong><small>{doctorNames.get(appointment.doctor_id) ?? `Doctor #${appointment.doctor_id}`} · {serviceNames.get(appointment.service_id) ?? `Service #${appointment.service_id}`}</small></div><span className={`status-pill ${appointment.status.toLowerCase()}`}>{appointment.status.toLowerCase()}</span></div>)}</div> : <div className="empty-state compact-empty"><span className="empty-illustration"><CalendarClock size={20} /></span><strong>No appointments today</strong><span>Your upcoming bookings will appear here.</span></div>}
        </article>
        <article className="surface call-surface">
          <div className="surface-heading"><div><span className="section-kicker">RECEPTION</span><h2>Recent calls</h2></div><Link to="/calls" className="icon-link" aria-label="View all calls"><ArrowRight size={17} /></Link></div>
          {calls.isLoading ? <div className="loading-row">Loading calls…</div> : latestCalls.length ? <div className="call-list">{latestCalls.map((call) => <div className="call-row" key={call.id}><span className={`call-icon ${call.handled_by === 'AI' ? 'call-ai' : 'call-human'}`}>{call.handled_by === 'AI' ? <Sparkles size={16} /> : <UserRoundCheck size={16} />}</span><div className="call-detail"><strong>{call.caller_number || 'Unknown caller'}</strong><small>{call.detected_intent?.replaceAll('_', ' ').toLowerCase() || 'General enquiry'} · {call.language || 'language not detected'}</small></div><div className="call-time">{formatTime(call.started_at)}<small>{call.status.replace('CALL_', '').toLowerCase()}</small></div></div>)}</div> : <div className="empty-state compact-empty"><span className="empty-illustration"><Phone size={20} /></span><strong>No calls recorded</strong><span>Connected voice calls will show up here.</span></div>}
          {data && <div className="call-footnote"><span><span className="tiny-dot ai-dot" /> AI answered <strong>{data.ai_calls}</strong></span><span><span className="tiny-dot team-dot" /> Team answered <strong>{data.human_calls}</strong></span></div>}
        </article>
      </section>
      <section className="bottom-grid">
        <article className="surface pipeline-surface"><div className="surface-heading"><div><span className="section-kicker">TEAM INBOX</span><h2>Follow-through</h2></div><Link to="/follow-ups" className="text-link">Open queue <ArrowRight size={15} /></Link></div><div className="follow-through"><div className="follow-stat"><span className="follow-number">{data?.pending_follow_ups ?? '—'}</span><span>follow-ups due</span></div><div className="follow-divider" /><div className="follow-stat"><span className="follow-number">{data?.missed_calls ?? '—'}</span><span>missed calls</span></div><div className="follow-divider" /><div className="follow-stat"><span className="follow-number">{data?.open_escalations ?? '—'}</span><span>open escalations</span></div></div></article>
        <article className="surface language-surface"><div className="surface-heading"><div><span className="section-kicker">VOICE DESK</span><h2>Language mix</h2></div><span className="status-chip"><span className="live-dot" /> Listening</span></div><div className="language-bars"><div><span>தமிழ்</span><div className="bar-track"><span style={{ width: languageShare(languageCounts.ta) }} /></div><strong>{languageCounts.ta}</strong></div><div><span>English</span><div className="bar-track coral-track"><span style={{ width: languageShare(languageCounts.en) }} /></div><strong>{languageCounts.en}</strong></div><div><span>Tanglish</span><div className="bar-track gold-track"><span style={{ width: languageShare(languageCounts.tanglish) }} /></div><strong>{languageCounts.tanglish}</strong></div></div><div className="language-foot"><ArrowUpRight size={14} /> Based on saved call language labels</div></article>
      </section>
    </div>
  )
}
