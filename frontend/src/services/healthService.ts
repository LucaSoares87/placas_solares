import { api } from "./api";

export type HealthResponse = {
  status?: string;
  service?: string;
  version?: string;
  environment?: string;
  timestamp?: string;
};

export async function getHealth(): Promise<HealthResponse> {
  const response = await api.get<HealthResponse>("/health");
  return response.data;
}