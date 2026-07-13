import request from './http'

export interface Storyline {
  id: string
  novel_id: string
  name: string
  description: string
  color: string
  node_count: number
  is_active: boolean
  order: number
  created_at: string
  updated_at: string
}

export interface StorylineNode {
  id: string
  novel_id: string
  storyline_id: string
  title: string
  description: string
  node_type: string
  status: string
  chapter_index?: number
  chapter_id?: string
  x: number
  y: number
  width: number
  height: number
  parent_ids: string[]
  child_ids: string[]
  tags: string[]
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export function listStorylines(novelId: string) {
  return request.get<Storyline[]>(`/novels/${novelId}/storylines`)
}

export function createStoryline(
  novelId: string,
  data: { name: string; description?: string; color?: string }
) {
  return request.post<Storyline>(`/novels/${novelId}/storylines`, data)
}

export function updateStoryline(storylineId: string, data: Partial<Storyline>) {
  return request.put<Storyline>(`/storylines/${storylineId}`, data)
}

export function deleteStoryline(storylineId: string) {
  return request.delete<{ deleted: boolean }>(`/storylines/${storylineId}`)
}

export function listNodes(storylineId: string) {
  return request.get<StorylineNode[]>(`/storylines/${storylineId}/nodes`)
}

export function listNodesByNovel(novelId: string) {
  return request.get<StorylineNode[]>(`/novels/${novelId}/storyline-nodes`)
}

export interface CreateNodeData {
  title: string
  description?: string
  node_type?: string
  status?: string
  chapter_index?: number
  chapter_id?: string
  x?: number
  y?: number
  width?: number
  height?: number
  parent_ids?: string[]
  tags?: string[]
}

export function createNode(storylineId: string, data: CreateNodeData) {
  return request.post<StorylineNode>(`/storylines/${storylineId}/nodes`, data)
}

export function updateNode(nodeId: string, data: Partial<StorylineNode>) {
  return request.put<StorylineNode>(`/storyline-nodes/${nodeId}`, data)
}

export function deleteNode(nodeId: string) {
  return request.delete<{ deleted: boolean }>(`/storyline-nodes/${nodeId}`)
}

export function connectNodes(sourceId: string, targetId: string) {
  return request.post<{ connected: boolean }>('/storyline-nodes/connect', {
    source_id: sourceId,
    target_id: targetId,
  })
}

export function disconnectNodes(sourceId: string, targetId: string) {
  return request.post<{ disconnected: boolean }>('/storyline-nodes/disconnect', {
    source_id: sourceId,
    target_id: targetId,
  })
}
