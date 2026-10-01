import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDownUp, ArrowRight, CircleAlert, Plus, Search, SlidersHorizontal, X } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { apiGet, apiPost, apiDelete } from '../services/api'
import type { DashboardSummary } from '../types'

type Field = { name: string; label: string; type?: string; required?: boolean; options?: string[]; source?: string; labelKey?: string }
type Resource = { title: string; eyebrow: string; description: string; endpoint?: string; createEndpoint?: string; fields?: Field[]; columns?: string[]; custom?: 'summary' | 'knowledge' }
const firstAvailableDate = new Date(Date.now() + 24 * 60 * 60 * 1000).toLocaleDateString('en-CA')

const resources: Record<string, Resource> = {
  '/calls': { title: 'Call activity', eyebrow: 'RECEPTION', description: 'Inbound conversations handled by your AI receptionist and clinic team.', endpoint: '/api/v1/calls', columns: ['caller_number', 'detected_intent', 'language', 'handled_by', 'status', 'started_at'] },
  '/appointments': { title: 'Appointments', eyebrow: 'SCHEDULING', description: 'Review bookings, manage availability and keep the day moving.', endpoint: '/api/v1/appointments', createEndpoint: '/api/v1/appointments', columns: ['customer_id', 'doctor_id', 'service_id', 'starts_at', 'status'] },
  '/customers': { title: 'Customers', eyebrow: 'RELATIONSHIPS', description: 'Patient details and history stay connected to your clinic.', endpoint: '/api/v1/customers', createEndpoint: '/api/v1/customers', columns: ['name', 'phone', 'email', 'created_at'], fields: [{ name: 'name', label: 'Full name' }, { name: 'phone', label: 'Phone number', type: 'tel' }, { name: 'email', label: 'Email', type: 'email', required: false }, { name: 'notes', label: 'Notes', type: 'textarea', required: false }] },
  '/leads': { title: 'Leads', eyebrow: 'GROWTH', description: 'Keep incoming enquiries visible and assign a clear next step.', endpoint: '/api/v1/leads', createEndpoint: '/api/v1/leads', columns: ['customer_id', 'source', 'status', 'notes', 'created_at'], fields: [{ name: 'customer_id', label: 'Customer', type: 'select', source: '/api/v1/customers', labelKey: 'name' }, { name: 'source', label: 'Source', type: 'select', options: ['phone', 'website', 'referral', 'manual'] }, { name: 'status', label: 'Status', type: 'select', options: ['NEW', 'CONTACTED', 'INTERESTED', 'FOLLOW_UP', 'CONVERTED', 'NOT_INTERESTED', 'LOST'] }, { name: 'notes', label: 'Notes', type: 'textarea', required: false }] },
  '/follow-ups': { title: 'Follow-ups', eyebrow: 'TEAM INBOX', description: 'A shared queue for the conversations that need a second touch.', endpoint: '/api/v1/follow-ups', createEndpoint: '/api/v1/follow-ups', columns: ['customer_id', 'due_at', 'status', 'notes'], fields: [{ name: 'customer_id', label: 'Customer', type: 'select', source: '/api/v1/customers', labelKey: 'name' }, { name: 'due_at', label: 'Due date', type: 'datetime-local' }, { name: 'notes', label: 'Notes', type: 'textarea', required: false }] },
  '/doctors': { title: 'Doctors', eyebrow: 'CLINIC TEAM', description: 'Manage your providers and the specialities patients can book.', endpoint: '/api/v1/doctors', createEndpoint: '/api/v1/doctors', columns: ['name', 'specialization', 'consultation_fee', 'status'], fields: [{ name: 'name', label: 'Doctor name' }, { name: 'specialization', label: 'Speciality' }, { name: 'consultation_fee', label: 'Consultation fee (INR)', type: 'number', required: false }, { name: 'phone', label: 'Phone', type: 'tel', required: false }, { name: 'email', label: 'Email', type: 'email', required: false }] },
  '/services': { title: 'Services', eyebrow: 'CLINIC CATALOG', description: 'Keep consultation types, durations and pricing in one place.', endpoint: '/api/v1/services', createEndpoint: '/api/v1/services', columns: ['name', 'duration_minutes', 'price', 'status'], fields: [{ name: 'name', label: 'Service name' }, { name: 'description', label: 'Description', type: 'textarea', required: false }, { name: 'duration_minutes', label: 'Duration (minutes)', type: 'number' }, { name: 'price', label: 'Price (INR)', type: 'number', required: false }] },
  '/knowledge': { title: 'Knowledge base', eyebrow: 'AI CONTENT', description: 'Approved clinic facts the assistant can use to answer patient questions.', endpoint: '/api/v1/knowledge/documents', createEndpoint: '/api/v1/knowledge/documents', columns: ['title', 'category', 'content', 'created_at'], fields: [{ name: 'title', label: 'Document title' }, { name: 'category', label: 'Category', type: 'select', options: ['faq', 'policy', 'clinic', 'pricing', 'service'] }, { name: 'content', label: 'Approved answer or information', type: 'textarea' }] },
  '/staff': { title: 'Staff', eyebrow: 'TEAM ACCESS', description: 'Invite clinic staff with role-scoped access to the workspace.', endpoint: '/api/v1/staff', createEndpoint: '/api/v1/staff', columns: ['name', 'email', 'role', 'is_active'], fields: [{ name: 'name', label: 'Full name' }, { name: 'email', label: 'Email', type: 'email' }, { name: 'password', label: 'Temporary password (10+ characters)', type: 'password' }, { name: 'role', label: 'Role', type: 'select', options: ['STAFF', 'RECEPTIONIST'] }] },
  '/escalations': { title: 'Human escalations', eyebrow: 'TEAM HANDOFF', description: 'Requests that need a personal response from your clinic team.', endpoint: '/api/v1/escalations', columns: ['reason', 'priority', 'status', 'created_at'] },
  '/analytics': { title: 'Clinic analytics', eyebrow: 'PERFORMANCE', description: 'A live snapshot of conversations, bookings and team follow-through.', custom: 'summary' },
}

