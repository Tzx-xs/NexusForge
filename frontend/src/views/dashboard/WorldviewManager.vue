<template>
  <div class="module-panel worldview-panel">
    <!-- 标签栏 -->
    <div class="wv-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="wv-tab"
        :class="{ active: activeTab === tab.key }"
        @click="switchTab(tab.key)"
      >
        <component :is="tab.icon" class="tab-icon"/>
        {{ tab.label }}
      </button>
    </div>

    <!-- 画布区域 -->
    <div class="wv-canvas-area">
      <svg
        ref="svgRef"
        class="wv-svg"
        width="100%"
        height="100%"
        @mousedown="startPan"
        @mousemove="doPan"
        @mouseup="endPan"
        @mouseleave="endPan"
        @wheel="doZoom"
        @click="hidePopover"
      >
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.5" result="blur"/>
            <feMerge>
              <feMergeNode in="blur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          <filter id="glow-strong" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="blur"/>
            <feMerge>
              <feMergeNode in="blur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          <linearGradient id="edge-pink" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="rgba(229,184,110,0.5)"/>
            <stop offset="100%" stop-color="rgba(229,184,110,0.2)"/>
          </linearGradient>
          <linearGradient id="edge-purple" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="rgba(167,139,250,0.5)"/>
            <stop offset="100%" stop-color="rgba(167,139,250,0.2)"/>
          </linearGradient>
          <marker id="arrow-purple" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="rgba(167,139,250,0.5)"/>
          </marker>
        </defs>
        <g ref="graphRef">
          <!-- 节点和连线由 JS 渲染 -->
        </g>
      </svg>

      <!-- 节点信息浮层 -->
      <div
        v-if="popover.show"
        class="node-popover xy-card-shimmer"
        :style="{ left: popover.x + 'px', top: popover.y + 'px' }"
      >
        <div class="popover-header">
          <span class="popover-dot" :style="{ background: popover.color }"/>
          <span class="popover-name">{{ popover.name }}</span>
          <span class="popover-role">{{ popover.role }}</span>
        </div>
        <div class="popover-body">
          <p>关系数：{{ popover.connections }}</p>
          <p v-if="popover.chapters > 0">出场章数：{{ popover.chapters }}</p>
        </div>
        <div class="popover-actions">
          <button @click="popoverAction('view')">查看详情</button>
          <button @click="popoverAction('edit')">编辑</button>
        </div>
      </div>

      <!-- 空状态 / 加载 -->
      <div v-if="loading || nodes.length === 0" class="wv-empty">
        <Loader v-if="loading" class="wv-empty-icon wv-spin"/>
        <Globe v-else class="wv-empty-icon"/>
        <p class="wv-empty-text">{{ loading ? '正在构建关系网络…' : '暂无数据，展示示例网络' }}</p>
      </div>

      <!-- 缩放控制 -->
      <div class="zoom-controls xy-card-shimmer">
        <button title="放大" @click="zoomIn">
          <Plus class="icon-14 zoom-icon"/>
        </button>
        <button title="缩小" @click="zoomOut">
          <Minus class="icon-14 zoom-icon"/>
        </button>
        <button title="重置视图" @click="resetView">
          <Rotate class="icon-14"/>
        </button>
      </div>

      <!-- 图例 -->
      <div class="wv-legend">
        <p class="legend-title">{{ legendTitle }}</p>
        <div class="legend-items">
          <div v-for="item in legendItems" :key="item.label" class="legend-item">
            <span class="legend-dot" :style="{ background: item.color }"/>
            {{ item.label }}
          </div>
        </div>
        <div class="legend-divider"/>
        <div class="legend-lines">
          <div class="legend-line-item">
            <svg width="20" height="6">
              <line x1="0" y1="3" x2="20" y2="3" stroke="rgba(229,184,110,0.6)" stroke-width="2"/>
            </svg>
            <span>亲密关系</span>
          </div>
          <div class="legend-line-item">
            <svg width="20" height="6">
              <line x1="0" y1="3" x2="20" y2="3" stroke="rgba(251,191,36,0.6)" stroke-width="1.5" stroke-dasharray="4 2"/>
            </svg>
            <span>立场对立</span>
          </div>
          <div class="legend-line-item">
            <svg width="20" height="6">
              <line x1="0" y1="3" x2="20" y2="3" stroke="rgba(167,139,250,0.6)" stroke-width="2"/>
            </svg>
            <span>因果关联</span>
          </div>
        </div>
        <p class="legend-hint">拖拽节点移动 · 滚轮缩放 · 点击查看详情</p>
      </div>
    </div>

    <XyDialog
      v-model="detailVisible"
      title="节点详情"
      confirm-text="知道了"
    >
      <div v-if="detailNode" class="detail-body">
        <div class="detail-header">
          <span class="detail-dot" :style="{ background: typeColors[detailNode.type] || 'var(--xy-brand-500)' }"/>
          <span class="detail-name">{{ detailNode.name }}</span>
          <span class="detail-role">{{ detailNode.role }}</span>
        </div>
        <p class="detail-identity">{{ detailNode.identity || detailNode.description || '暂无描述' }}</p>
        <div class="detail-meta">
          <span>关系数：{{ detailNode.connections }}</span>
          <span v-if="detailNode.chapters > 0">出场章节：{{ detailNode.chapters }}</span>
        </div>
      </div>
    </XyDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  CircleDot,
  Globe,
  Notebook,
  ChartBar,
  Plus,
  Minus,
  Rotate,
  Loader,
} from '@vicons/tabler'
import { useBibleStore } from '@/stores/bible'
import { useNovelStore } from '@/stores/novel'
import { useCurrentNovelId } from '@/composables/useCurrentNovelId'
import { listNodesByNovel } from '@/api/storylines'
import { getWorldview } from '@/api/worldview'
import { XyDialog } from '@/components/common'
import type { Character, WorldSetting } from '@/api/bible'
import type { StorylineNode } from '@/api/storylines'
import type { GraphNode, GraphEdge, GraphNodeType } from '@/api/worldview'

