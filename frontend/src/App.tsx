import { useState, useEffect, useRef } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:9000')

export default function App() {
  const [view, setView] = useState<'landing' | 'app'>('landing')

  if (view === 'app') {
    return <ScraperApp onBack={() => setView('landing')} />
  }

  return <LandingPage onGoToApp={() => setView('app')} />
}

function LandingPage({ onGoToApp }: { onGoToApp: () => void }) {
  const [scrolled, setScrolled] = useState(false)
  const [revealedSections, setRevealedSections] = useState<Set<string>>(new Set())
  const sectionRefs = useRef<Record<string, HTMLElement | null>>({})

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    const canvas = document.getElementById('wireframe-canvas') as HTMLCanvasElement
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationFrameId: number
    let width = canvas.width = window.innerWidth
    let height = canvas.height = window.innerHeight

    const handleResize = () => {
      width = canvas.width = window.innerWidth
      height = canvas.height = window.innerHeight
    }
    window.addEventListener('resize', handleResize)

    const cols = 40
    const rows = 20
    let time = 0

    const draw = () => {
      ctx.clearRect(0, 0, width, height)
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)'
      ctx.lineWidth = 1

      const stepX = width / cols
      const stepY = (height / 2) / rows
      const startY = height / 2

      ctx.beginPath()
      for (let y = 0; y <= rows; y++) {
        for (let x = 0; x <= cols; x++) {
          const px = x * stepX
          const noise = Math.sin(x * 0.5 + time) * Math.cos(y * 0.5 + time) * 30
          const py = startY + y * stepY + noise * (y / rows)
          
          if (x === 0) {
            ctx.moveTo(px, py)
          } else {
            ctx.lineTo(px, py)
          }
        }
      }
      for (let x = 0; x <= cols; x++) {
        for (let y = 0; y <= rows; y++) {
          const px = x * stepX
          const noise = Math.sin(x * 0.5 + time) * Math.cos(y * 0.5 + time) * 30
          const py = startY + y * stepY + noise * (y / rows)
          
          if (y === 0) {
            ctx.moveTo(px, py)
          } else {
            ctx.lineTo(px, py)
          }
        }
      }
      ctx.stroke()

      time += 0.01
      animationFrameId = requestAnimationFrame(draw)
    }
    draw()

    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animationFrameId)
    }
  }, [])

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setRevealedSections((prev) => new Set([...prev, entry.target.id]))
          }
        })
      },
      { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
    )

    Object.values(sectionRefs.current).forEach((el) => {
      if (el) observer.observe(el)
    })

    return () => observer.disconnect()
  }, [])

  const _isRevealed = (id: string) => revealedSections.has(id)
  void _isRevealed // suppress unused warning — kept for future use

  return (
    <div className="app">
      <nav className={`navbar ${scrolled ? 'scrolled' : ''}`} role="navigation" aria-label="Main navigation">
        <div className="navbar-inner">
          <a href="/" className="logo" aria-label="Spresy Home">
            <span className="logo-mark"></span>
            <span className="logo-text">Spresy</span>
          </a>
          <div className="nav-links">
            <a href="#features">Features</a>
            <a href="#how-it-works">How It Works</a>
            <a href="#pricing">Pricing</a>
          </div>
          <button onClick={onGoToApp} className="btn-primary nav-cta">Get Started</button>
        </div>
      </nav>

      <section id="hero" className="hero" aria-labelledby="hero-title">
        <div className="hero-background">
          <canvas id="wireframe-canvas" aria-hidden="true"></canvas>
          <div className="hero-glow" aria-hidden="true"></div>
        </div>

        <div className="container hero-container" style={{ gridTemplateColumns: '1fr', textAlign: 'center' }}>
          <div className="hero-content" id="hero-content" style={{ alignItems: 'center' }}>
            <span className="eyebrow">AI-POWERED LEAD INTELLIGENCE</span>
            <h1 id="hero-title" className="hero-title">
              Find Real Leads.<br />
              <span className="highlight">Validate Ideas.</span><br />
              Build With Confidence.
            </h1>
            <p className="hero-description" style={{ margin: '0 auto 3rem auto' }}>
              Spresy discovers, enriches, and validates business leads from public sources using AI-powered search and lead intelligence.
            </p>
            <div className="hero-ctas" style={{ justifyContent: 'center' }}>
              <button onClick={onGoToApp} className="btn-primary btn-large">Start Scraping Free →</button>
              <a href="#how-it-works" className="btn-secondary btn-large">See How It Works →</a>
            </div>
          </div>
        </div>

        <div className="scroll-indicator" aria-hidden="true">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>
        </div>
      </section>

      <section id="features" className="section features" ref={(el) => { sectionRefs.current.features = el }} aria-labelledby="features-title">
        <div className="container">
          <div className="section-header">
            <span className="section-badge">Capabilities</span>
            <h2 id="features-title" className="section-title">From Search to Signal.</h2>
            <p className="section-description">Four pillars that transform raw queries into qualified opportunities.</p>
          </div>

          <div className="features-grid">
            <article className="feature-card">
              <div className="feature-icon" aria-hidden="true">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
              </div>
              <h3 className="feature-title">AI Query Expansion</h3>
              <p className="feature-description">Turn simple searches into intelligent lead discovery. Your keywords expand into comprehensive search strategies across multiple dimensions.</p>
            </article>

            <article className="feature-card">
              <div className="feature-icon" aria-hidden="true">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
              </div>
              <h3 className="feature-title">Public Source Intelligence</h3>
              <p className="feature-description">Discover relevant businesses and contacts across publicly available sources — directories, registries, search engines, and web data.</p>
            </article>

            <article className="feature-card">
              <div className="feature-icon" aria-hidden="true">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 12l2 2 4-4M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 0 1-4.255-.949L3 20l1.395-3.72C3.514 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>
              </div>
              <h3 className="feature-title">Lead Validation</h3>
              <p className="feature-description">Filter weak results and surface higher-quality prospects. Every lead is verified against multiple signals before it reaches you.</p>
            </article>

            <article className="feature-card">
              <div className="feature-icon" aria-hidden="true">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M18 20V10M12 20V4M6 20v-6"/><path d="M4 20h16"/></svg>
              </div>
              <h3 className="feature-title">AI Lead Scoring</h3>
              <p className="feature-description">Prioritize the leads most relevant to your requirements. Scores from 0–100 based on completeness, relevance, and verified contact data.</p>
            </article>
          </div>
        </div>
      </section>

      <section id="how-it-works" className="section how-it-works" ref={(el) => { sectionRefs.current.howItWorks = el }} aria-labelledby="hiw-title">
        <div className="container">
          <div className="section-header">
            <span className="section-badge">Process</span>
            <h2 id="hiw-title" className="section-title">Three Steps to Qualified Leads.</h2>
            <p className="section-description">Define your criteria. Let AI expand and search. Focus on validated results.</p>
          </div>

          <div className="steps-grid">
            <article className="step-card">
              <div className="step-number">01</div>
              <h3 className="step-title">Define</h3>
              <p className="step-description">Tell Spresy what type of leads you're looking for. Keywords, industry, location, company size — be as specific or broad as you need.</p>
            </article>

            <article className="step-card">
              <div className="step-number">02</div>
              <h3 className="step-title">Discover</h3>
              <p className="step-description">Spresy expands your query into intelligent search variations and searches relevant public sources in parallel — directories, registries, search engines, and web data.</p>
            </article>

            <article className="step-card">
              <div className="step-number">03</div>
              <h3 className="step-title">Validate</h3>
              <p className="step-description">AI analyzes, enriches, and scores every result. Verified contacts, formatted data, relevance scores — so you can focus on the strongest opportunities.</p>
            </article>
          </div>
        </div>
      </section>

      <section id="lead-intelligence" className="section lead-intelligence" ref={(el) => { sectionRefs.current.leadIntelligence = el }} aria-labelledby="li-title">
        <div className="container">
          <div className="section-header">
            <span className="section-badge">Lead Intelligence</span>
            <h2 id="li-title" className="section-title">What a Discovered Lead Looks Like.</h2>
            <p className="section-description">Every lead comes enriched with verified contact data, firmographics, and an AI relevance score.</p>
          </div>

          <div className="lead-showcase">
            <div className="lead-card">
              <div className="lead-header">
                <div>
                  <h3 className="lead-company">Meridian Solar Solutions</h3>
                  <span className="lead-industry">Renewable Energy · Commercial Installation</span>
                </div>
                <span className="lead-score high">94</span>
              </div>

              <div className="lead-fields">
                <div className="lead-field">
                  <span className="field-key">Location</span>
                  <span className="field-value">Ahmedabad, Gujarat, India</span>
                </div>
                <div className="lead-field">
                  <span className="field-key">Website</span>
                  <span className="field-value"><a href="https://meridiansolar.example.com" target="_blank" rel="noopener noreferrer" className="link">meridiansolar.example.com</a></span>
                </div>
                <div className="lead-field">
                  <span className="field-key">Email</span>
                  <span className="field-value"><a href="mailto:contact@meridiansolar.example.com" className="link">contact@meridiansolar.example.com</a></span>
                </div>
                <div className="lead-field">
                  <span className="field-key">Phone</span>
                  <span className="field-value"><a href="tel:+917940012345" className="link">+91 79 4001 2345</a></span>
                </div>
                <div className="lead-field">
                  <span className="field-key">CIN</span>
                  <span className="field-value">U40106GJ2018PTC102345</span>
                </div>
                <div className="lead-field">
                  <span className="field-key">Source</span>
                  <span className="field-value">IndiaMART · Verified</span>
                </div>
              </div>

              <div className="lead-tags">
                <span className="tag verified">Verified Email</span>
                <span className="tag verified">Verified Phone</span>
                <span className="tag">GST Registered</span>
                <span className="tag">ISO 9001</span>
              </div>

              <div className="lead-actions">
                <button className="btn-secondary">Export Lead</button>
                <button className="btn-secondary">View Full Profile</button>
              </div>
            </div>

            <div className="lead-meta">
              <div className="meta-item">
                <span className="meta-value">50+</span>
                <span className="meta-label">Data Sources Queried</span>
              </div>
              <div className="meta-item">
                <span className="meta-value">{"< 30s"}</span>
                <span className="meta-label">Average Search Time</span>
              </div>
              <div className="meta-item">
                <span className="meta-value">87%</span>
                <span className="meta-label">Email Verification Rate</span>
              </div>
              <div className="meta-item">
                <span className="meta-value">0–100</span>
                <span className="meta-label">AI Scoring Range</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="pricing" className="section pricing" ref={(el) => { sectionRefs.current.pricing = el }} aria-labelledby="pricing-title">
        <div className="container">
          <div className="section-header">
            <span className="section-badge">Pricing</span>
            <h2 id="pricing-title" className="section-title">Simple, Transparent Pricing.</h2>
            <p className="section-description">Choose the plan that matches your lead volume. All plans include AI scoring and CSV export.</p>
          </div>

          <div className="pricing-grid">
            <article className="pricing-card">
              <div className="pricing-header">
                <h3 className="plan-name">Starter</h3>
                <div className="plan-price">
                  <span className="currency">$</span>
                  <span className="amount">0</span>
                  <span className="period">/month</span>
                </div>
                <p className="plan-description">For individuals testing the waters</p>
              </div>
              <ul className="plan-features">
                <li>100 leads / month</li>
                <li>5 data sources</li>
                <li>Basic AI scoring</li>
                <li>CSV export</li>
                <li className="disabled">API access</li>
                <li className="disabled">Priority support</li>
              </ul>
              <button className="btn-secondary btn-full">Start Free</button>
            </article>

            <article className="pricing-card featured">
              <div className="plan-badge">Recommended</div>
              <div className="pricing-header">
                <h3 className="plan-name">Professional</h3>
                <div className="plan-price">
                  <span className="currency">$</span>
                  <span className="amount">49</span>
                  <span className="period">/month</span>
                </div>
                <p className="plan-description">For growing teams and agencies</p>
              </div>
              <ul className="plan-features">
                <li>5,000 leads / month</li>
                <li>All 50+ data sources</li>
                <li>Advanced AI scoring & enrichment</li>
                <li>CSV + API access</li>
                <li>Priority support</li>
                <li>Market intelligence reports</li>
              </ul>
              <button onClick={onGoToApp} className="btn-primary btn-full">Get Started</button>
            </article>

            <article className="pricing-card">
              <div className="pricing-header">
                <h3 className="plan-name">Enterprise</h3>
                <div className="plan-price">
                  <span className="amount">Custom</span>
                </div>
                <p className="plan-description">For scale, compliance, and custom needs</p>
              </div>
              <ul className="plan-features">
                <li>Unlimited leads</li>
                <li>Custom data sources</li>
                <li>Dedicated infrastructure</li>
                <li>SLA & compliance support</li>
                <li>SSO & audit logs</li>
                <li>Custom AI models</li>
              </ul>
              <button className="btn-secondary btn-full">Contact Sales</button>
            </article>
          </div>
        </div>
      </section>

      <section id="cta" className="section cta" aria-labelledby="cta-title">
        <div className="cta-background">
          <div className="cta-glow" aria-hidden="true"></div>
        </div>

        <div className="container">
          <div className="cta-content">
            <h2 id="cta-title" className="cta-title">
              Stop Searching.<br />
              Start Finding.
            </h2>
            <p className="cta-description">
              Turn ideas into validated opportunities with AI-powered lead intelligence.
            </p>
            <button onClick={onGoToApp} className="btn-primary btn-large cta-btn">Get Started →</button>
          </div>
        </div>
      </section>

      <footer className="footer" role="contentinfo">
        <div className="container">
          <div className="footer-grid">
            <div className="footer-brand">
              <a href="/" className="logo" aria-label="Spresy Home">
                <span className="logo-mark"></span>
                <span className="logo-text">Spresy</span>
              </a>
              <p className="footer-description">
                AI-powered lead discovery and validation. Built for founders, agencies, and researchers who need real data.
              </p>
              <div className="footer-social">
                <a href="#" aria-label="Twitter" className="social-link">X</a>
                <a href="#" aria-label="LinkedIn" className="social-link">in</a>
                <a href="#" aria-label="GitHub" className="social-link">GH</a>
                <a href="#" aria-label="Email" className="social-link">✉</a>
              </div>
            </div>

            <nav className="footer-nav" aria-label="Product links">
              <h4>Product</h4>
              <a href="#features">Features</a>
              <a href="#pricing">Pricing</a>
              <a href="#lead-intelligence">Lead Intelligence</a>
              <a href="#">API Docs</a>
              <a href="#">Changelog</a>
            </nav>

            <nav className="footer-nav" aria-label="Company links">
              <h4>Company</h4>
              <a href="#">About</a>
              <a href="#">Blog</a>
              <a href="#">Careers</a>
              <a href="#">Contact</a>
            </nav>

            <nav className="footer-nav" aria-label="Legal links">
              <h4>Legal</h4>
              <a href="#">Privacy Policy</a>
              <a href="#">Terms of Service</a>
              <a href="#">Data Compliance</a>
              <a href="#">Scraping Ethics</a>
            </nav>
          </div>

          <div className="footer-bottom">
            <p>© 2025 Spresy. All rights reserved. Scraping legally from public sources only.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}

