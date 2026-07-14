import { ref, watch } from 'vue'

export type Theme = 'dark' | 'light' | 'system'

const theme = ref<Theme>(
  (localStorage.getItem('nexus-theme') as Theme) || 'dark'
)

function applyTheme(t: Theme) {
  const isDark = t === 'dark' || (t === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  document.documentElement.classList.toggle('dark', isDark)
}

// watcher 只创建一次，在模块级别
watch(theme, (newTheme) => {
  applyTheme(newTheme)
})

export function useTheme() {
  const setTheme = (newTheme: Theme) => {
    theme.value = newTheme
    localStorage.setItem('nexus-theme', newTheme)
    applyTheme(newTheme)
  }

  const initTheme = () => {
    applyTheme(theme.value)
    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (theme.value === 'system') {
        applyTheme('system')
      }
    })
  }

  return {
    theme,
    setTheme,
    initTheme,
  }
}
