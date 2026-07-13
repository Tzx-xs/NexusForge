import request from './http'

export interface VoiceFingerprint {
  fingerprint_id: string
  novel_id: string
  name: string
  lexical_richness: number
  sentence_length_mean: number
  sentence_length_std: number
  paragraph_length_mean: number
  paragraph_length_std: number
  unique_char_ratio: number
  function_word_ratio: number
  content_word_ratio: number
  dialogue_ratio: number
  narration_ratio: number
  description_ratio: number
  punctuation_density: Record<string, number>
  common_ngrams: string[]
  signature_phrases: string[]
  sentence_structure_diversity: number
  paragraph_starts: string[]
  avg_word_per_sentence: number
  clause_density: number
  source_sample_count: number
  source_char_count: number
  version: number
  created_at: string
  updated_at: string
}

export interface VoiceDriftResult {
  drifted: boolean
  overall_similarity: number
  dimension_scores: Record<string, number>
  drift_dimensions: string[]
  details: Record<string, unknown>
}

export interface VoiceFingerprintInfo {
  id: string
  name: string
  novel_id: string
  sample_count: number
  char_count: number
}

export function extractFingerprint(
  texts: string[],
  name: string = 'default',
  novelId: string = ''
) {
  return request.post<VoiceFingerprint>('/voice/extract', { texts, name, novel_id: novelId })
}

export function listFingerprints() {
  return request.get<VoiceFingerprintInfo[]>('/voice/fingerprints')
}

export function getFingerprint(fpId: string) {
  return request.get<VoiceFingerprint>(`/voice/fingerprints/${fpId}`)
}

export function detectDrift(baselineId: string, sampleText: string) {
  return request.post<VoiceDriftResult>('/voice/detect-drift', {
    baseline_id: baselineId,
    sample_text: sampleText,
  })
}

export function generateRewritePrompt(
  baselineId: string,
  targetText: string,
  driftDimensions: string[] = []
) {
  return request.post<{ prompt: string }>('/voice/rewrite-prompt', {
    baseline_id: baselineId,
    target_text: targetText,
    drift_dimensions: driftDimensions,
  })
}

export function getStyleGuide(fpId: string) {
  return request.get<{ style_guide: string }>(`/voice/fingerprints/${fpId}/style-guide`)
}

export function mergeFingerprints(texts: string[], name: string, novelId: string = '') {
  return request.post<VoiceFingerprint>('/voice/fingerprints/merge', {
    texts,
    name,
    novel_id: novelId,
  })
}
