import request from './http'

export interface Character {
  id: string
  novel_id: string
  name: string
  role: string
  description: string
  personality: string
  appearance: string
  background: string
  gender?: string
  age?: string
  created_at: string
  updated_at: string
}

export interface WorldSetting {
  id: string
  novel_id: string
  name: string
  setting_type: string
  description: string
  parent_id: string | null
  created_at: string
  updated_at: string
}

// ===== Character API =====

export function getCharacterList(novelId: string) {
  return request.get<Character[]>(`/novels/${novelId}/characters`)
}

export function createCharacter(
  novelId: string,
  data: {
    name: string
    role?: string
    description?: string
    personality?: string
    appearance?: string
    background?: string
    gender?: string
    age?: string
  }
) {
  return request.post<Character>(`/novels/${novelId}/characters`, data)
}

export function updateCharacter(
  characterId: string,
  data: Partial<
    Pick<Character, 'name' | 'role' | 'description' | 'personality' | 'appearance' | 'background' | 'gender' | 'age'>
  >
) {
  return request.put<Character>(`/characters/${characterId}`, data)
}

export function deleteCharacter(characterId: string) {
  return request.delete(`/characters/${characterId}`)
}

// ===== World Setting API =====

export function getSettingList(novelId: string, settingType?: string) {
  const params = settingType ? { setting_type: settingType } : {}
  return request.get<WorldSetting[]>(`/novels/${novelId}/settings`, { params })
}

export function createSetting(
  novelId: string,
  data: {
    name: string
    setting_type?: string
    description?: string
    parent_id?: string | null
  }
) {
  return request.post<WorldSetting>(`/novels/${novelId}/settings`, data)
}

export function updateSetting(
  settingId: string,
  data: Partial<Pick<WorldSetting, 'name' | 'setting_type' | 'description' | 'parent_id'>>
) {
  return request.put<WorldSetting>(`/settings/${settingId}`, data)
}

export function deleteSetting(settingId: string) {
  return request.delete(`/settings/${settingId}`)
}