const router = useRouter()
const message = useMessage()
const bibleStore = useBibleStore()
const novelStore = useNovelStore()
const { novelId } = useCurrentNovelId()

const tabs = [
  { key: 'characters', label: '人物关系图', icon: CircleDot },
  { key: 'geography', label: '地理关系图', icon: Globe },
  { key: 'rules', label: '规则体系图', icon: Notebook },
  { key: 'plot', label: '主线规划图', icon: ChartBar },
]

const activeTab = ref('characters')

const legendTitles: Record<string, string> = {
  characters: '人物关系图',
  geography: '地理关系图',
  rules: '规则体系图',
  plot: '主线规划图',
}

const legendTitle = ref(legendTitles.characters)

const tabLegendItems: Record<string, { label: string; color: string }[]> = {
  characters: [
    { label: '主角', color: 'var(--xy-brand-500)' },
    { label: '盟友', color: 'var(--xy-success)' },
    { label: '敌对', color: 'var(--xy-danger)' },
    { label: '中立', color: 'var(--xy-warning)' },
  ],
  geography: [
    { label: '主城', color: 'var(--xy-brand-500)' },
    { label: '秘境', color: 'var(--xy-success)' },
    { label: '势力', color: 'var(--xy-warning)' },
    { label: '遗迹', color: 'var(--xy-danger)' },
  ],
  rules: [
    { label: '核心规则', color: 'var(--xy-brand-500)' },
    { label: '进阶规则', color: 'var(--xy-success)' },
    { label: '限制规则', color: 'var(--xy-danger)' },
    { label: '衍生规则', color: 'var(--xy-warning)' },
  ],
  plot: [
    { label: '主线', color: 'var(--xy-brand-500)' },
    { label: '支线', color: 'var(--xy-success)' },
    { label: '转折', color: 'var(--xy-danger)' },
    { label: '伏笔', color: 'var(--xy-warning)' },
  ],
}

const legendItems = ref(tabLegendItems.characters)

const nodes = ref<GraphNode[]>([])
const edges = ref<GraphEdge[]>([])
const loading = ref(false)
const detailVisible = ref(false)
const detailNode = ref<GraphNode | null>(null)

const typeColors: Record<GraphNodeType, string> = {
  protagonist: 'var(--xy-brand-500)',
  ally: 'var(--xy-success)',
  enemy: 'var(--xy-danger)',
  neutral: 'var(--xy-warning)',
  location: 'var(--xy-info)',
  faction: 'var(--xy-warning)',
  rule: 'var(--xy-brand-400)',
  plot: 'var(--xy-brand-500)',
  event: 'var(--xy-success)',
}

