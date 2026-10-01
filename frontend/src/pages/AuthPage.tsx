import { type CSSProperties, useState } from 'react'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { ArrowRight, Check, Eye, EyeOff, HeartPulse, LockKeyhole, Mail, Menu, Play, ShieldCheck, UserRound, X } from 'lucide-react'
import { apiPost, saveSession, type Session } from '../services/api'

const authSchema = z.object({
  name: z.string().optional(),
  business_name: z.string().optional(),
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(10, 'Use at least 10 characters'),
})
type AuthValues = z.infer<typeof authSchema>

export function AuthPage() {
  const [authOpen, setAuthOpen] = useState(false)
  const [registerMode, setRegisterMode] = useState(false)
  const [pointer, setPointer] = useState({ x: 0, y: 0 })
  const [showPassword, setShowPassword] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [showHowItWorks, setShowHowItWorks] = useState(false)
  const [error, setError] = useState('')
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<AuthValues>({ resolver: zodResolver(authSchema) })

  const submit = handleSubmit(async (values) => {
    setError('')
    try {
      const session = await apiPost<Session>(`/api/v1/auth/${registerMode ? 'register' : 'login'}`, values)
      saveSession(session)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to sign in right now')
    }
  })

  return <main className="auth-screen">
    <div className="auth-noise" />
    <nav className="landing-nav">
      <a className="auth-brand" href="#top" aria-label="CareConnect home"><span className="brand-mark"><HeartPulse size={18} /></span><span>care<span>connect</span></span></a>
      <div className={`landing-links ${mobileMenuOpen ? 'landing-links-open' : ''}`}>
        <a href="#experience" onClick={() => setMobileMenuOpen(false)}>Experience</a>
        <a href="#trust" onClick={() => setMobileMenuOpen(false)}>Why CareConnect</a>
        <button type="button" onClick={() => { setShowHowItWorks(true); setMobileMenuOpen(false) }}>How it works</button>
        <button className="landing-mobile-login" type="button" onClick={() => { setRegisterMode(false); setAuthOpen(true); setMobileMenuOpen(false) }}>Sign in</button>
      </div>
      <div className="landing-actions"><button className="landing-login" type="button" onClick={() => { setRegisterMode(false); setAuthOpen(true) }}>Sign in</button><button className="landing-join" type="button" onClick={() => { setRegisterMode(true); setAuthOpen(true) }}>Join CareConnect <ArrowRight size={15} /></button></div>
      <button className="landing-menu" type="button" aria-label="Toggle navigation" onClick={() => setMobileMenuOpen((open) => !open)}>{mobileMenuOpen ? <X size={21} /> : <Menu size={21} />}</button>
    </nav>

    <section className="auth-hero" id="top">
      <div className="hero-copy">
        <span className="hero-kicker"><span className="hero-kicker-dot" /> A calmer way to care</span>
        <h1>Healthcare,<br /><em>connected</em> around you.</h1>
        <p>Find trusted doctors, understand your options, and book care that fits your life, all in one clear experience.</p>
        <div className="hero-actions"><button className="hero-primary" type="button" onClick={() => { setRegisterMode(false); setAuthOpen(true) }}>Find a doctor <ArrowRight size={17} /></button><button className="hero-secondary" type="button" onClick={() => setShowHowItWorks(true)}><span className="play-icon"><Play size={12} fill="currentColor" /></span> See how it works</button></div>
        <div className="hero-proof"><div className="proof-avatars"><span>AR</span><span>SK</span><span>JM</span></div><span><strong>4.9/5</strong> from people finding better care</span></div>
      </div>
      <div className="hero-stage" aria-label="Abstract connected healthcare visualization" onPointerMove={(event) => { const bounds = event.currentTarget.getBoundingClientRect(); setPointer({ x: (event.clientX - bounds.left - bounds.width / 2) / 18, y: (event.clientY - bounds.top - bounds.height / 2) / 18 }) }} onPointerLeave={() => setPointer({ x: 0, y: 0 })} style={{ '--pointer-x': `${pointer.x}px`, '--pointer-y': `${pointer.y}px` } as CSSProperties}>
        <div className="stage-glow" /><div className="stage-grid" /><div className="stage-orbit stage-orbit-one" /><div className="stage-orbit stage-orbit-two" /><div className="stage-orbit stage-orbit-three" />
        <div className="health-orb"><div className="orb-core"><HeartPulse size={42} strokeWidth={1.4} /><span>care<br />in sync</span></div><span className="orb-shine" /></div>
        <span className="stage-node node-one"><Check size={13} /></span><span className="stage-node node-two"><HeartPulse size={13} /></span><span className="stage-node node-three"><ShieldCheck size={13} /></span>
        <div className="stage-caption"><span className="live-dot" /> Designed around real life <strong>01 — 03</strong></div>
      </div>
    </section>

    <section className="experience-strip" id="experience"><div><span className="section-kicker">THE CARECONNECT EXPERIENCE</span><h2>Less searching.<br /><em>More certainty.</em></h2></div><div className="experience-points"><article><span>01</span><strong>Find your fit</strong><p>Explore trusted doctors by specialty, availability, and the care you need.</p></article><article><span>02</span><strong>Choose with clarity</strong><p>See profiles, services, and open appointment times in one view.</p></article><article><span>03</span><strong>Stay in control</strong><p>Manage your appointments and keep every next step close at hand.</p></article></div></section>

    <section className="trust-strip" id="trust"><span className="trust-icon"><ShieldCheck size={18} /></span><div><strong>Your care, treated with care.</strong><p>Private by design, simple by default, and always clear about what happens next.</p></div><div className="trust-meta"><span>Secure access</span><span>Human-first design</span><span>Built for everyday life</span></div></section>

    <section className="auth-overlay" aria-hidden={!authOpen && !showHowItWorks}>
      <div className="auth-overlay-backdrop" onClick={() => { setAuthOpen(false); setShowHowItWorks(false) }} />
      {showHowItWorks ? <div className="how-card"><button className="overlay-close" type="button" aria-label="Close" onClick={() => setShowHowItWorks(false)}><X size={18} /></button><span className="section-kicker">A SIMPLE FLOW</span><h2>Good care should feel<br /><em>easy to begin.</em></h2><div className="how-steps"><div><span>01</span><strong>Tell us what you need</strong><p>Start with a specialty or a doctor you already trust.</p></div><div><span>02</span><strong>Find a time that works</strong><p>Compare availability without endless calls or tabs.</p></div><div><span>03</span><strong>Keep your plan close</strong><p>Return anytime to see what is coming up next.</p></div></div><button className="hero-primary" type="button" onClick={() => { setShowHowItWorks(false); setRegisterMode(false); setAuthOpen(true) }}>Find a doctor <ArrowRight size={17} /></button></div> : <section className="auth-form-panel"><div className="auth-form-wrap"><div className="auth-mobile-mark"><span className="brand-mark"><HeartPulse size={17} /></span>care<span>connect</span></div><button className="overlay-close" type="button" aria-label="Close sign in" onClick={() => setAuthOpen(false)}><X size={18} /></button><span className="section-kicker">{registerMode ? 'START YOUR JOURNEY' : 'WELCOME BACK'}</span><h2>{registerMode ? 'Create your account' : 'Welcome back'}</h2><p className="auth-lede">{registerMode ? 'Your next step toward simpler care starts here.' : 'Continue your healthcare journey with CareConnect.'}</p>
        <div className="auth-mode" role="group" aria-label="Account mode"><button type="button" className={!registerMode ? 'mode-active' : ''} onClick={() => { setRegisterMode(false); setError('') }}>Sign in</button><button type="button" className={registerMode ? 'mode-active' : ''} onClick={() => { setRegisterMode(true); setError('') }}>Create account</button></div>
        <form className="auth-form" onSubmit={submit} noValidate>
          {registerMode && <><label className="field-label">Full name<div className="input-wrap"><UserRound size={16} /><input autoComplete="name" placeholder="Your name" {...register('name', { required: registerMode })} /></div>{errors.name && <small className="field-error">Name is required</small>}</label><label className="field-label">Practice or clinic name<div className="input-wrap"><HeartPulse size={16} /><input placeholder="Your clinic" {...register('business_name', { required: registerMode })} /></div>{errors.business_name && <small className="field-error">Clinic name is required</small>}</label></>}
          <label className="field-label">Email address<div className="input-wrap"><Mail size={16} /><input type="email" autoComplete="email" placeholder="you@example.com" {...register('email')} /></div>{errors.email && <small className="field-error">{errors.email.message}</small>}</label>
          <label className="field-label">Password<div className="input-wrap"><LockKeyhole size={16} /><input type={showPassword ? 'text' : 'password'} autoComplete={registerMode ? 'new-password' : 'current-password'} placeholder="At least 10 characters" {...register('password')} /><button className="password-toggle" type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword((visible) => !visible)}>{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button></div>{errors.password && <small className="field-error">{errors.password.message}</small>}</label>
          {!registerMode && <div className="form-options"><label><input type="checkbox" /> <span>Keep me signed in</span></label><button type="button" onClick={() => setError('Password recovery is available through your clinic administrator.')}>Forgot password?</button></div>}
          {error && <div className="notice error-notice" role="alert">{error}</div>}
          <button className="primary-button auth-submit" type="submit" disabled={isSubmitting}>{isSubmitting ? 'Please wait…' : registerMode ? 'Create my account' : 'Continue securely'} <ArrowRight size={16} /></button>
        </form><div className="auth-security"><span><LockKeyhole size={14} /> Secure, encrypted access</span><span><ShieldCheck size={14} /> Your privacy matters</span></div>
      </div></section>}
    </section>
  </main>
}
