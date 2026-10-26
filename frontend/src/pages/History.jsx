import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  History as HistoryIcon,
  Search,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Copy,
  Check,
  ChevronRight,
  Shield,
  Activity,
  Terminal,
  FileCode,
  Clock,
  RefreshCw,
  Hash,
  ArrowLeft,
  Server,
  Cloud,
  Laptop
} from 'lucide-react'
import client from '../api/client'
import Navbar from '../components/Navbar'

export default function History() {
  const [investigations, setInvestigations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [selectedClusterFilter, setSelectedClusterFilter] = useState('all')
  const [selectedInv, setSelectedInv] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [copiedCmd, setCopiedCmd] = useState(null)

  const clusterOptions = [
    { id: 'all', label: 'All Clusters', icon: Server },
    { id: 'local-kind', label: 'kind (kubevora-cluster)', icon: Laptop, isLocal: true },
    { id: 'aws-eks-staging', label: 'eks-staging-us-east-1', icon: Cloud },
    { id: 'gke-prod-primary', label: 'gke-prod-primary-eu-west-1', icon: Cloud }
  ]

  const fetchHistory = async () => {
    setLoading(true)
    setError(null)
    try {
      const url = selectedClusterFilter !== 'all'
        ? `/investigations?cluster_id=${selectedClusterFilter}`
        : '/investigations'
      const res = await client.get(url)
      const data = res.data || []
      setInvestigations(data)
      if (data.length > 0 && !selectedInv) {
        handleSelectInvestigation(data[0].id)
      }
    } catch (err) {
      console.error('Failed to fetch investigations:', err)
      setError('Unable to load investigation history from database.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [selectedClusterFilter])

  const handleSelectInvestigation = async (id) => {
    setLoadingDetail(true)
    try {
      const res = await client.get(`/investigations/${id}`)
      setSelectedInv(res.data)
    } catch (err) {
      console.error('Failed to fetch details:', err)
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleCopy = (text, id) => {
    navigator.clipboard.writeText(text)
    setCopiedCmd(id)
    setTimeout(() => setCopiedCmd(null), 2000)
  }

  const filtered = investigations.filter(inv => {
    const q = search.toLowerCase()
    const matchesSearch =
      (inv.id && inv.id.toLowerCase().includes(q)) ||
      (inv.namespace && inv.namespace.toLowerCase().includes(q)) ||
      (inv.root_cause && inv.root_cause.toLowerCase().includes(q)) ||
      (inv.fingerprint && inv.fingerprint.toLowerCase().includes(q)) ||
      (inv.cluster_context && inv.cluster_context.toLowerCase().includes(q))

    const matchesCluster =
      selectedClusterFilter === 'all' ||
      inv.cluster_context === selectedClusterFilter ||
      (!inv.cluster_context && selectedClusterFilter === 'local-kind')

    return matchesSearch && matchesCluster
  })

  const formatClusterBadge = (clusterContext) => {
    if (!clusterContext || clusterContext === 'local-kind' || clusterContext === 'default') {
      return {
        label: 'kind (kubevora-cluster)',
        badge: 'Local Kind',
        className: 'bg-cyan-50 text-cyan-800 border-cyan-200'
      }
    }
    if (clusterContext.includes('eks')) {
      return {
        label: 'eks-staging-us-east-1',
        badge: 'AWS EKS',
        className: 'bg-amber-50 text-amber-800 border-amber-200'
      }
    }
    if (clusterContext.includes('gke')) {
      return {
        label: 'gke-prod-primary-eu-west-1',
        badge: 'GCP GKE',
        className: 'bg-indigo-50 text-indigo-800 border-indigo-200'
      }
    }
    return {
      label: clusterContext,
      badge: 'Kubernetes',
      className: 'bg-slate-100 text-slate-700 border-slate-200'
    }
  }

  return (
    <div className="min-h-screen bg-slate-50/70 text-slate-800 flex flex-col font-sans">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-6 sm:px-8 py-8 space-y-7">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div>
            <div className="flex items-center gap-3">
              <Link
                to="/dashboard"
                className="px-3.5 py-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 hover:text-slate-900 transition-colors flex items-center gap-2 text-xs font-semibold shadow-xs"
                title="Back to Operations Console"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Console</span>
              </Link>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5 font-display">
                <HistoryIcon className="w-6 h-6 text-indigo-600" />
                Investigation History
              </h1>
            </div>
            <p className="text-xs text-slate-500 mt-1 font-medium">
              Historical Kubernetes incident reports, root causes, and incident fingerprints persisted in PostgreSQL.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search root cause, namespace, fingerprint..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="pl-9 pr-4 py-2 rounded-xl bg-white border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-500 w-80 shadow-xs transition-all"
              />
            </div>
            <button
              onClick={fetchHistory}
              disabled={loading}
              className="p-2.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-600 hover:text-slate-900 transition-colors shadow-xs cursor-pointer"
              title="Refresh History"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-600' : ''}`} />
            </button>
          </div>
        </div>

        {/* Cluster Filter Tabs */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-slate-200/80">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mr-1.5 font-display">Cluster:</span>
          {clusterOptions.map(opt => {
            const Icon = opt.icon
            const isSelected = selectedClusterFilter === opt.id
            return (
              <button
                key={opt.id}
                onClick={() => setSelectedClusterFilter(opt.id)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer whitespace-nowrap ${
                  isSelected
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-white hover:bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200 shadow-xs'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{opt.label}</span>
              </button>
            )
          })}
        </div>

        {/* Content Section */}
        {loading ? (
          <div className="text-center py-24 bg-white rounded-3xl border border-slate-200 shadow-xs">
            <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-3" />
            <p className="text-sm text-slate-500 font-medium">Loading persisted investigation records from PostgreSQL...</p>
          </div>
        ) : error ? (
          <div className="p-6 bg-rose-50 border border-rose-200 rounded-3xl text-rose-700 text-sm">
            {error}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-24 bg-white rounded-3xl border border-slate-200 shadow-xs">
            <Activity className="w-10 h-10 text-slate-400 mx-auto mb-3" />
            <h3 className="text-base font-bold text-slate-900 font-display">No Investigations Found</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-5">
              No historical incident reports recorded for {selectedClusterFilter === 'all' ? 'any cluster' : selectedClusterFilter}.
            </p>
            <Link
              to="/dashboard"
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold inline-flex items-center gap-2 shadow-xs transition-all"
            >
              Go to Dashboard to Investigate
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-7 items-start">
            {/* Investigations List */}
            <div className="lg:col-span-7 space-y-3.5">
              {filtered.map(inv => {
                const isSelected = selectedInv?.id === inv.id
                const clusterInfo = formatClusterBadge(inv.cluster_context)

                return (
                  <div
                    key={inv.id}
                    onClick={() => handleSelectInvestigation(inv.id)}
                    className={`p-5 rounded-2xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-indigo-50/70 border-indigo-300 shadow-md shadow-indigo-500/5'
                        : 'bg-white border-slate-200/90 hover:border-slate-300 hover:bg-slate-50/80 shadow-xs'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3 mb-2.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs font-bold text-indigo-700">{inv.id}</span>
                        <span className={`text-[10px] px-2 py-0.5 rounded-md font-bold border ${clusterInfo.className}`}>
                          {clusterInfo.badge}
                        </span>
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 font-mono font-medium">
                          ns/{inv.namespace}
                        </span>
                        <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                          inv.status === 'completed'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-amber-50 text-amber-700 border border-amber-200'
                        }`}>
                          {inv.status}
                        </span>
                      </div>

                      <span className="text-[11px] text-slate-400 flex items-center gap-1 font-mono shrink-0">
                        <Clock className="w-3 h-3" />
                        {inv.created_at ? new Date(inv.created_at).toLocaleString() : 'Recent'}
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-slate-900 mb-2.5 line-clamp-2 font-display">
                      {inv.root_cause || inv.title}
                    </h4>

                    <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-100">
                      <div className="flex items-center gap-3">
                        {inv.confidence_pct ? (
                          <span className="flex items-center gap-1 text-emerald-700 font-mono font-bold bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                            <Shield className="w-3.5 h-3.5 text-emerald-600" />
                            {inv.confidence_pct}% Confidence
                          </span>
                        ) : null}
                        {inv.fingerprint && inv.fingerprint !== 'none' ? (
                          <span className="flex items-center gap-1 font-mono text-[11px] text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                            <Hash className="w-3 h-3 text-slate-400" />
                            {inv.fingerprint}
                          </span>
                        ) : null}
                      </div>

                      <div className="flex items-center gap-1 text-indigo-600 font-bold text-xs">
                        View Details <ChevronRight className="w-3.5 h-3.5" />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Selected Investigation Detail Panel */}
            <div className="lg:col-span-5">
              {loadingDetail ? (
                <div className="p-10 rounded-3xl bg-white border border-slate-200 text-center shadow-xs">
                  <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin mx-auto mb-2" />
                  <p className="text-xs text-slate-500 font-medium">Loading full report & evidence...</p>
                </div>
              ) : selectedInv ? (
                <div className="p-6 rounded-3xl bg-white border border-slate-200 shadow-sm space-y-5 sticky top-24">
                  {/* Header */}
                  <div className="border-b border-slate-100 pb-4 space-y-2">
                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span className="font-mono text-indigo-700 font-bold">{selectedInv.id}</span>
                      <span className="text-slate-400 font-mono">
                        {selectedInv.created_at ? new Date(selectedInv.created_at).toLocaleString() : ''}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-2 py-0.5 rounded-md font-bold border ${formatClusterBadge(selectedInv.cluster_context).className}`}>
                        {formatClusterBadge(selectedInv.cluster_context).label}
                      </span>
                      <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 font-mono font-medium">
                        ns/{selectedInv.namespace}
                      </span>
                    </div>
                    <h3 className="text-sm font-black text-slate-900 pt-1 font-display">
                      {selectedInv.root_cause || selectedInv.title}
                    </h3>
                  </div>

                  {/* SRE Detailed Explanation */}
                  {selectedInv.explanation ? (
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5 flex items-center gap-1.5 font-display">
                        <Activity className="w-3.5 h-3.5 text-indigo-600" />
                        Senior SRE Explanation
                      </h4>
                      <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-2xl border border-slate-200 font-sans">
                        {selectedInv.explanation}
                      </p>
                    </div>
                  ) : null}

                  {/* Supporting Evidence Breakdown */}
                  {selectedInv.findings && selectedInv.findings.length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 font-display">Correlated Evidence</h4>
                      <div className="space-y-2 max-h-40 overflow-y-auto">
                        {selectedInv.findings.map((f, i) => (
                          <div key={i} className="p-3 rounded-xl bg-slate-50 text-[11px] border border-slate-200 text-slate-700">
                            <span className="font-mono text-indigo-700 font-bold">{f.resource_name}: </span>
                            <span className="text-slate-600">{f.summary || f.evidence_detail}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Suggested Safe Fix */}
                  {selectedInv.suggested_fix ? (
                    <div>
                      <h4 className="text-xs font-bold text-emerald-700 uppercase tracking-wider mb-1.5 flex items-center gap-1.5 font-display">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        Suggested Safe Fix
                      </h4>
                      <p className="text-xs text-emerald-950 leading-relaxed bg-emerald-50/70 border border-emerald-200 p-4 rounded-2xl whitespace-pre-line font-sans">
                        {selectedInv.suggested_fix}
                      </p>
                    </div>
                  ) : null}

                  {/* Recommended Kubectl Commands */}
                  {selectedInv.kubectl_commands && selectedInv.kubectl_commands.length > 0 ? (
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5 font-display">
                        <Terminal className="w-3.5 h-3.5 text-indigo-600" />
                        Recommended Kubectl Commands
                      </h4>
                      <div className="space-y-2.5">
                        {selectedInv.kubectl_commands.map((cmdObj, i) => (
                          <div key={i} className="bg-slate-900 rounded-2xl p-3 border border-slate-800 text-slate-100 shadow-xs">
                            <div className="flex items-center justify-between text-[11px] mb-1.5">
                              <span className="text-slate-300 font-medium">{cmdObj.purpose}</span>
                              <span className={`text-[9px] uppercase px-1.5 py-0.2 rounded font-bold ${
                                cmdObj.risk === 'read-only' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              }`}>
                                {cmdObj.risk}
                              </span>
                            </div>
                            <div className="flex items-center justify-between gap-2 font-mono text-xs text-cyan-300 bg-slate-950 px-3 py-2 rounded-xl border border-slate-800">
                              <code className="truncate">{cmdObj.command}</code>
                              <button
                                onClick={() => handleCopy(cmdObj.command, `hist-cmd-${i}`)}
                                className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition-colors cursor-pointer"
                                title="Copy command"
                              >
                                {copiedCmd === `hist-cmd-${i}` ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {/* YAML Diff Proposal */}
                  {selectedInv.yaml_proposal ? (
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5 font-display">
                        <FileCode className="w-3.5 h-3.5 text-purple-600" />
                        Proposed YAML Change
                      </h4>
                      <pre className="text-xs font-mono text-purple-200 bg-slate-950 p-4 rounded-2xl border border-slate-800 overflow-x-auto max-h-40">
                        {selectedInv.yaml_proposal}
                      </pre>
                    </div>
                  ) : null}

                  {/* Incident Fingerprint & Metadata */}
                  <div className="pt-3 border-t border-slate-100 text-xs text-slate-500 flex items-center justify-between">
                    <span className="font-medium">Incident Fingerprint:</span>
                    <span className="font-mono text-indigo-700 font-bold bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">{selectedInv.fingerprint || 'none'}</span>
                  </div>
                </div>
              ) : (
                <div className="p-10 rounded-3xl bg-white border border-slate-200 text-center text-slate-400 text-xs shadow-xs font-medium">
                  Select an investigation from the list to view its complete root-cause analysis and copyable commands.
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
