/**
 * KubeVora Fetch-based Server-Sent Events (SSE) Client
 * Handles authenticated POST streaming with Authorization: Bearer <token>
 */
import { API_BASE_URL } from './api.js'

export async function streamInvestigation({
  clusterId = 'local-kind',
  namespace = 'default',
  includeLogs = true,
  onProgress = () => {},
  onComplete = () => {},
  onError = () => {},
}) {
  const token = localStorage.getItem('kubevora_token')
  const headers = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  try {
    const response = await fetch(`${API_BASE_URL}/investigate/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        cluster_id: clusterId,
        namespace: namespace === 'all-namespaces' ? null : namespace,
        include_logs: includeLogs,
      }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let finalPayload = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() // keep incomplete last line in buffer

      for (const line of lines) {
        const trimmed = line.trim()
        if (trimmed.startsWith('data:')) {
          const jsonStr = trimmed.replace(/^data:\s*/, '')
          try {
            const eventData = JSON.parse(jsonStr)
            onProgress(eventData)

            if (eventData.stage === 'completed') {
              finalPayload = eventData
            } else if (eventData.stage === 'failed') {
              throw new Error(eventData.error || 'Investigation failed')
            }
          } catch (pe) {
            console.warn('[SSE] JSON parse warning:', pe, jsonStr)
          }
        }
      }
    }

    if (finalPayload) {
      onComplete(finalPayload)
    }
    return finalPayload
  } catch (err) {
    console.error('[SSE] Stream error:', err)
    onError(err)
    throw err
  }
}
