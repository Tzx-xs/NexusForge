<template>
  <div class="dag-view">
    <div class="dag-toolbar">
      <div class="toolbar-left">
        <n-select
          v-model:value="selectedStorylineId"
          :options="storylineOptions"
          size="small"
          style="width: 160px"
          @update:value="loadNodes"
        />
        <n-tag v-if="selectedStorylineId" size="small" type="primary" @click="addNode">
          <template #icon><Plus /></template>
          添加节点
        </n-tag>
      </div>
      <div class="toolbar-right">
        <n-button-group size="tiny">
          <n-button :circle="true" @click="zoomIn">+</n-button>
          <n-button :circle="true" @click="zoomOut">-</n-button>
        </n-button-group>
        <n-button size="tiny" @click="resetView">重置</n-button>
      </div>
    </div>

    <div ref="canvasRef" class="dag-canvas" @wheel.prevent="onWheel" @mousedown="onCanvasMouseDown">
      <svg
        class="dag-svg"
        :style="{ transform: `translate(${viewOffset.x}px, ${viewOffset.y}px) scale(${zoom})` }"
        :width="canvasWidth"
        :height="canvasHeight"
      >
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#999" />
          </marker>
        </defs>

        <g class="edges">
          <path
            v-for="edge in edges"
            :key="edge.id"
            :d="edge.path"
            fill="none"
            stroke="#ccc"
            stroke-width="2"
            marker-end="url(#arrowhead)"
            :class="{ 'edge-selected': selectedEdge === edge.id }"
            @click.stop="selectEdge(edge.id)"
          />
        </g>

        <g class="nodes">
          <foreignObject
            v-for="node in nodes"
            :key="node.id"
            :x="node.x"
            :y="node.y"
            :width="node.width"
            :height="node.height"
            class="node-wrapper"
            :class="{
              'node-selected': selectedNodeId === node.id,
              'node-dragging': draggingNodeId === node.id,
            }"
            @mousedown.stop="onNodeMouseDown($event, node)"
            @mouseup.stop="onNodeMouseUp(node)"
          >
            <div class="dag-node" :style="{ borderLeftColor: getNodeColor(node) }">
              <div class="node-header">
                <span class="node-title">{{ node.title }}</span>
                <span class="node-type">{{ getTypeLabel(node.node_type) }}</span>
              </div>
              <div class="node-body">{{ node.description || '点击编辑' }}</div>
              <div class="node-footer">
                <span v-if="node.chapter_index" class="chapter-tag">
                  第{{ node.chapter_index }}章
                </span>
                <n-tag size="tiny" :type="getStatusType(node.status)">
                  {{ getStatusLabel(node.status) }}
                </n-tag>
              </div>
            </div>
          </foreignObject>
        </g>
      </svg>

      <div v-if="nodes.length === 0" class="empty-hint">
        <n-empty description="暂无节点，点击添加创建第一个剧情节点" />
      </div>
    </div>

    <div v-if="selectedNode" class="node-detail">
      <div class="detail-header">
        <span>节点详情</span>
        <n-button size="tiny" text @click="selectedNodeId = null">
          <X />
        </n-button>
      </div>
      <div class="detail-body">
        <div class="detail-item">
          <label>标题</label>
          <n-input
            v-model:value="editingTitle"
            size="small"
            @blur="updateNodeField('title', editingTitle)"
          />
        </div>
        <div class="detail-item">
          <label>描述</label>
          <n-input
            v-model:value="editingDesc"
            type="textarea"
            :rows="3"
            size="small"
            @blur="updateNodeField('description', editingDesc)"
          />
        </div>
        <div class="detail-item">
          <label>类型</label>
          <n-select
            v-model:value="editingType"
            :options="nodeTypeOptions"
            size="small"
            @update:value="updateNodeField('node_type', editingType)"
          />
        </div>
        <div class="detail-item">
          <label>状态</label>
          <n-select
            v-model:value="editingStatus"
            :options="statusOptions"
            size="small"
            @update:value="updateNodeField('status', editingStatus)"
          />
        </div>
        <div class="detail-item">
          <label>关联章节</label>
          <n-input-number
            v-model:value="editingChapter"
            size="small"
            placeholder="章节序号"
            @update:value="updateNodeField('chapter_index', editingChapter)"
          />
        </div>
        <div class="detail-actions">
          <n-button size="small" type="error" @click="deleteSelectedNode">删除节点</n-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { NButton, NSelect, NInput, NInputNumber, NTag, NEmpty, useMessage } from 'naive-ui'
