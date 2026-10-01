import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Activity, AudioLines, CalendarDays, ChartNoAxesCombined, ChevronDown, CircleHelp, ClipboardList, Clock3, FileText, HeartPulse, LayoutDashboard, LogOut, Menu, Phone, Settings2, Stethoscope, Users, X } from 'lucide-react'
import { apiPost, clearSession } from '../services/api'
import type { User } from '../types'

const headerDate = new Intl.DateTimeFormat('en-IN', { weekday: 'short', day: 'numeric', month: 'short' }).format(new Date())

const navigation = [
  { label: 'Overview', to: '/', icon: LayoutDashboard },
  { label: 'Calls', to: '/calls', icon: Phone },
  { label: 'Appointments', to: '/appointments', icon: CalendarDays },
  { label: 'Customers', to: '/customers', icon: Users },
  { label: 'Leads', to: '/leads', icon: Activity },
  { label: 'Follow-ups', to: '/follow-ups', icon: Clock3 },
  { label: 'Doctors', to: '/doctors', icon: Stethoscope },
  { label: 'Services', to: '/services', icon: ClipboardList },
  { label: 'Knowledge base', to: '/knowledge', icon: FileText },
  { label: 'AI assistant', to: '/assistant', icon: AudioLines },
  { label: 'Staff', to: '/staff', icon: Users },
  { label: 'Escalations', to: '/escalations', icon: CircleHelp },
  { label: 'Analytics', to: '/analytics', icon: ChartNoAxesCombined },
]

export function AppShell({ user }: { user: User }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const navigate = useNavigate()
  const signOut = async () => {
    await apiPost<void>('/api/v1/auth/logout', {}).catch(() => undefined)
    clearSession()
    navigate('/login')
  }

  return (
    <div className="app-shell">
      {mobileOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="brand"><span className="brand-mark"><HeartPulse size={19} /></span><span>care<span>connect</span></span><button className="icon-button sidebar-close" aria-label="Close menu" onClick={() => setMobileOpen(false)}><X size={18} /></button></div>
        <div className="workspace-switch"><span className="clinic-avatar">{user.name.slice(0, 1).toUpperCase()}</span><span className="workspace-name"><strong>{user.business_id ? 'Clinic workspace' : 'CareConnect'}</strong><small>Business account</small></span><ChevronDown size={15} /></div>
        <div className="nav-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          {navigation.map(({ label, to, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'} onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-link ${isActive ? 'nav-active' : ''}`}><Icon size={17} strokeWidth={1.8} /><span>{label}</span></NavLink>)}
        </nav>
        <div className="sidebar-bottom">
          <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? 'nav-active' : ''}`} onClick={() => setMobileOpen(false)}><Settings2 size={17} /><span>Business settings</span></NavLink>
          <div className="user-card"><span className="user-avatar">{user.name.slice(0, 1).toUpperCase()}</span><span className="user-copy"><strong>{user.name}</strong><small>{user.role.replaceAll('_', ' ').toLowerCase()}</small></span><button className="icon-button logout-button" title="Sign out" aria-label="Sign out" onClick={signOut}><LogOut size={16} /></button></div>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar"><button className="icon-button menu-trigger" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu size={20} /></button><div className="breadcrumb"><span>Workspace</span><span className="crumb-slash">/</span><strong>Clinic operations</strong></div><div className="topbar-right"><span className="live-dot" /> <span>System online</span><span className="topbar-divider" /><span className="topbar-date">{headerDate}</span></div></header>
        <div className="page-frame"><Outlet /></div>
      </main>
    </div>
  )
}
