<template>
  <div class="iron-lock-panel">
    <div class="panel-section">
      <div class="section-header">
        <ShieldLock class="section-icon" />
        <span class="section-title">T0 铁锁</span>
      </div>
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else class="lock-stats">
        <div class="stat-card">
          <span class="stat-num">{{ ironLockData.fact_locks?.length || 0 }}</span>
          <span class="stat-label">事实锁</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ ironLockData.beat_locks?.length || 0 }}</span>
          <span class="stat-label">节拍锁</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ ironLockData.clue_locks?.length || 0 }}</span>
          <span class="stat-label">线索锁</span>
        </div>
      </div>
    </div>

    <div class="panel-section">
      <div class="section-header">
        <Users class="section-icon" />
        <span class="section-title">角色白名单</span>
      </div>
      <div class="character-tags">
        <span
          v-for="char in ironLockData.character_whitelist?.slice(0, 10) || []"
          :key="char"
          class="char-tag"
        >
          {{ char }}
        </span>
        <span v-if="!ironLockData.character_whitelist?.length" class="empty-text">暂无数据</span>
      </div>
    </div>

    <div class="panel-section">
      <div class="section-header">
        <Bone class="section-icon danger" />
        <span class="section-title">死亡名单</span>
      </div>
      <div class="death-list">
        <div
          v-for="char in ironLockData.death_list?.slice(0, 5) || []"
          :key="char"
          class="death-item"
        >
          <Bone class="death-icon" />
          <span>{{ char }}</span>
        </div>
        <div v-if="!ironLockData.death_list?.length" class="empty-text">暂无死亡角色</div>
      </div>
    </div>

    <div class="panel-section">
      <div class="section-header">
        <GitBranch class="section-icon" />
        <span class="section-title">关系图谱</span>
      </div>
      <div class="relationship-list">
        <div v-for="(rels, char) in topRelationships" :key="char" class="rel-item">
          <span class="rel-source">{{ char }}</span>
          <ArrowRight class="rel-arrow" />
          <span class="rel-target">{{ rels[0] || '—' }}</span>
        </div>
        <div v-if="!Object.keys(topRelationships).length" class="empty-text">暂无关系数据</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ShieldLock, Users, Bone, GitBranch, ArrowRight } from '@vicons/tabler'
import { getIronLock, type IronLockData } from '@/api/memory'
import { useCurrentNovelId } from '@/composables/useCurrentNovelId'

const { novelId } = useCurrentNovelId()
const loading = ref(false)
const ironLockData = ref<IronLockData>({
  fact_locks: [],
  beat_locks: [],
  clue_locks: [],
  character_whitelist: [],
  death_list: [],
  relationship_map: {},
})

const topRelationships = computed(() => {
  const map = ironLockData.value.relationship_map || {}
  const entries = Object.entries(map).slice(0, 5)
  return Object.fromEntries(entries)
})

async function fetchIronLock() {
  if (!novelId.value) return
  loading.value = true
  try {
    const res = await getIronLock(novelId.value)
    ironLockData.value = res
  } catch (e) {
    console.error('Failed to fetch iron lock:', e)
  } finally {
    loading.value = false
  }
}

watch(novelId, fetchIronLock)
onMounted(fetchIronLock)
</script>

<style scoped>
.iron-lock-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-section {
  background: var(--xy-surface-2);
  border-radius: 8px;
  padding: 12px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.section-icon {
  width: 14px;
  height: 14px;
  color: var(--xy-brand-500);
}

.section-icon.danger {
  color: var(--xy-danger);
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--xy-text-2);
}

.loading-state {
  text-align: center;
  padding: 20px;
  color: var(--xy-text-4);
  font-size: 12px;
}

.lock-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 4px;
  background: var(--xy-surface-1);
  border-radius: 6px;
}

.stat-num {
  font-size: 18px;
  font-weight: 700;
  color: var(--xy-brand-500);
  font-family: var(--xy-font-mono);
}

.stat-label {
  font-size: 11px;
  color: var(--xy-text-3);
  margin-top: 2px;
}

.character-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.char-tag {
  padding: 3px 8px;
  background: color-mix(in srgb, var(--xy-brand-500) 15%, transparent);
  color: var(--xy-brand-600);
  border-radius: 12px;
  font-size: 11px;
}

.death-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.death-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: var(--xy-surface-1);
  border-radius: 4px;
  font-size: 12px;
  color: var(--xy-text-3);
}

.death-icon {
  width: 12px;
  height: 12px;
  color: var(--xy-danger);
}

.relationship-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rel-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  background: var(--xy-surface-1);
  border-radius: 4px;
  font-size: 11px;
}

.rel-source {
  color: var(--xy-brand-600);
  font-weight: 500;
}

.rel-arrow {
  width: 12px;
  height: 12px;
  color: var(--xy-text-4);
  flex-shrink: 0;
}

.rel-target {
  color: var(--xy-text-2);
}

.empty-text {
  font-size: 12px;
  color: var(--xy-text-4);
  text-align: center;
  padding: 8px;
}
</style>
