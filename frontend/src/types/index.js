/**
 * @fileoverview Type definitions and schemas placeholder for KubeVora.
 */

/**
 * @typedef {Object} HealthStatusResponse
 * @property {'healthy' | 'degraded' | 'down'} status - Service health condition
 * @property {string} service - Identifying service name ('kubevora')
 */

/**
 * @typedef {Object} ClusterNodeEvidence
 * @property {string} name - Node hostname
 * @property {string} status - Node condition (Ready / NotReady)
 * @property {string} cpuUsage - CPU consumption metrics
 * @property {string} memoryUsage - RAM consumption metrics
 */

/**
 * @typedef {Object} RootCauseDiagnosis
 * @property {string} rootCause - Diagnosed failure cause
 * @property {number} confidenceScore - AI confidence rating (0.0 to 1.0)
 * @property {string[]} suggestedFixes - Recommended remediation actions
 */

export const TYPE_PLACEHOLDERS = {}
