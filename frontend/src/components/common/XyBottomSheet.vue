<template>
  <Teleport to="body">
    <Transition name="xy-bottom-sheet-fade">
      <div v-if="innerVisible" class="xy-bottom-sheet-mask" @click="handleMaskClick"></div>
    </Transition>
    <Transition name="xy-bottom-sheet-slide">
      <div
        v-if="innerVisible"
        class="xy-bottom-sheet"
        :style="{ height: height }"
        role="dialog"
        aria-modal="true"
      >
        <div class="xy-bottom-sheet-handle"></div>
        <div class="xy-bottom-sheet-body">
          <slot />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    height?: string
  }>(),
  {
    height: '50vh',
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const innerVisible = ref(false)

watch(
  () => props.modelValue,
  (val) => {
    innerVisible.value = val
  },
  { immediate: true }
)

function handleMaskClick() {
  innerVisible.value = false
  emit('update:modelValue', false)
}
</script>

<style scoped>
.xy-bottom-sheet-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--xy-overlay);
  z-index: var(--xy-z-modal-backdrop);
}

.xy-bottom-sheet {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  flex-direction: column;
  background: var(--xy-surface-1);
  border-radius: var(--xy-radius-xl) var(--xy-radius-xl) 0 0;
  box-shadow: var(--xy-shadow-lg);
  z-index: var(--xy-z-modal);
  overflow: hidden;
}

.xy-bottom-sheet-handle {
  width: 40px;
  height: 6px;
  border-radius: 3px;
  background: var(--xy-text-4);
  opacity: 0.3;
  margin: 8px auto 0;
  flex-shrink: 0;
}

.xy-bottom-sheet-body {
  flex: 1;
  overflow-y: auto;
}

.xy-bottom-sheet-fade-enter-active,
.xy-bottom-sheet-fade-leave-active {
  transition: opacity var(--xy-dur-md) var(--xy-ease-standard);
}

.xy-bottom-sheet-fade-enter-from,
.xy-bottom-sheet-fade-leave-to {
  opacity: 0;
}

.xy-bottom-sheet-slide-enter-active,
.xy-bottom-sheet-slide-leave-active {
  transition: transform var(--xy-dur-lg) var(--xy-ease-standard);
}

.xy-bottom-sheet-slide-enter-from,
.xy-bottom-sheet-slide-leave-to {
  transform: translateY(100%);
}
</style>
