import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../services/api'

/**
 * Hook to retrieve backend system health status
 */
export function useHealth() {
  return useQuery({
    queryKey: ['systemHealth'],
    queryFn: getHealth,
    retry: 1,
    refetchInterval: 15000,
  })
}

/**
 * Placeholder hook for future investigation runs
 */
export function useClusterInvestigation() {
  return {
    investigate: () => console.log('[Placeholder] useClusterInvestigation triggered'),
    isLoading: false,
    data: null,
  }
}