function formatCell(value: unknown, key: string) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Active' : 'Inactive'
  if (typeof value === 'string' && (key.endsWith('_at') || key === 'created_at')) return new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
  if (typeof value === 'string' && (key === 'status' || key === 'handled_by' || key === 'detected_intent' || key === 'role')) return value.replace('CALL_', '').replaceAll('_', ' ').toLowerCase()
  return String(value)
}

function CreateDialog({ config, onClose, onCreated }: { config: Resource; onClose: () => void; onCreated: (values: Record<string, unknown>) => void }) {
  const { register, handleSubmit, formState: { errors } } = useForm<Record<string, unknown>>()
  const fields = config.fields ?? []
  const submit = handleSubmit((values) => {
    const converted: Record<string, unknown> = {}
    Object.entries(values).forEach(([key, raw]) => {
      const value = String(raw ?? '').trim()
      if (!value) return
      const field = fields.find((item) => item.name === key)
      if (field?.type === 'number' || (field?.type === 'select' && field.source)) converted[key] = Number(value)
      else if (field?.type === 'datetime-local') converted[key] = new Date(value).toISOString()
      else converted[key] = value
    })
    onCreated(converted)
  })
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section className="form-dialog" role="dialog" aria-modal="true" aria-labelledby="create-title"><div className="dialog-heading"><div><span className="section-kicker">NEW RECORD</span><h2 id="create-title">Add {config.title.toLowerCase().replace(/s$/, '')}</h2></div><button className="icon-button" aria-label="Close dialog" onClick={onClose}><X size={18} /></button></div><form className="record-form" onSubmit={submit}>{fields.map((field) => <label className="field-label" key={field.name}>{field.label}{field.source ? <SourceField field={field} register={register} /> : field.type === 'select' ? <select className="form-control" {...register(field.name, { required: true })}><option value="">Choose…</option>{field.options?.map((option) => <option key={option} value={option}>{option.replaceAll('_', ' ')}</option>)}</select> : field.type === 'textarea' ? <textarea className="form-control" rows={3} {...register(field.name, { required: field.required ?? true })} /> : <input className="form-control" type={field.type ?? 'text'} step={field.type === 'number' ? 'any' : undefined} {...register(field.name, { required: field.required ?? true })} />}{errors[field.name] && <small className="field-error">This field is required</small>}</label>)}<div className="dialog-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancel</button><button type="submit" className="primary-button"><Plus size={16} /> Save record</button></div></form></section></div>
}