const edgeStyles: Record<GraphEdge['type'], { stroke: string; width: number; dash?: string; glow?: boolean }> = {
  intimate: { stroke: 'rgba(229,184,110,0.45)', width: 2.5, glow: true },
  opposite: { stroke: 'rgba(251,191,36,0.4)', width: 1.5, dash: '8 5' },
  causal: { stroke: 'rgba(167,139,250,0.4)', width: 2, glow: true },
  weak: { stroke: 'rgba(125,117,152,0.18)', width: 1 },
}

const popover = ref({
  show: false,
  x: 0,
  y: 0,
  id: '',
  name: '',
  role: '',
  color: '',
  connections: 0,
  chapters: 0,
})

const svgRef = ref<SVGSVGElement>()
const graphRef = ref<SVGGElement>()
let scale = 1
const translate = { x: 0, y: 0 }
let isPanning = false
const panStart = { x: 0, y: 0 }
let draggedNode: string | null = null
const dragOffset = { x: 0, y: 0 }
let isCentered = false
const graphPadding = 80

function circleLayout(count: number, radius = 200): { x: number; y: number }[] {
  const positions = []
  for (let i = 0; i < count; i++) {
    const angle = (i / count) * Math.PI * 2 - Math.PI / 2
    positions.push({ x: Math.cos(angle) * radius, y: Math.sin(angle) * radius })
  }
  return positions
}

function inferCharacterType(role: string): GraphNodeType {
  const r = role.toLowerCase()
  if (/主角|主人公|protagonist|lead/i.test(r)) return 'protagonist'
  if (/敌|反|反派|villain|enemy|opponent/i.test(r)) return 'enemy'
  if (/友|盟|同伴|ally|friend|companion/i.test(r)) return 'ally'
  return 'neutral'
}

function inferSettingType(settingType: string, tab: 'geography' | 'rules'): GraphNodeType {
  const t = settingType.toLowerCase()
  if (tab === 'geography') {
    if (/派|宗|盟|faction|sect|clan/.test(t)) return 'faction'
    return 'location'
  }
  return 'rule'
}

function updateConnections() {
  nodes.value.forEach((n) => {
    n.connections = edges.value.filter((e) => e.from === n.id || e.to === n.id).length
  })
}

function buildCharacterGraph(chars: Character[]) {
  if (chars.length === 0) return
  const positions = circleLayout(chars.length, 200)
  const protagonist = chars.find((c) => inferCharacterType(c.role) === 'protagonist') || chars[0]
  nodes.value = chars.map((c, i) => ({
    id: c.id,
    name: c.name,
    role: c.role,
    type: inferCharacterType(c.role),
    identity: c.description?.slice(0, 60) || c.personality?.slice(0, 60) || '',
    description: c.description,
    connections: 0,
    chapters: 0,
    x: positions[i].x,
    y: positions[i].y,
  }))
  edges.value = []
  chars.forEach((c) => {
    if (c.id === protagonist.id) return
    const type = inferCharacterType(c.role)
    let edgeType: GraphEdge['type'] = 'causal'
    if (type === 'enemy') edgeType = 'opposite'
    else if (type === 'ally') edgeType = 'intimate'
    edges.value.push({
      from: protagonist.id,
      to: c.id,
      label: type === 'enemy' ? '对立' : type === 'ally' ? '同盟' : '关联',
      type: edgeType,
    })
  })
  updateConnections()
}

function buildSettingGraph(settings: WorldSetting[], tab: 'geography' | 'rules') {
  if (settings.length === 0) return
  const positions = circleLayout(settings.length, 200)
  nodes.value = settings.map((s, i) => ({
    id: s.id,
    name: s.name,
    role: s.setting_type,
    type: inferSettingType(s.setting_type, tab),
    identity: s.description?.slice(0, 60) || '',
    description: s.description,
    connections: 0,
    chapters: 0,
    x: positions[i].x,
    y: positions[i].y,
  }))
  edges.value = []
  for (let i = 0; i < settings.length - 1; i++) {
    edges.value.push({
      from: settings[i].id,
      to: settings[i + 1].id,
      label: tab === 'geography' ? '相邻' : '派生',
      type: tab === 'geography' ? 'weak' : 'causal',
    })
  }
  updateConnections()
}

