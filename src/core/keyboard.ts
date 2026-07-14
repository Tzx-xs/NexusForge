import { onMounted, onUnmounted } from 'vue'

type KeyHandler = (event: KeyboardEvent) => void

interface KeyBinding {
  key: string
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  meta?: boolean
  handler: KeyHandler
}

const bindings: KeyBinding[] = []

export function useKeyboard() {
  const register = (binding: KeyBinding) => {
    bindings.push(binding)
  }

  const unregister = (binding: KeyBinding) => {
    const index = bindings.indexOf(binding)
    if (index > -1) {
      bindings.splice(index, 1)
    }
  }

  const handleKeydown = (event: KeyboardEvent) => {
    for (const binding of bindings) {
      const keyMatch = event.key.toLowerCase() === binding.key.toLowerCase()
      const ctrlMatch = binding.ctrl ? (event.ctrlKey || event.metaKey) : true
      const shiftMatch = binding.shift ? event.shiftKey : true
      const altMatch = binding.alt ? event.altKey : true
      const metaMatch = binding.meta ? event.metaKey : true

      if (keyMatch && ctrlMatch && shiftMatch && altMatch && metaMatch) {
        event.preventDefault()
        binding.handler(event)
      }
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeydown)
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown)
  })

  return {
    register,
    unregister,
  }
}
