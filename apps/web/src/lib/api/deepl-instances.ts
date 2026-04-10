import { apiClient } from "./client"

export interface DeepLInstanceResponse {
  id: string
  source_lang: string
  target_lang: string
  enabled: boolean
  created_at: string
}

export interface CreateDeepLInstanceRequest {
  source_lang: string
  target_lang: string
}

export async function getDeepLInstances(): Promise<DeepLInstanceResponse[]> {
  return apiClient<DeepLInstanceResponse[]>("/admin/deepl-instances")
}

export async function createDeepLInstance(
  data: CreateDeepLInstanceRequest
): Promise<DeepLInstanceResponse> {
  return apiClient<DeepLInstanceResponse>("/admin/deepl-instances", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function toggleDeepLInstance(
  id: string,
  enabled: boolean
): Promise<DeepLInstanceResponse> {
  return apiClient<DeepLInstanceResponse>(`/admin/deepl-instances/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ enabled }),
  })
}

export async function deleteDeepLInstance(id: string): Promise<void> {
  return apiClient<void>(`/admin/deepl-instances/${id}`, { method: "DELETE" })
}
