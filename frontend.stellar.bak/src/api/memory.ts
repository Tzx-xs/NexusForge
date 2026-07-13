import request from './http'

export interface MemoryFact {
  id: string
  novel_id: string
  fact_type: string
  subject: string
  predicate: string
  object_value: string
  confidence: number
  is_immutable: boolean
  source_chapter_id: string | null
  evidence_text: string | null
  created_at: string
  updated_at: string
}

export interface MemoryBeat {
  id: string
  novel_id: string
  chapter_id: string
  chapter_index: number
  beat_type: string
  content: string
  narrative_weight: number
  is_turning_point: boolean
  created_at: string
  updated_at: string
}

export interface MemoryClue {
  id: string
  novel_id: string
  clue_text: string
  status: string
  planted_chapter_id: string | null
  resolved_chapter_id: string | null
  importance: number
  related_characters: string[]
  created_at: string
  updated_at: string
}

export interface IronLockData {
  fact_locks: MemoryFact[]
  beat_locks: MemoryBeat[]
  clue_locks: MemoryClue[]
  character_whitelist: string[]
  death_list: string[]
  relationship_map: Record<string, string[]>
}

export function getIronLock(novelId: string, upToChapter?: number) {
  const params = upToChapter ? { up_to_chapter: upToChapter } : {}
  return request.get<IronLockData>(`/novels/${novelId}/memory/iron-lock`, { params })
}

export function getMemoryFacts(novelId: string, factType?: string, immutableOnly?: boolean) {
  const params: Record<string, string | number | boolean | undefined> = {}
  if (factType) params.fact_type = factType
  if (immutableOnly !== undefined) params.immutable_only = immutableOnly
  return request.get<MemoryFact[]>(`/novels/${novelId}/memory/facts`, { params })
}

export function getMemoryBeats(novelId: string, upToChapter?: number) {
  const params: Record<string, string | number | boolean | undefined> = {}
  if (upToChapter !== undefined) params.up_to_chapter = upToChapter
  return request.get<MemoryBeat[]>(`/novels/${novelId}/memory/beats`, { params })
}

export function getMemoryClues(novelId: string, status?: string) {
  const params: Record<string, string | number | boolean | undefined> = {}
  if (status) params.status = status
  return request.get<MemoryClue[]>(`/novels/${novelId}/memory/clues`, { params })
}
