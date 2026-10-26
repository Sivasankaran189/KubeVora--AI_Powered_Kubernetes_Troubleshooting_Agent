import React, { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import { streamInvestigation } from '../services/sseClient'
import {
  Activity,
  AlertTriangle,
  Boxes,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  ExternalLink,
  Eye,
  FileCode,
  Filter,
  Flame,
  GitBranch,
  Hash,
  HeartPulse,
  Layers,
  Plus,
  RefreshCw,
  Search,
  Server,
  ShieldAlert,
  Sparkles,
  Terminal,
  Wrench,
  X,
  Zap,
  Copy,
  Check,
  Shield,
  ChevronDown,
  Cloud,
  Laptop
} from 'lucide-react'

export const Dashboard = () => {
  const { user } = useAuth()

  // Clusters Fleet State
  const [clusters, setClusters] = useState([
    {
      id: 'local-kind',
      name: 'kind (kubevora-cluster)',
      provider: 'Local Docker / kind',
      region: 'localhost',
      status: 'Online (Degraded Workload Detected)',
      is_local: true,
      node_count: 1
    },
    {
      id: 'aws-eks-staging',
      name: 'eks-staging-us-east-1',
      provider: 'AWS EKS (Staging Grid)',
      region: 'us-east-1',
      status: 'Online',
      is_local: false,
      node_count: 3
    },
    {
      id: 'gke-prod-primary',
      name: 'gke-prod-primary-eu-west-1',
      provider: 'Google Cloud GKE (Production Primary)',
      region: 'europe-west1',
      status: 'Degraded (OOM Incident)',
      is_local: false,
      node_count: 5
    }
  ])
  const [selectedClusterId, setSelectedClusterId] = useState('local-kind')
  const [clusterDropdownOpen, setClusterDropdownOpen] = useState(false)

  // Cluster Telemetry State
  const [clusterStatus, setClusterStatus] = useState(null)
  const [namespaces, setNamespaces] = useState([])
  const [selectedNamespace, setSelectedNamespace] = useState('all-namespaces')
  const [workloads, setWorkloads] = useState([])
  const [events, setEvents] = useState([])
  const [searchQuery, setSearchQuery] = useState('')

  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [showLogsModal, setShowLogsModal] = useState(null)

  // Live SSE Investigation State
  const [investigationState, setInvestigationState] = useState('idle') // idle, running, completed, failed
  const [investigationStage, setInvestigationStage] = useState('started')
  const [investigationMessage, setInvestigationMessage] = useState('')
  const [liveDiagnosis, setLiveDiagnosis] = useState(null)
  const [completedPayload, setCompletedPayload] = useState(null)
  const [copiedCmd, setCopiedCmd] = useState(null)

  // Fetch Clusters Catalog
  useEffect(() => {
    const fetchClusterList = async () => {
      try {
        const res = await client.get('/clusters/list')
        if (res.data && res.data.length > 0) {
          setClusters(res.data)
        }
      } catch (err) {
        console.warn('Could not fetch cluster catalog, using defaults:', err)
      }
    }
    fetchClusterList()
  }, [])

  // Fetch Cluster Data for selectedClusterId and selectedNamespace
  const fetchClusterData = useCallback(async (isSilent = false) => {
    if (!isSilent) setRefreshing(true)
    try {
      const nsQuery = selectedNamespace !== 'all-namespaces' ? `&namespace=${selectedNamespace}` : ''

      const [statusRes, nsRes, wkldRes, evtRes] = await Promise.all([
        client.get(`/clusters/status?cluster_id=${selectedClusterId}`),
        client.get(`/clusters/namespaces?cluster_id=${selectedClusterId}`),
        client.get(`/clusters/workloads?cluster_id=${selectedClusterId}${nsQuery}`),
        client.get(`/clusters/events?cluster_id=${selectedClusterId}${nsQuery}`)
      ])

      setClusterStatus(statusRes.data)
      setNamespaces(nsRes.data || [])
      setWorkloads(wkldRes.data || [])
      setEvents(evtRes.data || [])
    } catch (err) {
      console.error('Failed to load cluster telemetry data:', err)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [selectedClusterId, selectedNamespace])

  useEffect(() => {
    fetchClusterData()
  }, [fetchClusterData])

  // Handle Cluster Switch
  const handleSelectCluster = (clusterId) => {
    setSelectedClusterId(clusterId)
    setSelectedNamespace('all-namespaces')
    setClusterDropdownOpen(false)
    setLiveDiagnosis(null)
    setInvestigationState('idle')
  }

  // Handle SSE Investigation Stream
  const handleRunInvestigation = async () => {
    if (investigationState === 'running') return
    setInvestigationState('running')
    setInvestigationStage('started')
    setInvestigationMessage(`Initiating deep Kubernetes telemetry collection on ${selectedClusterId}...`)
    setLiveDiagnosis(null)
    setCompletedPayload(null)

    try {
      await streamInvestigation({
        clusterId: selectedClusterId,
        namespace: selectedNamespace,
        includeLogs: true,
        onProgress: (evt) => {
          setInvestigationStage(evt.stage)
          setInvestigationMessage(evt.message || `Processing ${evt.stage}...`)
        },
        onComplete: (data) => {
          setInvestigationState('completed')
          setLiveDiagnosis(data.diagnosis)
          setCompletedPayload(data)
          fetchClusterData(true)
        },
        onError: (err) => {
          setInvestigationState('failed')
          setInvestigationMessage(err.message || 'Investigation error encountered')
        }
      })
    } catch (err) {
      setInvestigationState('failed')
      setInvestigationMessage(err.message || 'Streaming telemetry failed')
    }
  }

  const handleCopyCmd = (text, id) => {
    navigator.clipboard.writeText(text)
    setCopiedCmd(id)
    setTimeout(() => setCopiedCmd(null), 2000)
  }

  const handleQuickTroubleshoot = (workload) => {
    setSelectedNamespace(workload.namespace)
    handleRunInvestigation()
  }

  const currentCluster = clusters.find(c => c.id === selectedClusterId) || clusters[0]

  // Filter workloads by search
  const filteredWorkloads = workloads.filter(w =>
    w.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    w.kind.toLowerCase().includes(searchQuery.toLowerCase()) ||
    w.status.toLowerCase().includes(searchQuery.toLowerCase()) ||
    w.namespace.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getStatusBadge = (status) => {
    switch (status) {
      case 'Running':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200'
      case 'CrashLoopBackOff':
        return 'bg-rose-50 text-rose-700 border-rose-300 font-bold animate-pulse'
      case 'ImagePullBackOff':
      case 'ErrImagePull':
        return 'bg-amber-50 text-amber-700 border-amber-300 font-bold'
      case 'Pending':
        return 'bg-blue-50 text-blue-700 border-blue-200'
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200'
    }
  }

  return (
    <div className="min-h-screen bg-slate-50/70 text-slate-800 pb-24 font-sans">
      {/* =========================================================================
          Top Control Ribbon: Cluster Fleet Selector & Primary Live Actions
      ========================================================================= */}
      <div className="bg-white/95 backdrop-blur-md border-b border-slate-200/90 px-6 sm:px-8 py-5 sticky top-16 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-5">
          
          {/* Cluster Fleet Selector Dropdown */}
          <div className="relative">
            <div className="flex items-center gap-3">
              <span className="text-xs uppercase font-extrabold tracking-wider text-slate-400 font-display">Target Cluster:</span>
              <button
                onClick={() => setClusterDropdownOpen(!clusterDropdownOpen)}
                className="flex items-center gap-3 px-4 py-2.5 rounded-2xl bg-white hover:bg-slate-50 border border-slate-300 hover:border-indigo-400 text-slate-800 transition-all shadow-xs cursor-pointer"
              >
                <div className="w-7 h-7 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
                  {currentCluster.is_local ? <Laptop className="w-4 h-4 text-cyan-600" /> : <Cloud className="w-4 h-4 text-indigo-600" />}
                </div>
                <div className="text-left">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold tracking-tight text-slate-900 font-display">{currentCluster.name}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${
                      currentCluster.is_local ? 'bg-cyan-50 text-cyan-800 border-cyan-200' : 'bg-indigo-50 text-indigo-800 border-indigo-200'
                    }`}>
                      {currentCluster.is_local ? 'Local Cluster' : 'Cloud Grid'}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 font-medium">{currentCluster.provider} · {currentCluster.region}</p>
                </div>
                <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ml-1 ${clusterDropdownOpen ? 'rotate-180' : ''}`} />
              </button>
            </div>

            {/* Dropdown Menu */}
            {clusterDropdownOpen && (
              <div className="absolute left-0 mt-2.5 w-84 rounded-2xl bg-white border border-slate-200 shadow-xl p-2 z-50">
                <div className="px-3 py-2 text-[11px] font-extrabold text-slate-400 uppercase tracking-wider border-b border-slate-100 font-display">
                  Select Target Kubernetes Cluster
                </div>
                <div className="space-y-1 mt-1.5">
                  {clusters.map((c) => {
                    const isSelected = c.id === selectedClusterId
                    return (
                      <button
                        key={c.id}
                        onClick={() => handleSelectCluster(c.id)}
                        className={`w-full text-left p-3 rounded-xl transition-all flex items-start gap-3 cursor-pointer ${
                          isSelected
                            ? 'bg-indigo-50/80 border border-indigo-200 text-slate-900 shadow-xs'
                            : 'hover:bg-slate-50 text-slate-700'
                        }`}
                      >
                        <div className="mt-0.5 w-7 h-7 rounded-xl bg-slate-100 flex items-center justify-center text-slate-600">
                          {c.is_local ? <Laptop className="w-4 h-4 text-cyan-600" /> : <Cloud className="w-4 h-4 text-indigo-600" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-slate-900 truncate font-display">{c.name}</span>
                            {c.is_local && (
                              <span className="text-[9px] bg-cyan-100 text-cyan-800 px-1.5 py-0.2 rounded font-bold">Local</span>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-500 truncate mt-0.5">{c.provider}</p>
                          <span className={`text-[10px] font-mono font-medium block mt-1 ${c.status.includes('Degraded') || c.status.includes('OOM') ? 'text-amber-600' : 'text-emerald-600'}`}>
                            ● {c.status}
                          </span>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons: Live Sync & Primary Investigate */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => fetchClusterData()}
              disabled={refreshing}
              className="px-4 py-2.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-semibold flex items-center gap-2 transition-all disabled:opacity-50 shadow-xs cursor-pointer"
              title="Refresh telemetry"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-indigo-600 ${refreshing ? 'animate-spin' : ''}`} />
              <span>{refreshing ? 'Syncing...' : 'Live Sync'}</span>
            </button>

            <Link
              to="/history"
              className="px-4 py-2.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-semibold flex items-center gap-2 transition-all shadow-xs"
              title="View persisted investigations in PostgreSQL"
            >
              <Clock className="w-3.5 h-3.5 text-purple-600" />
              <span>History</span>
            </Link>

            <button
              onClick={handleRunInvestigation}
              disabled={investigationState === 'running'}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-700 to-violet-700 hover:from-indigo-700 hover:to-violet-800 text-white text-xs font-bold flex items-center gap-2 shadow-md shadow-indigo-600/20 transition-all disabled:opacity-60 cursor-pointer"
            >
              <Sparkles className={`w-3.5 h-3.5 ${investigationState === 'running' ? 'animate-spin' : ''}`} />
              <span>{investigationState === 'running' ? 'Investigating...' : '⚡ Investigate Cluster'}</span>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 sm:px-8 mt-8 space-y-8">

        {/* =========================================================================
            Live 7-Stage Stepper Banner (Streaming SSE Pipeline)
        ========================================================================= */}
        {investigationState === 'running' && (
          <div className="bg-white border border-indigo-200 rounded-3xl p-6 sm:p-7 shadow-sm text-slate-800 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-3">
                <RefreshCw className="w-4 h-4 text-indigo-600 animate-spin" />
                <span className="text-sm font-bold text-slate-900 font-display">
                  Live Kubernetes Investigation Pipeline in Progress
                </span>
                <span className="text-xs text-indigo-600 font-mono bg-indigo-50 px-2 py-0.5 rounded-md font-semibold">
                  [{currentCluster.name}]
                </span>
              </div>
              <span className="text-xs font-mono font-bold text-indigo-700 bg-indigo-50 px-3 py-1 rounded-full border border-indigo-200">
                stage: {investigationStage}
              </span>
            </div>

            <p className="text-xs text-slate-600 font-medium">{investigationMessage}</p>

            {/* Stepper Pipeline */}
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5 text-center text-xs">
              {[
                { key: 'pods', label: '1. Pods' },
                { key: 'logs', label: '2. Logs' },
                { key: 'events', label: '3. Events' },
                { key: 'deployments', label: '4. Rollouts' },
                { key: 'network', label: '5. Network' },
                { key: 'ai_reasoning', label: '6. Gemini SRE' },
                { key: 'persisting', label: '7. Persist' },
              ].map(step => {
                const stages = ['started', 'pods', 'logs', 'events', 'deployments', 'network', 'ai_reasoning', 'persisting', 'completed']
                const currentIdx = stages.indexOf(investigationStage)
                const stepIdx = stages.indexOf(step.key)
                const isPassed = currentIdx >= stepIdx
                const isCurrent = currentIdx === stepIdx

                return (
                  <div
                    key={step.key}
                    className={`py-2.5 px-2 rounded-xl border transition-all ${
                      isCurrent
                        ? 'bg-indigo-600 text-white font-bold border-indigo-600 shadow-md shadow-indigo-600/20 animate-pulse'
                        : isPassed
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold'
                        : 'bg-slate-50 text-slate-400 border-slate-200'
                    }`}
                  >
                    {step.label}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* =========================================================================
            Unified Final Gemini AI Reasoning & Safe Suggestion Card (Same Page)
        ========================================================================= */}
        {liveDiagnosis && (
          <div className="bg-white border-2 border-indigo-500/30 rounded-3xl p-7 sm:p-9 shadow-lg shadow-indigo-500/5 space-y-7 relative overflow-hidden">
            {/* Header / Root Cause Banner */}
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-5 border-b border-slate-200/90 pb-6">
              <div className="space-y-2 flex-1">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping" />
                  <span className="text-xs uppercase font-extrabold tracking-wider text-indigo-700 bg-indigo-50 border border-indigo-200 px-3 py-1 rounded-full flex items-center gap-1.5 font-display">
                    <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                    Senior SRE Gemini AI Reasoning & Remediation
                  </span>
                  <span className="text-[11px] px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 font-mono font-medium">
                    cluster: {completedPayload?.cluster_context || selectedClusterId}
                  </span>
                  <span className="text-[11px] px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 font-mono font-medium">
                    ns/{completedPayload?.namespace || selectedNamespace}
                  </span>
                </div>
                <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight leading-snug font-display">
                  {liveDiagnosis.root_cause}
                </h2>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <span className="text-xs font-mono font-bold text-emerald-700 bg-emerald-50 border border-emerald-300 px-4 py-2 rounded-full flex items-center gap-1.5 shadow-xs">
                  <Shield className="w-4 h-4 text-emerald-600" />
                  {liveDiagnosis.confidence}% Confidence ({liveDiagnosis.confidence_level || 'High'})
                </span>
                <button
                  onClick={() => setLiveDiagnosis(null)}
                  className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                  title="Close diagnosis banner"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Detailed SRE Explanation */}
            <div>
              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2.5 flex items-center gap-1.5 font-display">
                <Activity className="w-3.5 h-3.5 text-indigo-600" />
                Causal Root Cause Analysis
              </h4>
              <p className="text-sm text-slate-700 leading-relaxed bg-slate-50/90 p-5 rounded-2xl border border-slate-200">
                {liveDiagnosis.explanation}
              </p>
            </div>

            {/* Supporting Correlated Telemetry Evidence */}
            {liveDiagnosis.supporting_evidence && liveDiagnosis.supporting_evidence.length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5 font-display">
                  <Database className="w-3.5 h-3.5 text-cyan-600" />
                  Correlated Telemetry Evidence
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                  {liveDiagnosis.supporting_evidence.map((evi, i) => (
                    <div key={i} className="p-4 rounded-2xl bg-slate-50 border border-slate-200/90 text-xs">
                      <div className="flex items-center justify-between text-[11px] mb-2">
                        <span className="font-mono text-indigo-700 font-bold">{evi.resource}</span>
                        <span className="text-[10px] uppercase font-bold text-slate-600 bg-slate-200/80 px-2 py-0.5 rounded">
                          {evi.source}
                        </span>
                      </div>
                      <p className="text-slate-700 font-mono text-[11px] leading-relaxed">{evi.detail}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Suggested Safe Remediation Plan */}
            {liveDiagnosis.suggested_fix && (
              <div>
                <h4 className="text-xs font-bold text-emerald-700 uppercase tracking-wider mb-2.5 flex items-center gap-1.5 font-display">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  Recommended Safe Remediation Plan
                </h4>
                <div className="p-5 rounded-2xl bg-emerald-50/70 border border-emerald-200/90 text-xs sm:text-sm text-emerald-950 leading-relaxed whitespace-pre-line font-sans">
                  {liveDiagnosis.suggested_fix}
                </div>
              </div>
            )}

            {/* Recommended Kubectl Commands with One-Click Copy */}
            {liveDiagnosis.kubectl_commands && liveDiagnosis.kubectl_commands.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-2.5">
                  <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5 font-display">
                    <Terminal className="w-3.5 h-3.5 text-indigo-600" />
                    Recommended Manual Kubectl Commands
                  </h4>
                  <span className="text-[11px] text-amber-700 font-medium bg-amber-50 border border-amber-200 px-2.5 py-0.5 rounded-md">
                    Zero auto-execution: Copy & inspect manually
                  </span>
                </div>
                <div className="space-y-3">
                  {liveDiagnosis.kubectl_commands.map((cmdObj, i) => (
                    <div key={i} className="bg-slate-900 rounded-2xl p-4 border border-slate-800 text-slate-100 shadow-xs">
                      <div className="flex items-center justify-between text-xs mb-2">
                        <span className="text-slate-300 font-medium">{cmdObj.purpose}</span>
                        <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                          cmdObj.risk === 'read-only'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        }`}>
                          {cmdObj.risk}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-3 font-mono text-xs text-cyan-300 bg-slate-950 px-3.5 py-2.5 rounded-xl border border-slate-800">
                        <code className="truncate selection:bg-indigo-600">{cmdObj.command}</code>
                        <button
                          onClick={() => handleCopyCmd(cmdObj.command, `live-cmd-${i}`)}
                          className="flex items-center gap-1.5 text-slate-400 hover:text-white px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors shrink-0 cursor-pointer"
                          title="Copy command"
                        >
                          {copiedCmd === `live-cmd-${i}` ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                              <span className="text-[11px] text-emerald-400 font-semibold">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" />
                              <span className="text-[11px]">Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Proposed YAML Diff */}
            {liveDiagnosis.yaml_proposal && (
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2.5 flex items-center gap-1.5 font-display">
                  <FileCode className="w-3.5 h-3.5 text-purple-600" />
                  Proposed Manifest Patch (YAML Diff)
                </h4>
                <pre className="text-xs font-mono text-purple-200 bg-slate-950 p-5 rounded-2xl border border-slate-800 overflow-x-auto shadow-xs">
                  {liveDiagnosis.yaml_proposal}
                </pre>
              </div>
            )}

            {/* Persisted to PostgreSQL Footer */}
            {completedPayload?.fingerprint && (
              <div className="pt-4 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between text-xs text-slate-500 gap-3">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span className="font-medium text-slate-700">Report Persisted to PostgreSQL</span>
                  <span className="font-mono text-slate-500">· Fingerprint: <code className="text-indigo-700 font-bold bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">{completedPayload.fingerprint}</code></span>
                </div>
                <Link
                  to="/history"
                  className="text-indigo-600 hover:text-indigo-800 font-bold flex items-center gap-1 transition-colors"
                >
                  View in History Page →
                </Link>
              </div>
            )}
          </div>
        )}

        {/* =========================================================================
            Cluster Health Ratio & Telemetry Metrics Cards Grid
        ========================================================================= */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
          {/* Health Ratio */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs hover:border-slate-300 transition-all">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider font-display">Health Ratio</span>
              <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <Boxes className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-4 flex items-baseline gap-2">
              <span className="text-3xl font-black text-slate-900 font-display">
                {clusterStatus?.healthy_pods ?? 0}
                <span className="text-slate-400 text-lg font-normal"> / {clusterStatus?.total_pods ?? 0}</span>
              </span>
              <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                {clusterStatus?.total_pods ? Math.round((clusterStatus.healthy_pods / clusterStatus.total_pods) * 100) : 100}% OK
              </span>
            </div>
            <div className="w-full bg-slate-100 h-2 rounded-full mt-4 overflow-hidden">
              <div 
                className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${clusterStatus?.total_pods ? (clusterStatus.healthy_pods / clusterStatus.total_pods) * 100 : 100}%` }}
              />
            </div>
          </div>

          {/* Operational Events */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs hover:border-slate-300 transition-all">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider font-display">Warning Events</span>
              <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                <AlertTriangle className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-4 flex items-baseline gap-2">
              <span className="text-3xl font-black text-amber-600 font-display">
                {clusterStatus?.warning_events ?? 0}
              </span>
              <span className="text-xs font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                Active
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-3 font-medium truncate">
              {currentCluster.name}
            </p>
          </div>

          {/* Cluster Fleet & Nodes */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs hover:border-slate-300 transition-all">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider font-display">Cluster Fleet</span>
              <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <Server className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-4 flex items-baseline gap-2">
              <span className="text-2xl font-black text-slate-900 font-display">
                {clusterStatus?.nodes_ready ?? 1} / {clusterStatus?.nodes_total ?? 1}
              </span>
              <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200">
                Ready
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-3 font-medium truncate font-mono">
              k8s {clusterStatus?.k8s_version || 'v1.30'}
            </p>
          </div>

          {/* Resource Utilization */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs hover:border-slate-300 transition-all">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider font-display">Resource Load</span>
              <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                <Cpu className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-4 flex items-baseline justify-between text-xs font-semibold text-slate-700 font-mono">
              <span>CPU: <strong className="text-blue-600">{clusterStatus?.cpu_usage_pct ?? 38}%</strong></span>
              <span>MEM: <strong className="text-purple-600">{clusterStatus?.memory_usage_pct ?? 52}%</strong></span>
            </div>
            <div className="w-full bg-slate-100 h-2 rounded-full mt-4 overflow-hidden flex">
              <div className="bg-blue-500 h-full" style={{ width: `${clusterStatus?.cpu_usage_pct ?? 38}%` }} />
              <div className="bg-purple-500 h-full" style={{ width: `${(clusterStatus?.memory_usage_pct ?? 52) / 2}%` }} />
            </div>
          </div>
        </div>

        {/* =========================================================================
            Namespace Filter Bar & Workload Search
        ========================================================================= */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
          {/* Namespace Scope Pills */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
            <span className="text-xs font-bold text-slate-400 px-1 flex items-center gap-1.5 uppercase font-display">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <span>Scope:</span>
            </span>
            {namespaces.map(ns => (
              <button
                key={ns.name}
                onClick={() => setSelectedNamespace(ns.name)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all whitespace-nowrap flex items-center gap-1.5 cursor-pointer ${
                  selectedNamespace === ns.name
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700'
                }`}
              >
                <span>{ns.name}</span>
                {ns.warning_count > 0 && (
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                )}
              </button>
            ))}
          </div>

          {/* Search Bar */}
          <div className="relative min-w-[260px]">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3.5 top-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search components or pods..."
              className="w-full pl-9 pr-4 py-2 bg-slate-50 focus:bg-white border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition-all"
            />
          </div>
        </div>

        {/* =========================================================================
            Workloads Telemetry Table
        ========================================================================= */}
        <div className="bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div className="flex items-center gap-2.5">
              <Layers className="w-4 h-4 text-indigo-600" />
              <h3 className="text-sm font-bold text-slate-900 font-display">
                Cluster Workloads Matrix ({filteredWorkloads.length})
              </h3>
              <span className="text-xs text-slate-500 font-mono font-medium">[{currentCluster.name}]</span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-4 px-6">Component / Resource</th>
                  <th className="py-4 px-6">Namespace</th>
                  <th className="py-4 px-6">Status</th>
                  <th className="py-4 px-6">Replicas</th>
                  <th className="py-4 px-6">Restarts</th>
                  <th className="py-4 px-6">Resource Usage</th>
                  <th className="py-4 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
                {filteredWorkloads.map(w => (
                  <tr key={w.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-2.5">
                        <span className="px-2 py-0.5 rounded-md bg-slate-100 text-[10px] text-slate-700 font-bold border border-slate-200">
                          {w.kind}
                        </span>
                        <span className="font-bold text-slate-900 text-sm font-display">{w.name}</span>
                      </div>
                      {w.message && (
                        <p className="text-xs text-rose-600 mt-1 font-mono line-clamp-1 font-medium">
                          {w.message}
                        </p>
                      )}
                    </td>
                    <td className="py-4 px-6">
                      <span className="text-slate-500 font-mono font-medium">{w.namespace}</span>
                    </td>
                    <td className="py-4 px-6">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getStatusBadge(w.status)}`}>
                        {w.status}
                      </span>
                    </td>
                    <td className="py-4 px-6 font-semibold text-slate-800">{w.ready_replicas}</td>
                    <td className="py-4 px-6">
                      <span className={w.restarts > 5 ? 'text-rose-600 font-bold font-mono' : 'text-slate-500 font-mono'}>
                        {w.restarts}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-slate-500 text-xs">
                      <div>Memory: <span className="text-slate-800 font-medium">{w.memory_usage}</span></div>
                      <div>Compute: <span className="text-slate-800 font-medium">{w.cpu_usage}</span></div>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {w.status !== 'Running' && (
                          <button
                            onClick={() => handleQuickTroubleshoot(w)}
                            className="px-3.5 py-1.5 rounded-xl bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 hover:text-indigo-900 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-xs cursor-pointer"
                            title="Diagnose this workload"
                          >
                            <Wrench className="w-3.5 h-3.5 text-indigo-600" />
                            <span>Diagnose</span>
                          </button>
                        )}
                        <button
                          onClick={() => setShowLogsModal(w)}
                          className="p-1.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-500 hover:text-slate-800 shadow-xs cursor-pointer"
                          title="Inspect Telemetry Logs"
                        >
                          <Terminal className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredWorkloads.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-400 font-medium">
                      No components matching criteria in scope "{selectedNamespace}" for {currentCluster.name}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* =========================================================================
            Live Kubernetes Event Stream
        ========================================================================= */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <HeartPulse className="w-4 h-4 text-cyan-600" />
              <h3 className="text-sm font-bold text-slate-900 font-display">Cluster Event Stream</h3>
              <span className="text-xs text-slate-500 font-mono">[{currentCluster.name}]</span>
            </div>
            <span className="text-xs font-mono text-slate-500">{events.length} Events Logged</span>
          </div>

          <div className="space-y-2.5">
            {events.slice(0, 8).map((evt, i) => (
              <div key={i} className="flex items-center justify-between p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 text-xs">
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    evt.type === 'Warning' ? 'bg-amber-100 text-amber-800 border border-amber-200' : 'bg-slate-200 text-slate-700'
                  }`}>
                    {evt.reason}
                  </span>
                  <span className="font-mono text-indigo-700 font-semibold">{evt.object}</span>
                  <span className="text-slate-700 line-clamp-1">{evt.message}</span>
                </div>
                <span className="text-[11px] text-slate-400 font-mono shrink-0 ml-3">
                  {evt.timestamp || 'Just now'}
                </span>
              </div>
            ))}
            {events.length === 0 && (
              <div className="text-center py-6 text-slate-400 text-xs font-medium">
                No active warning events in current cluster scope.
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Log Inspection Modal */}
      {showLogsModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white border border-slate-200 rounded-3xl max-w-2xl w-full p-6 text-slate-800 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-indigo-600" />
                <h3 className="text-sm font-bold text-slate-900 font-display">
                  Telemetry Stream: {showLogsModal.name}
                </h3>
              </div>
              <button
                onClick={() => setShowLogsModal(null)}
                className="text-slate-400 hover:text-slate-700 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="bg-slate-950 p-4 rounded-2xl font-mono text-xs text-slate-200 space-y-1.5 max-h-80 overflow-y-auto border border-slate-800">
              <p className="text-slate-400"># Inspecting workload {showLogsModal.name} in namespace {showLogsModal.namespace}</p>
              <p className="text-slate-400"># Cluster context: {currentCluster.name} ({currentCluster.provider})</p>
              <p className="text-cyan-300">[info] Workload kind: {showLogsModal.kind} · Status: {showLogsModal.status}</p>
              <p className="text-amber-300">[event] Restarts observed: {showLogsModal.restarts} · Last Event: {showLogsModal.last_event}</p>
              {showLogsModal.message && (
                <p className="text-rose-400 font-bold">[error] {showLogsModal.message}</p>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowLogsModal(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700 cursor-pointer"
              >
                Close
              </button>
              <button
                onClick={() => {
                  const target = showLogsModal
                  setShowLogsModal(null)
                  handleQuickTroubleshoot(target)
                }}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-xs font-semibold text-white flex items-center gap-1.5 cursor-pointer shadow-xs"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Run Full AI SRE Investigation</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard
