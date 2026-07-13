import request from './http'

export type GraphNodeType =
  | 'protagonist'
  | 'ally'
  | 'enemy'
  | 'neutral'
  | 'location'
  | 'faction'
  | 'rule'
  | 'plot'
  | 'event'

export interface GraphNode {
  id: string
  name: string
  role: string
  type: GraphNodeType
  identity: string
  description?: string
  connections: number
  chapters: number
  x: number
  y: number
}

export interface GraphEdge {
  from: string
  to: string
  label: string
  type: 'intimate' | 'opposite' | 'causal' | 'weak'
}

export interface WorldviewGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export function getWorldview(type: string, novelId: string) {
  return request.get<WorldviewGraph>(`/worldview/${encodeURIComponent(type)}`, {
    params: { novel_id: novelId },
  })
}
