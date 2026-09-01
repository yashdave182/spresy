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

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!keyword.trim()) return

    setLoading(true)
    setError(null)
    setResults([])
    setJobId(null)

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

      // Update progress message for the user
      if (data.progress?.message) {
        setLoadingStage(data.progress.message)
      } else if (data.status === 'running') {
        setLoadingStage('Searching for leads...')
      }

      // Show partial leads immediately as they arrive
      if (data.leads && data.leads.length > 0) {
        setResults(data.leads)
      }

      // Keep polling until the job is fully done
      if (data.status === 'running' || data.status === 'pending' || data.status === 'partial') {
        setTimeout(() => pollJob(id), 3000)
      } else {
        // Job is completed or failed — stop polling
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
              {jobId && !loading && (
                <a href={`${API_BASE.replace(/\/$/, '')}/api/jobs/${jobId}/csv`} className="download-link" download>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true" style={{ marginRight: '4px' }}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
                  Download CSV
                </a>
              )}
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
    </div>
  )
}