import request from './http'

export interface SearchCharacter {
  id: string
  novel_id?: string
  name: string
  role?: string
  description?: string
}

export interface SearchForeshadow {
  id: string
  novel_id?: string
  title: string
  description?: string
  priority?: string
  status?: string
  planted_chapter_index?: number
}

export interface SearchFact {
  id: string
  novel_id?: string
  fact_type?: string
  key: string
  value?: string
  locked_at_chapter?: number
}

export interface SearchSetting {
  id: string
  novel_id?: string
  name: string
  setting_type?: string
  description?: string
}

export interface SearchChapter {
  id: string
  novel_id?: string
  number: number
  title: string
  outline?: string
  status?: string
  word_count?: number
}

export interface SearchResults {
  characters: SearchCharacter[]
  foreshadows: SearchForeshadow[]
  facts: SearchFact[]
  settings: SearchSetting[]
  chapters: SearchChapter[]
}

export function searchAll(q: string, novelId: string): Promise<SearchResults> {
  return request.get<SearchResults>('/search', {
    params: { q, novel_id: novelId },
  })
}
