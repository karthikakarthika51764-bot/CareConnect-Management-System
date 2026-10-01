import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, CircleAlert, Clock3, Save } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { apiGet, apiPut } from '../services/api'

type Business = { id: number; name: string; phone: string | null; email: string | null; address: string | null; timezone: string; description: string | null; status: string }
type Hours = { id?: number; day_of_week: number; open_time: string | null; close_time: string | null; is_closed: boolean }
const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const defaultHours = weekdays.map((_, day_of_week) => ({ day_of_week, open_time: '09:00', close_time: '17:00', is_closed: day_of_week === 6 }))

export function BusinessSettingsPage() {
  const queryClient = useQueryClient()
  const business = useQuery({ queryKey: ['business'], queryFn: () => apiGet<Business>('/api/v1/business') })
  const hours = useQuery({ queryKey: ['hours'], queryFn: () => apiGet<Hours[]>('/api/v1/business/hours') })
  const { register, handleSubmit, reset, formState: { isDirty } } = useForm<Business>()
  const [scheduleDraft, setScheduleDraft] = useState<Hours[] | null>(null)
  const [notice, setNotice] = useState('')
  useEffect(() => { if (business.data) reset(business.data) }, [business.data, reset])
  const schedule = scheduleDraft ?? defaultHours.map((day) => ({ ...day, ...hours.data?.find((item) => item.day_of_week === day.day_of_week) }))
  const saveBusiness = useMutation({ mutationFn: (payload: Business) => apiPut<Business>('/api/v1/business', payload), onSuccess: (value) => { queryClient.setQueryData(['business'], value); setNotice('Business details saved') } })
  const saveHours = useMutation({ mutationFn: (payload: Hours[]) => apiPut<Hours[]>('/api/v1/business/hours', payload), onSuccess: (value) => { queryClient.setQueryData(['hours'], value); setScheduleDraft(defaultHours.map((day) => ({ ...day, ...value.find((item) => item.day_of_week === day.day_of_week) }))); setNotice('Working hours saved') } })
  const updateDay = (index: number, patch: Partial<Hours>) => setScheduleDraft((current) => (current ?? schedule).map((day, row) => row === index ? { ...day, ...patch } : day))

  return <div className="workspace-page page-enter"><div className="page-heading"><div><span className="section-kicker">WORKSPACE CONFIGURATION</span><h1>Business settings</h1><p>Clinic identity and opening hours used by your patient-facing workflows.</p></div></div>{notice && <div className="notice success-notice"><Check size={16} /> {notice}</div>}{(business.error || saveBusiness.error || saveHours.error) && <div className="notice error-notice"><CircleAlert size={16} /> {(business.error || saveBusiness.error || saveHours.error)?.message}</div>}
    <div className="settings-layout"><section className="surface settings-surface"><div className="surface-heading"><div><span className="section-kicker">CLINIC PROFILE</span><h2>Public details</h2></div></div><form className="settings-form" onSubmit={handleSubmit((value) => saveBusiness.mutate(value))}><label className="field-label">Clinic name<input className="form-control" {...register('name', { required: true })} /></label><label className="field-label">Phone<input className="form-control" type="tel" {...register('phone')} /></label><label className="field-label">Contact email<input className="form-control" type="email" {...register('email')} /></label><label className="field-label">Timezone<input className="form-control" {...register('timezone', { required: true })} /></label><label className="field-label field-span">Address<textarea className="form-control" rows={2} {...register('address')} /></label><label className="field-label field-span">Description<textarea className="form-control" rows={3} {...register('description')} /></label><div className="settings-actions"><span>{business.data?.status === 'active' ? 'Clinic account active' : 'Loading clinic details'}</span><button className="primary-button" disabled={!isDirty || saveBusiness.isPending}><Save size={15} /> Save profile</button></div></form></section>
    <section className="surface settings-surface"><div className="surface-heading"><div><span className="section-kicker">APPOINTMENT WINDOWS</span><h2><Clock3 size={18} /> Working hours</h2></div><button className="secondary-button" disabled={saveHours.isPending} onClick={() => saveHours.mutate(schedule)}><Save size={15} /> Save hours</button></div><div className="hours-table"><div className="hours-header"><span>DAY</span><span>OPENS</span><span>CLOSES</span><span>CLOSED</span></div>{schedule.map((day, index) => <div className={`hours-row ${day.is_closed ? 'hours-closed' : ''}`} key={day.day_of_week}><strong>{weekdays[day.day_of_week]}</strong><input aria-label={`${weekdays[day.day_of_week]} opening time`} type="time" disabled={day.is_closed} value={day.open_time ?? ''} onChange={(event) => updateDay(index, { open_time: event.target.value })} /><input aria-label={`${weekdays[day.day_of_week]} closing time`} type="time" disabled={day.is_closed} value={day.close_time ?? ''} onChange={(event) => updateDay(index, { close_time: event.target.value })} /><label className="closed-toggle"><input type="checkbox" checked={day.is_closed} onChange={(event) => updateDay(index, { is_closed: event.target.checked })} /><span>{day.is_closed ? 'Closed' : 'Open'}</span></label></div>)}</div></section></div></div>
}