function buildPlotGraph(plotNodes: StorylineNode[]) {
  if (plotNodes.length === 0) return
  nodes.value = plotNodes.map((n) => ({
    id: n.id,
    name: n.title,
    role: n.node_type,
    type: n.node_type === 'milestone' ? 'plot' : 'event',
    identity: n.description?.slice(0, 60) || '',
    description: n.description,
    connections: (n.parent_ids?.length || 0) + (n.child_ids?.length || 0),
    chapters: n.chapter_index ?? 0,
    x: n.x ?? 0,
    y: n.y ?? 0,
  }))
  edges.value = []
  plotNodes.forEach((n) => {
    n.child_ids?.forEach((childId) => {
      edges.value.push({ from: n.id, to: childId, label: '推进', type: 'causal' })
    })
  })
  updateConnections()
}

function makeDemoData(tab: string) {
  if (tab === 'characters') {
    nodes.value = [
      { id: 'demo-c1', name: '唐凌轩', role: '主角', type: 'protagonist', identity: '渊墟觉醒者，背负星渊印记', connections: 0, chapters: 12, x: 0, y: -160 },
      { id: 'demo-c2', name: '赵天行', role: '导师', type: 'ally', identity: '训练馆馆长，通脉巅峰', connections: 0, chapters: 8, x: -160, y: 40 },
      { id: 'demo-c3', name: '韩铮', role: '对手', type: 'enemy', identity: '通脉后期，拳法刚猛', connections: 0, chapters: 6, x: 160, y: 40 },
      { id: 'demo-c4', name: '苏晚晴', role: '盟友', type: 'ally', identity: '情报商人，嗅觉敏锐', connections: 0, chapters: 4, x: 0, y: 180 },
    ]
    edges.value = [
      { from: 'demo-c1', to: 'demo-c2', label: '师徒', type: 'intimate' },
      { from: 'demo-c1', to: 'demo-c3', label: '对立', type: 'opposite' },
      { from: 'demo-c1', to: 'demo-c4', label: '合作', type: 'intimate' },
      { from: 'demo-c2', to: 'demo-c3', label: '因果', type: 'causal' },
    ]
  } else if (tab === 'geography') {
    nodes.value = [
      { id: 'demo-g1', name: '渊城', role: '主城', type: 'location', identity: '人类最后的巨城，悬浮于渊海之上', connections: 0, chapters: 0, x: 0, y: -120 },
      { id: 'demo-g2', name: '黑墟', role: '秘境', type: 'location', identity: '星渊裂隙所在，魔气弥漫', connections: 0, chapters: 0, x: -140, y: 80 },
      { id: 'demo-g3', name: '天工阁', role: '势力', type: 'faction', identity: '炼器与情报中枢', connections: 0, chapters: 0, x: 140, y: 80 },
    ]
    edges.value = [
      { from: 'demo-g1', to: 'demo-g2', label: '相邻', type: 'weak' },
      { from: 'demo-g1', to: 'demo-g3', label: '统属', type: 'causal' },
    ]
  } else if (tab === 'rules') {
    nodes.value = [
      { id: 'demo-r1', name: '星渊共鸣', role: '核心规则', type: 'rule', identity: '觉醒者与星渊建立精神链接', connections: 0, chapters: 0, x: 0, y: -100 },
      { id: 'demo-r2', name: '魔气侵蚀', role: '限制规则', type: 'rule', identity: '过度使用渊力会遭受反噬', connections: 0, chapters: 0, x: -160, y: 60 },
      { id: 'demo-r3', name: '境界体系', role: '进阶规则', type: 'rule', identity: '通脉、凝神、化渊三境九重', connections: 0, chapters: 0, x: 160, y: 60 },
    ]
    edges.value = [
      { from: 'demo-r1', to: 'demo-r2', label: '制衡', type: 'opposite' },
      { from: 'demo-r1', to: 'demo-r3', label: '派生', type: 'causal' },
    ]
  } else {
    nodes.value = [
      { id: 'demo-p1', name: '渊启', role: '开端', type: 'plot', identity: '星渊觉醒，主角踏入修行', connections: 0, chapters: 1, x: -180, y: 0 },
      { id: 'demo-p2', name: '试炼', role: '转折', type: 'event', identity: '与韩铮的首次正面交锋', connections: 0, chapters: 5, x: 0, y: -80 },
      { id: 'demo-p3', name: '裂隙', role: '高潮', type: 'plot', identity: '黑墟裂隙开启，真相浮现', connections: 0, chapters: 12, x: 180, y: 0 },
    ]
    edges.value = [
      { from: 'demo-p1', to: 'demo-p2', label: '推进', type: 'causal' },
      { from: 'demo-p2', to: 'demo-p3', label: '推进', type: 'causal' },
    ]
  }
  updateConnections()
}

