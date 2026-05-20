import { useQuery } from "@tanstack/react-query";

import {
  fallbackDashboardKpis,
  getDashboardKpis,
  type DashboardKpis
} from "../services/dashboardService";

export type DashboardKpisState = {
  kpis: DashboardKpis;
  isLoading: boolean;
  isUsingFallback: boolean;
  isError: boolean;
};

export function useDashboardKpis(): DashboardKpisState {
  const query = useQuery({
    queryKey: ["dashboard", "kpis"],
    queryFn: getDashboardKpis,
    retry: false,
    refetchOnWindowFocus: false,
    staleTime: 30000
  });

  return {
    kpis: query.data ?? fallbackDashboardKpis,
    isLoading: query.isLoading,
    isUsingFallback: !query.data,
    isError: query.isError
  };
}