function ScraperApp({ onBack }: { onBack: () => void }) {
  const [keyword, setKeyword] = useState('')
  const [location, setLocation] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingStage, setLoadingStage] = useState('Starting...')
  const [jobId, setJobId] = useState<string | null>(null)
  const [results, setResults] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)
  const [showCampaign, setShowCampaign] = useState(false)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!keyword.trim()) return

    setLoading(true)
    setError(null)
    setResults([])
    setJobId(null)
    setShowCampaign(false)

    try {
      const response = await fetch(`${API_BASE.replace(/\/$/, '')}/api/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keyword: keyword.trim(),
          location: location.trim() || undefined,
          max_leads: 50,
          use_ai: true,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to start scrape job')
      }

      const job = await response.json()
      setJobId(job.id)
      pollJob(job.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
      setLoading(false)
    }
  }

  const pollJob = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE.replace(/\/$/, '')}/api/jobs/${id}/result`)
      if (!response.ok) throw new Error('Failed to get results')

      const data = await response.json()

      if (data.progress?.message) {
        setLoadingStage(data.progress.message)
      } else if (data.status === 'running') {
        setLoadingStage('Searching for leads...')
      }

      if (data.leads && data.leads.length > 0) {
        setResults(data.leads)
      }

      if (data.status === 'running' || data.status === 'pending' || data.status === 'partial') {
        setTimeout(() => pollJob(id), 3000)
      } else {
        setLoading(false)
        if (data.leads && data.leads.length === 0) {
          setError('No leads found for this search. Try a different keyword or location.')
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch results')
      setLoading(false)
    }
  }

  return (
    <div className="app" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <nav className="navbar scrolled" style={{ position: 'relative', top: '0', maxWidth: '100%', width: '100%', borderRadius: '0', borderLeft: 'none', borderRight: 'none', borderTop: 'none', transform: 'none', left: '0' }}>
        <div className="navbar-inner" style={{ maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <button onClick={onBack} className="btn-secondary" style={{ padding: '8px 12px', border: 'none' }}>← Back</button>
            <span className="logo">
              <span className="logo-text">Spresy <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>/ App</span></span>
            </span>
          </div>
        </div>
      </nav>

      <div className="container" style={{ padding: '40px 20px', flexGrow: 1 }}>
        <div className="search-interface" style={{ maxWidth: '100%', marginBottom: '40px' }}>
          <div className="search-header">
            <div className="search-dots">
              <span></span><span></span><span></span>
            </div>
            <span className="search-title">Lead Generation Engine</span>
          </div>
          <form onSubmit={handleSearch} className="search-form" style={{ display: 'flex', gap: '20px', alignItems: 'flex-end', flexWrap: 'wrap' }} noValidate>
            <div className="search-field" style={{ flex: '1', minWidth: '300px', marginBottom: 0 }}>
              <label htmlFor="keyword" className="field-label">What are you looking for?</label>
              <input
                id="keyword"
                type="text"
                placeholder="real estate agents, plumbers, solar installers..."
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                className="field-input"
                required
                autoComplete="off"
                disabled={loading}
              />
            </div>
            <div className="search-field" style={{ flex: '1', minWidth: '300px', marginBottom: 0 }}>
              <label htmlFor="location" className="field-label">Location</label>
              <input
                id="location"
                type="text"
                placeholder="Ahmedabad, India"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="field-input"
                autoComplete="off"
                disabled={loading}
              />
            </div>
            <button type="submit" className="btn-primary search-submit" style={{ width: 'auto', marginTop: 0 }} disabled={loading || !keyword.trim()}>
              {loading ? (
                <>
                  <span className="spinner" aria-hidden="true" style={{ marginRight: '8px' }}></span>
                  Searching...
                </>
              ) : (
                'Search'
              )}
            </button>
          </form>

          {loading && (
            <div style={{ marginTop: '12px', color: 'var(--text-muted)', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="spinner" style={{ width: '12px', height: '12px', borderWidth: '2px' }}></span>
              {loadingStage}
            </div>
          )}

          {error && <div className="error-toast" role="alert" style={{ marginTop: '20px' }}>{error}</div>}
        </div>

        {(results.length > 0 || loading) && (
          <div className="results-panel" role="region" aria-label="Search results" aria-live="polite">
            <div className="results-header">
              <span className="results-title">
                Discovered Leads {results.length > 0 && `(${results.length})`}
                {loading && results.length > 0 && <span style={{ marginLeft: '8px', fontSize: '12px', color: 'var(--accent)', fontWeight: 400 }}>finding more...</span>}
              </span>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                {jobId && !loading && (
                  <a href={`${API_BASE.replace(/\/$/, '')}/api/jobs/${jobId}/csv`} className="download-link" download>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true" style={{ marginRight: '4px' }}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
                    Download CSV
                  </a>
                )}
                {results.length > 0 && !loading && jobId && (
                  <button
                    className="btn-primary"
                    style={{ padding: '8px 18px', fontSize: '13px', background: 'linear-gradient(135deg, #7c3aed, #a855f7)', borderRadius: '8px' }}
                    onClick={() => setShowCampaign(true)}
                  >
                    🚀 Start Outreach Campaign
                  </button>
                )}
              </div>
            </div>
            <div className="results-table">
              <div className="results-row header" style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 1fr 1fr 1fr 80px' }}>
                <span>Company</span>
                <span>Industry</span>
                <span>Location</span>
                <span>Website</span>
                <span>Email</span>
                <span>Phone</span>
                <span>Score</span>
              </div>
              {results.length > 0 ? (
                results.map((lead, i) => (
                  <div key={i} className="results-row" style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 1fr 1fr 1fr 80px', alignItems: 'center' }}>
                    <span className="lead-name" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{lead.name || 'N/A'}</span>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{lead.category || lead.industry || 'N/A'}</span>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{lead.city || lead.location || 'N/A'}</span>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{lead.website ? <a href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`} target="_blank" rel="noopener noreferrer" className="link">{(() => { try { return new URL(lead.website.startsWith('http') ? lead.website : `https://${lead.website}`).hostname } catch { return lead.website } })()}</a> : 'N/A'}</span>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{lead.email ? <a href={`mailto:${lead.email}`} className="link">{lead.email}</a> : 'N/A'}</span>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{lead.phone || 'N/A'}</span>
                    <span>
                      <span className={`score-badge ${lead.ai_score >= 80 ? 'high' : lead.ai_score >= 50 ? 'medium' : 'low'}`}>
                        {lead.ai_score ?? '—'}
                      </span>
                    </span>
                  </div>
                ))
              ) : (
                loading && (
                  <div className="results-row empty">
                    <span className="spinner" style={{ marginRight: '10px' }}></span>
                    <span className="empty-state">Crawling web for leads and running AI qualification...</span>
                  </div>
                )
              )}
            </div>
          </div>
        )}
      </div>

      {showCampaign && jobId && (
        <CampaignFlow
          jobId={jobId}
          onClose={() => setShowCampaign(false)}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// CampaignFlow — 3-step outreach automation modal
// ---------------------------------------------------------------------------

type CampaignStep = 'setup' | 'review' | 'send'

function CampaignFlow({ jobId, onClose }: { jobId: string; onClose: () => void }) {
  const [step, setStep] = useState<CampaignStep>('setup')
  const [campaignId, setCampaignId] = useState<string | null>(null)
  const [campaignStatus, setCampaignStatus] = useState('')
  const [messages, setMessages] = useState<any[]>([])
  const [batchResult, setBatchResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Setup form state
  const [smtpEmail, setSmtpEmail] = useState('')
  const [smtpPassword, setSmtpPassword] = useState('')
  const [smtpHost, setSmtpHost] = useState('smtp.gmail.com')
  const [smtpPort, setSmtpPort] = useState(587)
  const [senderName, setSenderName] = useState('')
  const [physicalAddress, setPhysicalAddress] = useState('')
  const [prompt, setPrompt] = useState('')
  const [uploadedFiles, setUploadedFiles] = useState<{ file_path: string; filename: string; preview: string }[]>([])
  const [uploading, setUploading] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editSubject, setEditSubject] = useState('')
  const [editBody, setEditBody] = useState('')

  // Auto-detect SMTP host from email
  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    setSmtpEmail(val)
    if (val.includes('@gmail.com')) { setSmtpHost('smtp.gmail.com'); setSmtpPort(587) }
    else if (val.includes('@outlook.com') || val.includes('@hotmail.com')) { setSmtpHost('smtp-mail.outlook.com'); setSmtpPort(587) }
    else if (val.includes('@yahoo.com')) { setSmtpHost('smtp.mail.yahoo.com'); setSmtpPort(587) }
    else if (val.includes('@zoho.com')) { setSmtpHost('smtp.zoho.com'); setSmtpPort(465) }
  }

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    setUploading(true)
    setError(null)
    try {
      const results = []
      for (const file of Array.from(files)) {
        const fd = new FormData()
        fd.append('file', file)
        const resp = await fetch(`${API_BASE.replace(/\/$/, '')}/api/upload`, { method: 'POST', body: fd })
        if (!resp.ok) throw new Error('Upload failed')
        const data = await resp.json()
        results.push({ file_path: data.file_path, filename: data.filename, preview: data.extracted_text_preview })
      }
      setUploadedFiles(prev => [...prev, ...results])
    } catch (err) {
      setError('File upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const handleCreateCampaign = async () => {
    if (!prompt.trim()) { setError('Please enter outreach instructions.'); return }
    if (!smtpEmail || !smtpPassword) { setError('Please enter your email and app password.'); return }
    setError(null)
    setBusy(true)
    try {
      // Save SMTP credentials
      const smtpFd = new FormData()
      smtpFd.append('email', smtpEmail)
      smtpFd.append('smtp_host', smtpHost)
      smtpFd.append('smtp_port', String(smtpPort))
      smtpFd.append('password', smtpPassword)
      smtpFd.append('sender_name', senderName)
      const smtpResp = await fetch(`${API_BASE.replace(/\/$/, '')}/api/smtp`, { method: 'POST', body: smtpFd })
      if (!smtpResp.ok) throw new Error('Failed to save SMTP credentials')
      const smtpData = await smtpResp.json()

      // Create campaign
      const campFd = new FormData()
      campFd.append('job_id', jobId)
      campFd.append('prompt', prompt)
      campFd.append('smtp_credential_id', smtpData.id)
      campFd.append('sender_name', senderName)
      campFd.append('physical_address', physicalAddress || 'India')
      campFd.append('doc_file_paths', uploadedFiles.map(f => f.file_path).join(','))
      campFd.append('doc_filenames', uploadedFiles.map(f => f.filename).join(','))
      const campResp = await fetch(`${API_BASE.replace(/\/$/, '')}/api/campaigns`, { method: 'POST', body: campFd })
      if (!campResp.ok) throw new Error('Failed to create campaign')
      const campData = await campResp.json()
      setCampaignId(campData.id)

      // Start message generation
      await fetch(`${API_BASE.replace(/\/$/, '')}/api/campaigns/${campData.id}/generate`, { method: 'POST' })
      setCampaignStatus('generating')
      setStep('review')
      startPolling(campData.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create campaign')
    } finally {
      setBusy(false)
    }
  }

  const startPolling = (id: string) => {
    if (pollingRef.current) clearInterval(pollingRef.current)
    pollingRef.current = setInterval(async () => {
      const resp = await fetch(`${API_BASE.replace(/\/$/, '')}/api/campaigns/${id}`)
      if (!resp.ok) return
      const data = await resp.json()
      setCampaignStatus(data.status)
      if (data.status === 'review' || data.status === 'running' || data.status === 'completed') {
        clearInterval(pollingRef.current!)
        // Load messages
        const msgResp = await fetch(`${API_BASE.replace(/\/$/, '')}/api/campaigns/${id}/messages`)
        if (msgResp.ok) setMessages(await msgResp.json())
      }
    }, 3000)
  }

  const handleApproveAll = async () => {
    if (!campaignId) return
    setBusy(true)
    try {
      await fetch(`${API_BASE.replace(/\/$/, '')}/api/campaigns/${campaignId}/approve-all`, { method: 'POST' })
      setMessages(prev => prev.map(m => m.status === 'generated' ? { ...m, status: 'approved' } : m))
      setCampaignStatus('running')
      setStep('send')
    } finally {
      setBusy(false)
    }
  }

  const handleApproveOne = async (id: string) => {
    await fetch(`${API_BASE.replace(/\/$/, '')}/api/outreach/${id}/approve`, { method: 'POST' })
    setMessages(prev => prev.map(m => m.id === id ? { ...m, status: 'approved' } : m))
  }

  const handleEditSave = async (id: string) => {
    const fd = new FormData()
    fd.append('subject', editSubject)
    fd.append('message', editBody)
    await fetch(`${API_BASE.replace(/\/$/, '')}/api/outreach/${id}`, { method: 'PUT', body: fd })
    setMessages(prev => prev.map(m => m.id === id ? { ...m, subject: editSubject, message: editBody, user_edited: true } : m))
    setEditingId(null)
  }

  const handleSendBatch = async () => {
    if (!campaignId) return
    setBusy(true)
    try {
      const resp = await fetch(`${API_BASE.replace(/\/$/, '')}/api/campaigns/${campaignId}/send-batch`, { method: 'POST' })
      const data = await resp.json()
      setBatchResult(data)
      // Refresh messages
      const msgResp = await fetch(`${API_BASE.replace(/\/$/, '')}/api/campaigns/${campaignId}/messages`)
      if (msgResp.ok) setMessages(await msgResp.json())
    } finally {
      setBusy(false)
    }
  }

  const handlePause = async () => {
    if (!campaignId) return
    await fetch(`${API_BASE.replace(/\/$/, '')}/api/campaigns/${campaignId}/pause`, { method: 'POST' })
    setCampaignStatus('paused')
  }

  useEffect(() => () => { if (pollingRef.current) clearInterval(pollingRef.current) }, [])

  const statusBadge = (s: string) => {
    const colors: Record<string, string> = {
      generated: '#7c3aed', approved: '#2563eb', claimed: '#d97706',
      sent: '#16a34a', failed: '#dc2626', bounced: '#9a3412',
      skipped: '#6b7280', pending: '#6b7280',
    }
    return (
      <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
        background: (colors[s] || '#6b7280') + '22', color: colors[s] || '#6b7280', textTransform: 'uppercase' }}>
        {s}
      </span>
    )
  }

  const approvedCount = messages.filter(m => m.status === 'approved').length
  const generatedCount = messages.filter(m => m.status === 'generated').length
  const sentCount = messages.filter(m => m.status === 'sent').length
  const skippedCount = messages.filter(m => m.status === 'skipped').length

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
      padding: '20px', overflowY: 'auto',
    }}>
      <div style={{
        background: 'var(--surface)', borderRadius: '16px', border: '1px solid var(--border)',
        width: '100%', maxWidth: '860px', maxHeight: '90vh', overflow: 'hidden',
        display: 'flex', flexDirection: 'column', marginTop: '20px',
        boxShadow: '0 25px 80px rgba(0,0,0,0.5)',
      }}>
        {/* Header */}
        <div style={{ padding: '24px 28px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700 }}>
              {step === 'setup' ? '🚀 Create Outreach Campaign' : step === 'review' ? '✍️ Review Messages' : '📤 Send Campaign'}
            </h2>
            <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
              {(['setup', 'review', 'send'] as CampaignStep[]).map((s, i) => (
                <div key={s} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <div style={{ width: '24px', height: '24px', borderRadius: '50%', fontSize: '12px', fontWeight: 700,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: step === s ? 'var(--accent)' : ((['setup', 'review', 'send'].indexOf(step) > i) ? '#16a34a' : 'var(--border)'),
                    color: step === s || (['setup', 'review', 'send'].indexOf(step) > i) ? 'white' : 'var(--text-muted)',
                  }}>{i + 1}</div>
                  <span style={{ fontSize: '12px', color: step === s ? 'var(--text)' : 'var(--text-muted)', textTransform: 'capitalize' }}>{s}</span>
                  {i < 2 && <span style={{ color: 'var(--border)', margin: '0 4px' }}>›</span>}
                </div>
              ))}
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: '20px', lineHeight: 1 }}>✕</button>
        </div>

        {/* Body */}
        <div style={{ overflowY: 'auto', padding: '28px', flexGrow: 1 }}>
          {error && <div className="error-toast" style={{ marginBottom: '20px' }}>{error}</div>}

          {/* ---- STEP 1: SETUP ---- */}
          {step === 'setup' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>

              {/* Email Settings */}
              <section>
                <h3 style={{ margin: '0 0 16px', fontSize: '15px', fontWeight: 600, color: 'var(--accent)' }}>📧 Email Settings</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                  <div>
                    <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Your Email *</label>
                    <input className="field-input" type="email" placeholder="you@gmail.com" value={smtpEmail} onChange={handleEmailChange} style={{ width: '100%' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                      App Password * <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent)', fontSize: '11px' }}>Get Gmail App Password →</a>
                    </label>
                    <input className="field-input" type="password" placeholder="xxxx xxxx xxxx xxxx" value={smtpPassword} onChange={e => setSmtpPassword(e.target.value)} style={{ width: '100%' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Display Name</label>
                    <input className="field-input" type="text" placeholder="Yash Dave" value={senderName} onChange={e => setSenderName(e.target.value)} style={{ width: '100%' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Physical Address <span style={{ fontSize: '10px' }}>(CAN-SPAM required)</span></label>
                    <input className="field-input" type="text" placeholder="123 Main St, Ahmedabad, India" value={physicalAddress} onChange={e => setPhysicalAddress(e.target.value)} style={{ width: '100%' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>SMTP Host</label>
                    <input className="field-input" type="text" value={smtpHost} onChange={e => setSmtpHost(e.target.value)} style={{ width: '100%' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>SMTP Port</label>
                    <input className="field-input" type="number" value={smtpPort} onChange={e => setSmtpPort(Number(e.target.value))} style={{ width: '100%' }} />
                  </div>
                </div>
              </section>

              {/* Document Upload */}
              <section>
                <h3 style={{ margin: '0 0 16px', fontSize: '15px', fontWeight: 600, color: 'var(--accent)' }}>📎 Upload Documents</h3>
                <div
                  style={{ border: '2px dashed var(--border)', borderRadius: '12px', padding: '32px', textAlign: 'center', cursor: 'pointer', transition: 'border-color 0.2s', position: 'relative' }}
                  onDragOver={e => { e.preventDefault(); (e.currentTarget as HTMLElement).style.borderColor = 'var(--accent)' }}
                  onDragLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)' }}
                  onDrop={async e => { e.preventDefault(); (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)'; await handleFileUpload(e.dataTransfer.files) }}
                  onClick={() => document.getElementById('doc-upload-input')?.click()}
                >
                  <input id="doc-upload-input" type="file" multiple accept=".pdf,.docx,.doc,.txt,.md,.png,.jpg,.jpeg" style={{ display: 'none' }} onChange={e => handleFileUpload(e.target.files)} />
                  {uploading ? (
                    <><span className="spinner" style={{ marginRight: '8px' }}></span>Uploading...</>
                  ) : (
                    <>
                      <div style={{ fontSize: '32px', marginBottom: '8px' }}>📄</div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Drop files here or click to browse</div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '4px' }}>PDF, DOCX, TXT, images — resume, portfolio, pitch deck</div>
                    </>
                  )}
                </div>
                {uploadedFiles.length > 0 && (
                  <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {uploadedFiles.map((f, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px', background: 'var(--surface-alt)', borderRadius: '8px', fontSize: '13px' }}>
                        <span>📄</span>
                        <span style={{ fontWeight: 500 }}>{f.filename}</span>
                        <span style={{ color: 'var(--text-muted)', fontSize: '11px', flexGrow: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.preview}</span>
                        <button onClick={() => setUploadedFiles(prev => prev.filter((_, j) => j !== i))} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: '14px' }}>✕</button>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {/* Prompt */}
              <section>
                <h3 style={{ margin: '0 0 16px', fontSize: '15px', fontWeight: 600, color: 'var(--accent)' }}>✨ Outreach Instructions</h3>
                <textarea
                  className="field-input"
                  rows={5}
                  style={{ width: '100%', resize: 'vertical', fontFamily: 'inherit' }}
                  placeholder={`Example: "I'm a full-stack developer with 3 years of experience in React and Node.js. I'm looking for a junior/mid-level developer role. Please write a personalized cold email applying to each company, referencing my resume, and asking about open positions."`}
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                />
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px' }}>
                  AI will read your documents and use these instructions to craft a unique message for each lead.
                </div>
              </section>
            </div>
          )}

          {/* ---- STEP 2: REVIEW ---- */}
          {step === 'review' && (
            <div>
              {campaignStatus === 'generating' && (
                <div style={{ textAlign: 'center', padding: '40px 0' }}>
                  <span className="spinner" style={{ width: '32px', height: '32px', borderWidth: '3px', marginBottom: '16px', display: 'inline-block' }}></span>
                  <div style={{ fontSize: '16px', fontWeight: 500 }}>AI is writing personalized messages...</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '8px' }}>Validating emails, checking suppression list, and crafting unique outreach for each lead.</div>
                </div>
              )}
              {messages.length > 0 && (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
                    <div style={{ display: 'flex', gap: '16px', fontSize: '13px' }}>
                      <span>✅ <strong>{generatedCount}</strong> ready</span>
                      <span>⏭️ <strong>{skippedCount}</strong> skipped</span>
                      <span>🔵 <strong>{approvedCount}</strong> approved</span>
                    </div>
                    {generatedCount > 0 && (
                      <button className="btn-primary" style={{ padding: '8px 20px', fontSize: '13px' }} onClick={handleApproveAll} disabled={busy}>
                        {busy ? 'Approving...' : `Approve All (${generatedCount}) & Continue →`}
                      </button>
                    )}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {messages.map(m => (
                      <div key={m.id} style={{ border: '1px solid var(--border)', borderRadius: '10px', overflow: 'hidden' }}>
                        <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: '12px', background: 'var(--surface-alt)' }}>
                          <div style={{ flexGrow: 1 }}>
                            <span style={{ fontWeight: 600, fontSize: '14px' }}>{m.lead_name || 'Unknown'}</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '12px', marginLeft: '10px' }}>{m.to_email || 'no email'}</span>
                            {m.user_edited && <span style={{ marginLeft: '8px', fontSize: '10px', color: '#a855f7', fontWeight: 600 }}>EDITED</span>}
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {statusBadge(m.status)}
                            {m.status === 'generated' && (
                              <>
                                <button onClick={() => { setEditingId(m.id); setEditSubject(m.subject || ''); setEditBody(m.message || '') }}
                                  style={{ background: 'none', border: '1px solid var(--border)', borderRadius: '6px', padding: '3px 10px', cursor: 'pointer', fontSize: '12px', color: 'var(--text-muted)' }}>
                                  Edit
                                </button>
                                <button onClick={() => handleApproveOne(m.id)}
                                  style={{ background: 'var(--accent)', border: 'none', borderRadius: '6px', padding: '3px 10px', cursor: 'pointer', fontSize: '12px', color: 'white', fontWeight: 600 }}>
                                  Approve
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                        {m.status !== 'skipped' && (
                          <div style={{ padding: '12px 16px' }}>
                            {editingId === m.id ? (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                <input className="field-input" value={editSubject} onChange={e => setEditSubject(e.target.value)} placeholder="Subject" style={{ fontSize: '13px' }} />
                                <textarea className="field-input" rows={6} value={editBody} onChange={e => setEditBody(e.target.value)} style={{ fontSize: '13px', resize: 'vertical', fontFamily: 'inherit' }} />
                                <div style={{ display: 'flex', gap: '8px' }}>
                                  <button className="btn-primary" style={{ padding: '6px 16px', fontSize: '12px' }} onClick={() => handleEditSave(m.id)}>Save</button>
                                  <button onClick={() => setEditingId(null)} style={{ background: 'none', border: '1px solid var(--border)', borderRadius: '6px', padding: '6px 16px', cursor: 'pointer', fontSize: '12px', color: 'var(--text-muted)' }}>Cancel</button>
                                </div>
                              </div>
                            ) : (
                              <>
                                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>Subject: <strong>{m.subject || '—'}</strong></div>
                                <div style={{ fontSize: '13px', whiteSpace: 'pre-wrap', color: 'var(--text)', lineHeight: 1.6 }}>{m.message || m.skip_reason || '—'}</div>
                              </>
                            )}
                          </div>
                        )}
                        {m.status === 'skipped' && (
                          <div style={{ padding: '10px 16px', fontSize: '12px', color: 'var(--text-muted)' }}>
                            Skipped: {m.skip_reason || 'unknown reason'}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* ---- STEP 3: SEND ---- */}
          {step === 'send' && (
            <div>
              {/* Stats */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '28px' }}>
                {[
                  { label: 'Sent', value: messages.filter(m => m.status === 'sent').length, color: '#16a34a' },
                  { label: 'Pending', value: messages.filter(m => m.status === 'approved').length, color: '#2563eb' },
                  { label: 'Failed', value: messages.filter(m => m.status === 'failed').length, color: '#dc2626' },
                  { label: 'Daily Quota Left', value: batchResult?.daily_remaining ?? '—', color: 'var(--accent)' },
                ].map(stat => (
                  <div key={stat.label} style={{ padding: '16px', background: 'var(--surface-alt)', borderRadius: '10px', border: '1px solid var(--border)', textAlign: 'center' }}>
                    <div style={{ fontSize: '28px', fontWeight: 700, color: stat.color }}>{stat.value}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>{stat.label}</div>
                  </div>
                ))}
              </div>

              {batchResult && (
                <div style={{ padding: '12px 16px', borderRadius: '8px', background: '#16a34a22', border: '1px solid #16a34a44', marginBottom: '20px', fontSize: '13px' }}>
                  Last batch: <strong>{batchResult.sent} sent</strong>, {batchResult.failed} failed, {batchResult.bounced} bounced, {batchResult.remaining} remaining
                  {batchResult.limit_reached && <span style={{ color: '#dc2626', marginLeft: '8px' }}>⚠️ Daily limit reached</span>}
                </div>
              )}

              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <button
                  className="btn-primary"
                  style={{ padding: '12px 28px', fontSize: '15px', background: 'linear-gradient(135deg, #16a34a, #15803d)' }}
                  onClick={handleSendBatch}
                  disabled={busy || messages.filter(m => m.status === 'approved').length === 0}
                >
                  {busy ? <><span className="spinner" style={{ marginRight: '8px', borderTopColor: 'white' }}></span>Sending...</> : '📤 Send Next Batch (5)'}
                </button>
                <button
                  onClick={handlePause}
                  style={{ padding: '12px 24px', fontSize: '14px', background: 'none', border: '1px solid var(--border)', borderRadius: '10px', cursor: 'pointer', color: 'var(--text-muted)' }}
                >
                  ⏸ Pause
                </button>
              </div>

              {/* Message list */}
              <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {messages.filter(m => m.status !== 'skipped').map(m => (
                  <div key={m.id} style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 14px', background: 'var(--surface-alt)', borderRadius: '8px', fontSize: '13px' }}>
                    <span style={{ fontWeight: 500, flexGrow: 1 }}>{m.lead_name}</span>
                    <span style={{ color: 'var(--text-muted)' }}>{m.to_email}</span>
                    {statusBadge(m.status)}
                    {m.status === 'failed' && (
                      <button onClick={() => handleApproveOne(m.id)} style={{ background: 'none', border: '1px solid var(--border)', borderRadius: '6px', padding: '2px 8px', cursor: 'pointer', fontSize: '11px', color: 'var(--text-muted)' }}>Retry</button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: '16px 28px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
          <button onClick={onClose} style={{ background: 'none', border: '1px solid var(--border)', borderRadius: '8px', padding: '8px 18px', cursor: 'pointer', color: 'var(--text-muted)', fontSize: '13px' }}>Close</button>
          {step === 'setup' && (
            <button className="btn-primary" onClick={handleCreateCampaign} disabled={busy || !prompt.trim() || !smtpEmail || !smtpPassword}>
              {busy ? <><span className="spinner" style={{ marginRight: '8px' }}></span>Creating...</> : 'Generate Messages →'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}