async function loadTabData(tab: string) {
  loading.value = true
  hidePopover()
  isCentered = false
  let hasData = false
  try {
    const id = novelId.value
    if (id && id !== '1') {
      try {
        const data = await getWorldview(tab, id)
        if (data.nodes.length > 0) {
          nodes.value = data.nodes
          edges.value = data.edges
          hasData = true
        }
      } catch (e) {
        console.warn('世界观聚合接口不可用，回退到圣经库获取:', e)
      }
      if (!hasData) {
        if (tab === 'characters') {
          await bibleStore.fetchCharacters(id)
          if (bibleStore.characters.length > 0) {
            buildCharacterGraph(bibleStore.characters)
            hasData = true
          }
        } else if (tab === 'geography' || tab === 'rules') {
          await bibleStore.fetchSettings(id)
          const type = tab === 'geography' ? 'location' : 'rule'
          const filtered = bibleStore.settings.filter(
            (s) =>
              s.setting_type?.toLowerCase().includes(type) ||
              s.setting_type?.includes(type === 'location' ? '地理' : '规则')
          )
          if (filtered.length > 0) {
            buildSettingGraph(filtered, tab as 'geography' | 'rules')
            hasData = true
          }
        } else if (tab === 'plot') {
          try {
            const plotNodes = await listNodesByNovel(id)
            if (plotNodes.length > 0) {
              buildPlotGraph(plotNodes)
              hasData = true
            }
          } catch (e) {
            // 剧情节点 API 错误时降级为示例
          }
        }
      }
    }
    if (!hasData) {
      makeDemoData(tab)
    }
  } finally {
    loading.value = false
    nextTick(renderGraph)
  }
}

function renderGraph() {
  const g = graphRef.value
  if (!g) return

  g.innerHTML = ''
  if (!isCentered && nodes.value.length > 0) {
    fitGraph()
    isCentered = true
  }
  updateTransform()

  const ns = 'http://www.w3.org/2000/svg'

  // Draw edges
  edges.value.forEach((rel, idx) => {
    const from = nodes.value.find((c) => c.id === rel.from)
    const to = nodes.value.find((c) => c.id === rel.to)
    if (!from || !to) return

    const style = edgeStyles[rel.type]
    const line = document.createElementNS(ns, 'line')
    line.setAttribute('x1', String(from.x))
    line.setAttribute('y1', String(from.y))
    line.setAttribute('x2', String(to.x))
    line.setAttribute('y2', String(to.y))
    line.setAttribute('stroke', style.stroke)
    line.setAttribute('stroke-width', String(style.width))
    if (style.dash) line.setAttribute('stroke-dasharray', style.dash)
    if (style.glow) line.setAttribute('filter', 'url(#glow)')
    if (rel.type === 'causal') line.setAttribute('marker-end', 'url(#arrow-purple)')
    if (idx % 2 === 0 && rel.type !== 'weak') {
      line.classList.add('flowing-line')
      line.setAttribute('stroke-dasharray', style.dash || '12 8')
    }
    g.appendChild(line)

    const midX = (from.x + to.x) / 2
    const midY = (from.y + to.y) / 2
    const text = document.createElementNS(ns, 'text')
    text.setAttribute('x', String(midX))
    text.setAttribute('y', String(midY - 8))
    text.setAttribute('text-anchor', 'middle')
    text.setAttribute('font-size', '10')
    text.setAttribute('fill', 'var(--xy-text-4)')
    text.textContent = rel.label
    g.appendChild(text)
  })

  // Draw nodes
  nodes.value.forEach((char) => {
    const nodeG = document.createElementNS(ns, 'g')
    nodeG.setAttribute('transform', `translate(${char.x},${char.y})`)
    nodeG.setAttribute('class', 'graph-node')
    nodeG.addEventListener('mousedown', (e) => startDrag(e, char.id))
    nodeG.addEventListener('mouseenter', () => nodeG.classList.add('hovered'))
    nodeG.addEventListener('mouseleave', () => nodeG.classList.remove('hovered'))
    nodeG.addEventListener('click', (e) => showPopover(e, char))

    const shadow = document.createElementNS(ns, 'circle')
    shadow.setAttribute('r', '26')
    shadow.setAttribute('fill', typeColors[char.type] || 'var(--xy-brand-500)')
    shadow.setAttribute('opacity', '0.12')
    shadow.setAttribute('class', 'node-shadow')
    nodeG.appendChild(shadow)

    const circle = document.createElementNS(ns, 'circle')
    circle.setAttribute('r', '22')
    circle.setAttribute('fill', 'var(--xy-surface-2)')
    circle.setAttribute('stroke', typeColors[char.type] || 'var(--xy-brand-500)')
    circle.setAttribute('stroke-width', '2')
    circle.setAttribute('class', 'node-circle')
    nodeG.appendChild(circle)

    const text = document.createElementNS(ns, 'text')
    text.setAttribute('text-anchor', 'middle')
    text.setAttribute('y', '4')
    text.setAttribute('font-size', '11')
    text.setAttribute('font-weight', '500')
    text.setAttribute('fill', 'var(--xy-text-1)')
    text.textContent = char.name
    nodeG.appendChild(text)

    g.appendChild(nodeG)
  })
}

