import request from './http'

export interface Snapshot {
  id: string
  novel_id: string
  chapter_id: string
  snapshot_type: string
  name: string
  description?: string
  content_hash?: string
  diff_data?: Record<string, unknown>
  parent_snapshot_id?: string
  created_by: string
  created_at: string
  updated_at: string
}

export function listSnapshots(novelId: string, params?: { limit?: number; chapter_id?: string }): Promise<Snapshot[]> {
  return request.get<Snapshot[]>(`/novels/${novelId}/snapshots`, { params })
}

export function listChapterSnapshots(chapterId: string) {
  return request.get<Snapshot[]>(`/chapters/${chapterId}/snapshots`)
}

export function createSnapshot(data: {
  novel_id: string
  chapter_id?: string
  snapshot_type?: string
  name: string
  description?: string
  content_hash?: string
  diff_data?: Record<string, unknown>
}) {
  return request.post<Snapshot>('/snapshots', data)
}

export function getSnapshot(snapshotId: string) {
  return request.get<Snapshot>(`/snapshots/${snapshotId}`)
}

export function deleteSnapshot(snapshotId: string) {
  return request.delete<{ deleted: boolean }>(`/snapshots/${snapshotId}`)
}

export function getSnapshotContent(snapshotId: string): Promise<string> {
  return request.get<string>(`/snapshots/${snapshotId}/content`)
}

export function restoreFromSnapshot(chapterId: string, snapshotId: string): Promise<unknown> {
  return request.post<unknown>(`/chapters/${chapterId}/restore/${snapshotId}`)
}
