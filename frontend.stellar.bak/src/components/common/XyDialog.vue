<template>
  <Teleport to="body">
    <Transition name="xy-dialog-fade">
      <div v-if="innerVisible" class="xy-dialog-mask" @click="handleMaskClick"></div>
    </Transition>
    <Transition name="xy-dialog-scale">
      <div
        v-if="innerVisible"
        class="xy-dialog-wrapper"
        role="dialog"
        aria-modal="true"
        aria-labelledby="xy-dialog-title"
      >
        <div class="xy-dialog">
          <div class="xy-dialog-header">
            <slot name="header">
              <h2 id="xy-dialog-title" class="xy-dialog-title">{{ title }}</h2>
            </slot>
          </div>
          <div class="xy-dialog-body">
            <slot />
          </div>
          <div class="xy-dialog-footer">
            <slot name="footer">
              <button class="xy-dialog-btn xy-dialog-btn-cancel" @click="handleCancel">
                {{ cancelText }}
              </button>
              <button class="xy-dialog-btn xy-dialog-btn-confirm" @click="handleConfirm">
                {{ confirmText }}
              </button>
            </slot>
          </div>
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
    title?: string
    confirmText?: string
    cancelText?: string
  }>(),
  {
    title: '',
    confirmText: '确认',
    cancelText: '取消',
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: []
  cancel: []
}>()

const innerVisible = ref(false)

watch(
  () => props.modelValue,
  (val) => {
    innerVisible.value = val
  },
  { immediate: true }
)

function handleConfirm() {
  // B4 修复：确认按钮默认关闭弹窗（帮助中心「知道了」此前点了无反应）
  innerVisible.value = false
  emit('update:modelValue', false)
  emit('confirm')
}

function handleCancel() {
  innerVisible.value = false
  emit('update:modelValue', false)
  emit('cancel')
}

function handleMaskClick() {
  handleCancel()
}
</script>

<style scoped>
.xy-dialog-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--xy-overlay);
  z-index: var(--xy-z-modal-backdrop);
}

.xy-dialog-wrapper {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--xy-z-modal);
  pointer-events: none;
}

.xy-dialog {
  pointer-events: auto;
  width: 420px;
  max-width: calc(100vw - 32px);
  max-height: calc(100vh - 32px);
  display: flex;
  flex-direction: column;
  background: var(--xy-surface-1);
  border-radius: var(--xy-radius-xl);
  box-shadow: var(--xy-shadow-modal);
  border: var(--xy-border-w-1) solid var(--xy-border-1);
  overflow: hidden;
}

.xy-dialog-header {
  flex-shrink: 0;
  padding: var(--xy-space-6) var(--xy-space-6) var(--xy-space-3);
}

.xy-dialog-title {
  margin: 0;
  font-size: var(--xy-fs-lg);
  font-weight: var(--xy-fw-sb);
  color: var(--xy-text-1);
  line-height: var(--xy-lh-snug);
  text-align: center;
}

.xy-dialog-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 var(--xy-space-6) var(--xy-space-5);
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-2);
  line-height: var(--xy-lh-normal);
}

.xy-dialog-footer {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--xy-space-3);
  padding: 0 var(--xy-space-6) var(--xy-space-6);
}

.xy-dialog-btn {
  height: 32px;
  padding: 0 var(--xy-space-5);
  border-radius: var(--xy-radius-md);
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-med);
  font-family: var(--xy-font-sans);
  cursor: pointer;
  transition:
    background var(--xy-dur-sm) var(--xy-ease-standard),
    color var(--xy-dur-sm) var(--xy-ease-standard),
    transform var(--xy-dur-sm) var(--xy-ease-standard),
    opacity var(--xy-dur-sm) var(--xy-ease-standard);
}

.xy-dialog-btn-cancel {
  background: transparent;
  border: var(--xy-border-w-1) solid var(--xy-border-1);
  color: var(--xy-text-2);
}

.xy-dialog-btn-cancel:hover {
  background: var(--xy-surface-2);
}

.xy-dialog-btn-confirm {
  background: var(--xy-brand-500);
  border: none;
  color: var(--xy-text-inverse);
  font-weight: var(--xy-fw-sb);
}

.xy-dialog-btn-confirm:hover {
  background: var(--xy-brand-400);
  transform: translateY(-1px);
}

.xy-dialog-fade-enter-active,
.xy-dialog-fade-leave-active {
  transition: opacity var(--xy-dur-md) var(--xy-ease-standard);
}

.xy-dialog-fade-enter-from,
.xy-dialog-fade-leave-to {
  opacity: 0;
}

.xy-dialog-scale-enter-active,
.xy-dialog-scale-leave-active {
  transition:
    opacity var(--xy-dur-md) var(--xy-ease-standard),
    transform var(--xy-dur-md) var(--xy-ease-standard);
}

.xy-dialog-scale-enter-from,
.xy-dialog-scale-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