import { Plus, X } from '@vicons/tabler'
import {
  listStorylines,
  createNode as apiCreateNode,
  updateNode as apiUpdateNode,
  deleteNode as apiDeleteNode,
  listNodes as apiListNodes,
  type Storyline,
  type StorylineNode,
} from '@/api/storylines'

const props = defineProps<{
  novelId: string
}>()

const message = useMessage()

const canvasRef = ref<HTMLElement | null>(null)
const canvasWidth = ref(2000)
const canvasHeight = ref(2000)

const zoom = ref(1)
const viewOffset = ref({ x: 50, y: 50 })

const storylines = ref<Storyline[]>([])
const selectedStorylineId = ref<string>('')
const nodes = ref<StorylineNode[]>([])
const selectedNodeId = ref<string | null>(null)
const selectedEdge = ref<string | null>(null)

const editingTitle = ref('')
const editingDesc = ref('')
const editingType = ref('scene')
const editingStatus = ref('draft')
const editingChapter = ref<number | null>(null)

const draggingNodeId = ref<string | null>(null)
const dragStartPos = ref({ x: 0, y: 0 })
const dragStartNodePos = ref({ x: 0, y: 0 })
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0 })

const storylineOptions = computed(() =>
  storylines.value.map((s) => ({ label: s.name, value: s.id }))
)

const nodeTypeOptions = [
  { label: '场景', value: 'scene' },
  { label: '事件', value: 'event' },
  { label: '转折', value: 'turning_point' },
  { label: '高潮', value: 'climax' },
  { label: '结局', value: 'ending' },
]

const statusOptions = [
  { label: '草稿', value: 'draft' },
  { label: '规划中', value: 'planned' },
  { label: '已完成', value: 'completed' },
]

const selectedNode = computed(() => nodes.value.find((n) => n.id === selectedNodeId.value) || null)

watch(selectedNode, (node) => {
  if (node) {
    editingTitle.value = node.title
    editingDesc.value = node.description
    editingType.value = node.node_type
    editingStatus.value = node.status
    editingChapter.value = node.chapter_index ?? null
  }
})

const edges = computed(() => {
  const edgeList: { id: string; path: string; source: string; target: string }[] = []
  for (const node of nodes.value) {
    for (const childId of node.child_ids) {
      const child = nodes.value.find((n) => n.id === childId)
      if (child) {
        const sx = node.x + node.width
        const sy = node.y + node.height / 2
        const tx = child.x
        const ty = child.y + child.height / 2
        const mx = (sx + tx) / 2
        const path = `M ${sx} ${sy} C ${mx} ${sy}, ${mx} ${ty}, ${tx} ${ty}`
        edgeList.push({
          id: `${node.id}-${childId}`,
          path,
          source: node.id,
          target: childId,
        })
      }
    }
  }
  return edgeList
})

function getNodeColor(node: StorylineNode) {
  const colors: Record<string, string> = {
    scene: '#2080f0',
    event: '#18a058',
    turning_point: '#f0a020',
    climax: '#d03050',
    ending: '#722ed1',
  }
  return colors[node.node_type] || '#2080f0'
}

function getTypeLabel(type: string) {
  const item = nodeTypeOptions.find((o) => o.value === type)
  return item?.label || type
}

function getStatusLabel(status: string) {
  const item = statusOptions.find((o) => o.value === status)
  return item?.label || status
}

function getStatusType(status: string) {
  switch (status) {
    case 'completed':
      return 'success'
    case 'planned':
      return 'warning'
    default:
      return 'default'
  }
}

function selectEdge(edgeId: string) {
  selectedEdge.value = selectedEdge.value === edgeId ? null : edgeId
  selectedNodeId.value = null
}