function startDrag(e: MouseEvent, nodeId: string) {
  e.stopPropagation()
  draggedNode = nodeId
  const char = nodes.value.find((c) => c.id === nodeId)
  if (!char) return
  const svg = svgRef.value
  if (!svg) return
  const rect = svg.getBoundingClientRect()
  const mx = (e.clientX - rect.left - translate.x) / scale
  const my = (e.clientY - rect.top - translate.y) / scale
  dragOffset.x = mx - char.x
  dragOffset.y = my - char.y
  hidePopover()
}

function onMouseMove(e: MouseEvent) {
  if (!draggedNode) {
    if (!isPanning) return
    translate.x = e.clientX - panStart.x
    translate.y = e.clientY - panStart.y
    updateTransform()
    return
  }
  const svg = svgRef.value
  if (!svg) return
  const rect = svg.getBoundingClientRect()
  const mx = (e.clientX - rect.left - translate.x) / scale
  const my = (e.clientY - rect.top - translate.y) / scale
  const char = nodes.value.find((c) => c.id === draggedNode)
  if (char) {
    char.x = mx - dragOffset.x
    char.y = my - dragOffset.y
    renderGraph()
  }
}

function onMouseUp() {
  draggedNode = null
  isPanning = false
}

function startPan(e: MouseEvent) {
  if (draggedNode) return
  isPanning = true
  panStart.x = e.clientX - translate.x
  panStart.y = e.clientY - translate.y
  hidePopover()
}

function doPan(e: MouseEvent) {
  if (!isPanning || draggedNode) return
  translate.x = e.clientX - panStart.x
  translate.y = e.clientY - panStart.y
  updateTransform()
}

function endPan() {
  isPanning = false
}

function doZoom(e: WheelEvent) {
  e.preventDefault()
  const delta = e.deltaY > 0 ? 0.9 : 1.1
  scale = Math.max(0.3, Math.min(3, scale * delta))
  updateTransform()
}

function zoomIn() {
  scale = Math.min(3, scale * 1.2)
  updateTransform()
}

function zoomOut() {
  scale = Math.max(0.3, scale * 0.8)
  updateTransform()
}

function resetView() {
  centerGraphAtScale(1)
}

function updateTransform() {
  const g = graphRef.value
  if (g) g.setAttribute('transform', `translate(${translate.x},${translate.y}) scale(${scale})`)
}