function SourceField({ field, register }: { field: Field; register: ReturnType<typeof useForm<Record<string, unknown>>>['register'] }) {
  const options = useQuery({ queryKey: ['form-options', field.source], queryFn: () => apiGet<Record<string, unknown>[]>(field.source!) })
  return <select className="form-control" {...register(field.name, { required: true })}><option value="">Choose…</option>{(options.data ?? []).map((item) => <option key={String(item.id)} value={String(item.id)}>{String(item[field.labelKey ?? 'name'])}</option>)}</select>
}

function BookingDialog({ onClose, onCreated }: { onClose: () => void; onCreated: (values: Record<string, unknown>) => void }) {
  const customers = useQuery({ queryKey: ['customers'], queryFn: () => apiGet<Record<string, unknown>[]>('/api/v1/customers') })
  const doctors = useQuery({ queryKey: ['doctors'], queryFn: () => apiGet<Record<string, unknown>[]>('/api/v1/doctors') })
  const services = useQuery({ queryKey: ['services'], queryFn: () => apiGet<Record<string, unknown>[]>('/api/v1/services') })
  const [customerId, setCustomerId] = useState('')
  const [doctorId, setDoctorId] = useState('')
  const [serviceId, setServiceId] = useState('')
  const [onDate, setOnDate] = useState('')
  const [slot, setSlot] = useState('')
  const [notes, setNotes] = useState('')
  const availability = useQuery({
    queryKey: ['availability', doctorId, serviceId, onDate],
    queryFn: () => apiGet<{ slots: string[] }>(`/api/v1/appointments/availability?doctor_id=${doctorId}&service_id=${serviceId}&on_date=${onDate}`),
    enabled: Boolean(doctorId && serviceId && onDate),
  })
  const minimumDate = firstAvailableDate
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section className="form-dialog" role="dialog" aria-modal="true" aria-labelledby="booking-title"><div className="dialog-heading"><div><span className="section-kicker">SLOT CHECK</span><h2 id="booking-title">Book an appointment</h2></div><button className="icon-button" aria-label="Close dialog" onClick={onClose}><X size={18} /></button></div><div className="record-form"><label className="field-label">Patient<select className="form-control" value={customerId} onChange={(event) => setCustomerId(event.target.value)}><option value="">Choose a patient…</option>{(customers.data ?? []).map((item) => <option key={String(item.id)} value={String(item.id)}>{String(item.name)} · {String(item.phone)}</option>)}</select></label><label className="field-label">Doctor<select className="form-control" value={doctorId} onChange={(event) => { setDoctorId(event.target.value); setSlot('') }}><option value="">Choose a doctor…</option>{(doctors.data ?? []).map((item) => <option key={String(item.id)} value={String(item.id)}>{String(item.name)} · {String(item.specialization)}</option>)}</select></label><label className="field-label">Service<select className="form-control" value={serviceId} onChange={(event) => { setServiceId(event.target.value); setSlot('') }}><option value="">Choose a service…</option>{(services.data ?? []).map((item) => <option key={String(item.id)} value={String(item.id)}>{String(item.name)} · {String(item.duration_minutes)} min</option>)}</select></label><label className="field-label">Date<input className="form-control" type="date" min={minimumDate} value={onDate} onChange={(event) => { setOnDate(event.target.value); setSlot('') }} /></label>{doctorId && serviceId && onDate && <label className="field-label">Available time<select className="form-control" value={slot} onChange={(event) => setSlot(event.target.value)} disabled={availability.isLoading || !availability.data?.slots.length}><option value="">{availability.isLoading ? 'Checking availability…' : availability.data?.slots.length ? 'Choose an available time…' : 'No times available on this date'}</option>{(availability.data?.slots ?? []).map((value) => <option key={value} value={value}>{new Date(value).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</option>)}</select></label>}<label className="field-label">Notes <span className="field-optional">Optional</span><textarea className="form-control" rows={2} value={notes} onChange={(event) => setNotes(event.target.value)} /></label>{availability.error && <div className="notice error-notice"><CircleAlert size={15} /> {availability.error.message}</div>}<div className="dialog-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancel</button><button type="button" className="primary-button" disabled={!customerId || !doctorId || !serviceId || !slot} onClick={() => onCreated({ customer_id: Number(customerId), doctor_id: Number(doctorId), service_id: Number(serviceId), starts_at: slot, notes })}><Plus size={16} /> Confirm booking</button></div></div></section></div>
}

export function WorkspacePage() {
  const location = useLocation()
  const config = resources[location.pathname] ?? resources['/calls']
  const [showCreate, setShowCreate] = useState(false)
  const [search, setSearch] = useState('')
  const client = useQueryClient()
  const isCustom = Boolean(config.custom)
  const items = useQuery({ queryKey: ['resource', config.endpoint], queryFn: () => apiGet<Record<string, unknown>[]>(config.endpoint!), enabled: Boolean(config.endpoint) })
  const summary = useQuery({ queryKey: ['summary'], queryFn: () => apiGet<DashboardSummary>('/api/v1/dashboard/summary'), enabled: config.custom === 'summary' })
  const create = useMutation({ mutationFn: (values: Record<string, unknown>) => apiPost(config.createEndpoint!, values), onSuccess: () => { void client.invalidateQueries({ queryKey: ['resource', config.endpoint] }); void client.invalidateQueries({ queryKey: ['summary'] }); setShowCreate(false) } })
  const remove = useMutation({ mutationFn: (id: number) => apiDelete(`/api/v1/knowledge/documents/${id}`), onSuccess: () => void client.invalidateQueries({ queryKey: ['resource', config.endpoint] }) })
  const cancelBooking = useMutation({ mutationFn: (id: number) => apiPost(`/api/v1/appointments/${id}/cancel`, {}), onSuccess: () => { void client.invalidateQueries({ queryKey: ['resource', config.endpoint] }); void client.invalidateQueries({ queryKey: ['summary'] }) } })
  const rows = useMemo(() => (items.data ?? []).filter((row) => Object.values(row).some((value) => String(value ?? '').toLowerCase().includes(search.toLowerCase()))), [items.data, search])
  const isLoading = isCustom ? summary.isLoading : items.isLoading
  const error = isCustom ? summary.error : items.error

  return <div className="workspace-page page-enter"><div className="page-heading"><div><span className="section-kicker">{config.eyebrow}</span><h1>{config.title}</h1><p>{config.description}</p></div>{config.createEndpoint && <button className="primary-button" onClick={() => setShowCreate(true)}><Plus size={16} /> Add new</button>}</div>
    {showCreate && (location.pathname === '/appointments' ? <BookingDialog onClose={() => setShowCreate(false)} onCreated={(values) => create.mutate(values)} /> : <CreateDialog config={config} onClose={() => setShowCreate(false)} onCreated={(values) => create.mutate(values)} />)}
    {create.error && <div className="notice error-notice" role="alert"><CircleAlert size={17} /> {create.error.message}</div>}
    {config.custom === 'summary' ? <AnalyticsSummary data={summary.data} isLoading={summary.isLoading} /> : <section className="surface data-surface"><div className="table-toolbar"><div className="table-count">{items.data?.length ?? 0} records <span>·</span> business workspace</div><div className="table-tools"><label className="search-box"><Search size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search records" aria-label="Search records" /></label><button className="icon-button filter-button" title="Sort by most recent" aria-label="Sort by most recent"><SlidersHorizontal size={16} /></button></div></div>
      {error && <div className="notice error-notice table-notice" role="alert"><CircleAlert size={17} /> {error instanceof Error ? error.message : 'Could not load records'}</div>}
      {isLoading ? <div className="loading-panel">Loading records…</div> : rows.length ? <div className="table-scroll"><table className="data-table"><thead><tr>{(config.columns ?? []).map((column) => <th key={column}>{column.replaceAll('_', ' ')}<ArrowDownUp size={12} /></th>)}{(config.title === 'Knowledge base' || config.title === 'Appointments') && <th>Actions</th>}</tr></thead><tbody>{rows.map((row) => <tr key={String(row.id)}>{(config.columns ?? []).map((column, index) => <td key={column}>{config.title === 'Call activity' && index === 0 ? <Link className="table-primary-link" to={`/calls/${row.id}`}>{row[column] ? formatCell(row[column], column) : `Call #${row.id}`}</Link> : <span className={column === 'status' ? `status-pill ${String(row[column]).toLowerCase()}` : ''}>{formatCell(row[column], column)}</span>}</td>)}{config.title === 'Knowledge base' && <td><button className="text-action danger-text" onClick={() => { if (window.confirm('Delete this knowledge document?')) remove.mutate(Number(row.id)) }}>Delete</button></td>}{config.title === 'Appointments' && <td>{row.status === 'CONFIRMED' || row.status === 'PENDING' ? <button className="text-action danger-text" disabled={cancelBooking.isPending} onClick={() => { if (window.confirm('Cancel this appointment and release its slot?')) cancelBooking.mutate(Number(row.id)) }}>Cancel</button> : <span>—</span>}</td>}</tr>)}</tbody></table></div> : <div className="empty-state"><span className="empty-illustration"><Search size={20} /></span><strong>{search ? 'No matching records' : 'Nothing here yet'}</strong><span>{search ? 'Try a different search term.' : 'New clinic records will appear here as your team works.'}</span>{config.createEndpoint && !search && <button className="secondary-button" onClick={() => setShowCreate(true)}><Plus size={15} /> Add first record</button>}</div>}
      {rows.length > 0 && <div className="table-footer"><span>Showing {rows.length} of {items.data?.length ?? 0}</span><span>Page 1 <button className="icon-button" aria-label="Next page" disabled><ArrowRight size={14} /></button></span></div>}
    </section>}
  </div>
}

function AnalyticsSummary({ data, isLoading }: { data?: DashboardSummary; isLoading: boolean }) {
  const metrics = [{ label: 'Calls handled', value: data?.total_calls }, { label: 'AI answered', value: data?.ai_calls }, { label: 'Human answered', value: data?.human_calls }, { label: 'Appointments today', value: data?.appointments_today }, { label: 'New leads', value: data?.new_leads }, { label: 'Follow-ups pending', value: data?.pending_follow_ups }, { label: 'Missed calls', value: data?.missed_calls }, { label: 'Open escalations', value: data?.open_escalations }]
  return <section className="analytics-grid">{metrics.map((metric, index) => <article className={`surface analytics-tile analytics-tile-${index % 4}`} key={metric.label}><span>{metric.label}</span><strong>{isLoading ? '—' : metric.value ?? 0}</strong><small><ArrowRight size={13} /> Live business data</small></article>)}</section>
}