async function loadStorylines() {
  const res = await listStorylines(props.novelId)
  storylines.value = res
  if (res.length > 0 && !selectedStorylineId.value) {
    selectedStorylineId.value = res[0].id
    await loadNodes()
  }
}

async function loadNodes() {
  if (!selectedStorylineId.value) return
  const res = await apiListNodes(selectedStorylineId.value)
  nodes.value = res
  selectedNodeId.value = null
}

async function addNode() {
  if (!selectedStorylineId.value) return
  const newY = nodes.value.length > 0 ? Math.max(...nodes.value.map((n) => n.y)) + 100 : 50
  const res = await apiCreateNode(selectedStorylineId.value, {
    title: '新节点',
    description: '',
    node_type: 'scene',
    status: 'draft',
    x: 100 + Math.random() * 100,
    y: newY,
  })
  nodes.value.push(res)
  selectedNodeId.value = res.id
  message.success('节点已创建')
}

async function updateNodeField(field: string, value: any) {
  if (!selectedNodeId.value) return
  const node = nodes.value.find((n) => n.id === selectedNodeId.value)
  if (!node) return
  if ((node as any)[field] !== value) {
    ;(node as any)[field] = value
    await apiUpdateNode(selectedNodeId.value, { [field]: value })
  }
}

async function deleteSelectedNode() {
  if (!selectedNodeId.value) return
  const res = await apiDeleteNode(selectedNodeId.value)
  if (res.deleted) {
    nodes.value = nodes.value.filter((n) => n.id !== selectedNodeId.value)
    selectedNodeId.value = null
    message.success('节点已删除')
  }
}

function onWheel(e: WheelEvent) {
  const delta = e.deltaY > 0 ? 0.9 : 1.1
  zoom.value = Math.max(0.3, Math.min(2, zoom.value * delta))
}

function onCanvasMouseDown(e: MouseEvent) {
  if (e.button !== 0) return
  isPanning.value = true
  panStart.value = { x: e.clientX - viewOffset.value.x, y: e.clientY - viewOffset.value.y }

  const onMouseMove = (ev: MouseEvent) => {
    if (isPanning.value) {
      viewOffset.value = {
        x: ev.clientX - panStart.value.x,
        y: ev.clientY - panStart.value.y,
      }
    }
  }

  const onMouseUp = () => {
    isPanning.value = false
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
  }

  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

function onNodeMouseDown(e: MouseEvent, node: StorylineNode) {
  draggingNodeId.value = node.id
  selectedNodeId.value = node.id
  selectedEdge.value = null
  dragStartPos.value = { x: e.clientX, y: e.clientY }
  dragStartNodePos.value = { x: node.x, y: node.y }

  const onMouseMove = (ev: MouseEvent) => {
    if (draggingNodeId.value !== node.id) return
    const dx = (ev.clientX - dragStartPos.value.x) / zoom.value
    const dy = (ev.clientY - dragStartPos.value.y) / zoom.value
    node.x = Math.max(0, dragStartNodePos.value.x + dx)
    node.y = Math.max(0, dragStartNodePos.value.y + dy)
  }

  const onMouseUp = () => {
    if (draggingNodeId.value === node.id) {
      apiUpdateNode(node.id, { x: node.x, y: node.y })
      draggingNodeId.value = null
    }
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
  }

  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

function onNodeMouseUp(_node: StorylineNode) {
  draggingNodeId.value = null
}

function zoomIn() {
  zoom.value = Math.min(2, zoom.value * 1.2)
}

function zoomOut() {
  zoom.value = Math.max(0.3, zoom.value / 1.2)
}

function resetView() {
  zoom.value = 1
  viewOffset.value = { x: 50, y: 50 }
}

onMounted(() => {
  loadStorylines()
})
</script>

<style scoped>
.dag-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--xy-bg-canvas);
  position: relative;
}

.dag-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--xy-space-2) var(--xy-space-4);
  background: var(--xy-surface-1);
  border-bottom: var(--xy-border-w-1) solid var(--xy-divider);
  flex-shrink: 0;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--xy-space-3);
}