function fitGraph() {
  const svg = svgRef.value
  if (!svg || nodes.value.length === 0) return
  const xs = nodes.value.map((n) => n.x)
  const ys = nodes.value.map((n) => n.y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const bboxW = Math.max(maxX - minX, 1)
  const bboxH = Math.max(maxY - minY, 1)
  const availW = Math.max(svg.clientWidth - graphPadding * 2, 100)
  const availH = Math.max(svg.clientHeight - graphPadding * 2, 100)
  scale = Math.min(availW / bboxW, availH / bboxH, 1.5)
  translate.x = (svg.clientWidth - bboxW * scale) / 2 - minX * scale
  translate.y = (svg.clientHeight - bboxH * scale) / 2 - minY * scale
}

function centerGraphAtScale(s: number) {
  const svg = svgRef.value
  if (!svg || nodes.value.length === 0) return
  const xs = nodes.value.map((n) => n.x)
  const ys = nodes.value.map((n) => n.y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const bboxW = Math.max(maxX - minX, 1)
  const bboxH = Math.max(maxY - minY, 1)
  scale = s
  translate.x = (svg.clientWidth - bboxW * scale) / 2 - minX * scale
  translate.y = (svg.clientHeight - bboxH * scale) / 2 - minY * scale
  updateTransform()
}

function showPopover(e: MouseEvent, char: GraphNode) {
  if (draggedNode) return
  e.stopPropagation()
  const svg = svgRef.value
  if (!svg) return
  const rect = svg.getBoundingClientRect()
  popover.value = {
    show: true,
    x: e.clientX - rect.left + 12,
    y: e.clientY - rect.top + 12,
    id: char.id,
    name: char.name,
    role: `${char.role} · ${char.identity}`,
    color: typeColors[char.type] || 'var(--xy-brand-500)',
    connections: char.connections,
    chapters: char.chapters,
  }
}

function hidePopover() {
  popover.value.show = false
}

function popoverAction(action: string) {
  if (action === 'view') {
    detailNode.value = nodes.value.find((n) => n.id === popover.value.id) || null
    detailVisible.value = true
  } else if (action === 'edit') {
    const id = novelId.value
    if (id && id !== '1') {
      router.push(`/workspace/${id}/writing/1`)
    } else {
      message.info('请先创建小说以编辑世界观')
    }
  }
  hidePopover()
}

function switchTab(tab: string) {
  activeTab.value = tab
  legendTitle.value = legendTitles[tab]
  legendItems.value = tabLegendItems[tab]
  loadTabData(tab)
}

async function ensureNovelIdLoaded() {
  if ((!novelId.value || novelId.value === '1') && novelStore.novels.length === 0) {
    try {
      await novelStore.fetchNovels({ page: 1 })
    } catch (e) {
      console.warn('加载小说列表失败:', e)
    }
  }
}

onMounted(async () => {
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
  await ensureNovelIdLoaded()
  loadTabData(activeTab.value)
})

watch(novelId, (newId, oldId) => {
  if (newId && newId !== oldId && newId !== '1') {
    loadTabData(activeTab.value)
  }
})

onUnmounted(() => {
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseup', onMouseUp)
})
</script>

<style scoped>
.worldview-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.wv-tabs {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 0 24px;
  background: var(--xy-bg-canvas);
  border-bottom: 1px solid var(--xy-border-1);
  flex-shrink: 0;
  overflow-x: auto;
}

.wv-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 12px 18px;
  border: none;
  background: transparent;
  color: var(--xy-text-2);
  font-size: 13px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
  transition: all var(--xy-dur-sm);
  position: relative;
}

.wv-tab:hover {
  color: var(--xy-text-1);
}

.wv-tab.active {
  color: var(--xy-text-1);
}

.wv-tab.active::after {
  content: '';
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 0;
  height: 2px;
  border-radius: 2px 2px 0 0;
  background: linear-gradient(90deg, var(--xy-brand-400), var(--xy-brand-starlight), var(--xy-brand-400));
  background-size: 200% 100%;
  box-shadow: 0 -2px 8px rgba(196, 181, 253, 0.3);
  animation: xy-border-flow 3s linear infinite;
}

.tab-icon {
  width: 14px;
  height: 14px;
}

.tab-icon :deep(path),
.tab-icon :deep(g) {
  stroke-width: 2;
}

.icon-14 {
  width: 14px;
  height: 14px;
}

.zoom-icon :deep(path),
.zoom-icon :deep(g) {
  stroke-width: 2.5;
}

.wv-canvas-area {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: var(--xy-bg-page);
}

.wv-svg {
  display: block;
  cursor: move;
}

:deep(.graph-node) {
  cursor: pointer;
  transition: transform var(--xy-dur-sm) var(--xy-ease-spring);
}

:deep(.graph-node .node-circle) {
  transition: all var(--xy-dur-sm);
}

:deep(.graph-node.hovered) {
  transform: scale(1.12);
}

:deep(.graph-node.hovered .node-circle) {
  filter: url(#glow-strong);
  stroke-width: 3;
}

:deep(.graph-node.hovered .node-shadow) {
  opacity: 0.22;
}

:deep(.graph-node:not(.hovered) .node-circle) {
  animation: node-pulse 3s ease-in-out infinite;
}

@keyframes node-pulse {
  0%, 100% { filter: drop-shadow(0 0 2px rgba(124, 108, 191, 0.1)); }
  50% { filter: drop-shadow(0 0 6px rgba(124, 108, 191, 0.25)); }
}

:deep(.flowing-line) {
  animation: line-flow 2s linear infinite;
}

@keyframes line-flow {
  from { stroke-dashoffset: 24; }
  to { stroke-dashoffset: 0; }
}

.node-popover {
  position: absolute;
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-2);
  border-radius: var(--xy-radius-md, 8px);
  padding: 12px;
  min-width: 180px;
  box-shadow: var(--xy-shadow-lg);
  z-index: 100;
  animation: xy-fade-in var(--xy-dur-sm) var(--xy-ease-standard);
}

.popover-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.popover-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.popover-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--xy-text-1);
}

