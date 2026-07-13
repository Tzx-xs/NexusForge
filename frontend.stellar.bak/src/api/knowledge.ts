import request from './http'

export interface KnowledgeTriple {
  id: string
  novel_id: string
  subject: string
  predicate: string
  object: string
  confidence: number
  source_chapter_id: string | null
  created_at: string
  updated_at: string
}

export interface ChapterSummary {
  id: string
  novel_id: string
  chapter_id: string
  chapter_index: number
  summary_text: string
  key_events: string[]
  word_count: number
  created_at: string
  updated_at: string
}

export function getKnowledgeTriples(novelId: string, subject?: string, predicate?: string) {
  const params: Record<string, string | undefined> = {}
  if (subject) params.subject = subject
  if (predicate) params.predicate = predicate
  return request.get<KnowledgeTriple[]>(`/novels/${novelId}/knowledge/triples`, { params })
}

export function getChapterSummaries(novelId: string, limit = 10) {
  return request.get<ChapterSummary[]>(`/novels/${novelId}/knowledge/summaries`, {
    params: { limit },
  })
}

export interface KnowledgeSearchResult {
  content: string
  score: number
  metadata?: Record<string, unknown>
}

export function searchKnowledge(novelId: string, query: string, topK = 5) {
  return request.post<KnowledgeSearchResult[]>(`/novels/${novelId}/knowledge/search`, {
    query,
    top_k: topK,
  })
}
