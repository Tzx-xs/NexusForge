import { ref } from 'vue'
import { useTheme } from './theme'

const isInitialized = ref(false)
const initError = ref<string | null>(null)

export function useAppInit() {
  const init = async () => {
    try {
      const { initTheme } = useTheme()
      initTheme()

      console.log(`Nexus v${import.meta.env.VITE_APP_VERSION}`)
      isInitialized.value = true
    } catch (error) {
      initError.value = error instanceof Error ? error.message : 'Initialization failed'
      console.error('App init error:', error)
    }
  }

  return {
    isInitialized,
    initError,
    init,
  }
}