.popover-role {
  margin-left: auto;
  font-size: 11px;
  color: var(--xy-text-3);
}

.popover-body {
  font-size: 12px;
  color: var(--xy-text-2);
  line-height: 1.6;
  margin-bottom: 10px;
}

.popover-body p {
  margin: 0;
}

.popover-actions {
  display: flex;
  gap: 8px;
}

.popover-actions button {
  flex: 1;
  padding: 5px 10px;
  border-radius: var(--xy-radius-sm, 5px);
  border: 1px solid var(--xy-border-1);
  background: var(--xy-surface-2);
  color: var(--xy-text-2);
  font-size: 12px;
  cursor: pointer;
  transition: all var(--xy-dur-sm);
}

.popover-actions button:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
}

.wv-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  pointer-events: none;
  color: var(--xy-text-3);
}

.wv-empty-icon {
  width: 40px;
  height: 40px;
  opacity: 0.5;
}

.wv-spin {
  animation: wv-spin 1s linear infinite;
}

@keyframes wv-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.wv-empty-text {
  font-size: 13px;
  margin: 0;
}

.zoom-controls {
  position: absolute;
  bottom: 20px;
  right: 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-md, 8px);
  padding: 6px;
}

.zoom-controls button {
  width: 32px;
  height: 32px;
  border-radius: var(--xy-radius-sm, 5px);
  border: none;
  background: transparent;
  color: var(--xy-text-2);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--xy-dur-sm);
}

.zoom-controls button:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
}

.wv-legend {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(20, 17, 39, 0.9);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-md, 8px);
  padding: 12px 14px;
  font-size: 11px;
  color: var(--xy-text-3);
  backdrop-filter: blur(8px);
  min-width: 140px;
  overflow: hidden;
}

.wv-legend::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(196, 181, 253, 0.18), rgba(124, 108, 191, 0.12), rgba(236, 72, 153, 0.08), transparent);
  background-size: 200% 100%;
  animation: xy-border-flow 8s linear infinite;
  pointer-events: none;
}

.legend-title {
  font-weight: 500;
  margin-bottom: 8px;
  color: var(--xy-text-2);
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 10px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-divider {
  height: 1px;
  background: var(--xy-border-1);
  margin: 8px 0;
}

.legend-lines {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.legend-line-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-line-item svg {
  flex-shrink: 0;
}

.legend-hint {
  margin-top: 10px;
  font-size: 10px;
  color: var(--xy-text-4);
}

.detail-body {
  padding: 4px 0;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.detail-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.detail-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--xy-text-1);
}

.detail-role {
  margin-left: auto;
  font-size: 12px;
  color: var(--xy-text-3);
  background: var(--xy-surface-2);
  padding: 2px 8px;
  border-radius: var(--xy-radius-sm);
}

.detail-identity {
  font-size: 13px;
  color: var(--xy-text-2);
  line-height: 1.6;
  margin: 0 0 16px;
}

.detail-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--xy-text-3);
}
</style>