.dag-canvas {
  flex: 1;
  overflow: hidden;
  position: relative;
  cursor: grab;
  background-image:
    radial-gradient(circle, var(--xy-border-1) 1px, transparent 1px),
    linear-gradient(90deg, transparent 49.5%, var(--xy-border-1) 49.5%, var(--xy-border-1) 50.5%, transparent 50.5%),
    linear-gradient(transparent 49.5%, var(--xy-border-1) 49.5%, var(--xy-border-1) 50.5%, transparent 50.5%);
  background-size: 24px 24px, 24px 24px, 24px 24px;
}

.dag-canvas:active {
  cursor: grabbing;
}

.dag-svg {
  transform-origin: 0 0;
  will-change: transform;
}

.node-wrapper {
  cursor: move;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
}

.dag-node {
  width: 100%;
  height: 100%;
  background: var(--xy-surface-1);
  border: var(--xy-border-w-1) solid var(--xy-border-1);
  border-left: 3px solid var(--xy-brand-500);
  border-radius: var(--xy-radius-md);
  padding: var(--xy-space-2) var(--xy-space-3);
  display: flex;
  flex-direction: column;
  box-shadow: var(--xy-shadow-sm);
  transition:
    box-shadow var(--xy-dur-sm) var(--xy-ease-standard),
    transform var(--xy-dur-xs) var(--xy-ease-standard),
    border-color var(--xy-dur-sm) var(--xy-ease-standard);
  font-size: var(--xy-fs-xs);
}

.node-wrapper:hover .dag-node {
  box-shadow: var(--xy-shadow-md);
  transform: translateY(-1px);
}

.node-selected .dag-node {
  border-color: var(--xy-brand-500);
  box-shadow:
    0 0 0 2px var(--xy-brand-50),
    var(--xy-shadow-md);
}

.node-dragging .dag-node {
  box-shadow: var(--xy-shadow-lg);
  transform: scale(1.02);
}

.node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--xy-space-1);
}

.node-title {
  font-weight: var(--xy-fw-med);
  color: var(--xy-text-1);
  font-size: var(--xy-fs-sm);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-type {
  font-size: 10px;
  color: var(--xy-text-3);
  background: var(--xy-surface-2);
  padding: 2px 8px;
  border-radius: var(--xy-radius-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.node-body {
  flex: 1;
  color: var(--xy-text-2);
  font-size: var(--xy-fs-xs);
  line-height: 1.5;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.node-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--xy-space-2);
  padding-top: var(--xy-space-1);
  border-top: var(--xy-border-w-1) solid var(--xy-divider);
}

.chapter-tag {
  font-size: 10px;
  color: var(--xy-brand-600);
  background: var(--xy-brand-50);
  padding: 2px 8px;
  border-radius: var(--xy-radius-sm);
  font-weight: var(--xy-fw-med);
}

.edge-selected {
  stroke: var(--xy-brand-500) !important;
  stroke-width: 3px !important;
}

.empty-hint {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.node-detail {
  position: absolute;
  right: var(--xy-space-4);
  top: calc(var(--xy-panel-header-h) + var(--xy-space-3));
  width: 280px;
  background: var(--xy-surface-1);
  border-radius: var(--xy-radius-lg);
  box-shadow: var(--xy-shadow-lg);
  border: var(--xy-border-w-1) solid var(--xy-border-2);
  z-index: 100;
  overflow: hidden;
  animation: xy-fade-in var(--xy-dur-sm) var(--xy-ease-standard);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--xy-space-2) var(--xy-space-3);
  border-bottom: var(--xy-border-w-1) solid var(--xy-divider);
  font-weight: var(--xy-fw-sb);
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-1);
  background: var(--xy-surface-2);
}

.detail-body {
  padding: var(--xy-space-3);
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-2);
  max-height: 400px;
  overflow-y: auto;
}

.detail-item label {
  display: block;
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
  margin-bottom: var(--xy-space-1);
  font-weight: var(--xy-fw-med);
}

.detail-actions {
  padding-top: var(--xy-space-2);
  border-top: var(--xy-border-w-1) solid var(--xy-divider);
  display: flex;
  justify-content: flex-end;
}

@keyframes node-appear {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(8px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.node-wrapper {
  animation: node-appear var(--xy-dur-md) var(--xy-ease-standard);
}
</style>
