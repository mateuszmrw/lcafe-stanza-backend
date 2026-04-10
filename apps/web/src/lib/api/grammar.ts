import { apiClient } from "./client"

export interface GrammarTokenInput {
  w: string
  l: string
  pos: string
  feats: string
  dep_head?: number
  dep_rel?: string
}

export interface TokenAnnotation {
  w: string
  annotation: string
}

export interface GrammarExplainResponse {
  token_annotations: TokenAnnotation[]
  prose_explanation: string
}

export async function explainGrammar(
  tokens: GrammarTokenInput[],
  languageCode: string
): Promise<GrammarExplainResponse> {
  return apiClient<GrammarExplainResponse>("/grammar/explain", {
    method: "POST",
    body: JSON.stringify({ tokens, language_code: languageCode }),
  })
}
