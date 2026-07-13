import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './styles/main.css'
import { toast } from './utils/toast'
import { fetchApiConfig } from './utils/config'

;(async () => {
  await fetchApiConfig()

  const app = createApp(App)
  const pinia = createPinia()

  app.config.errorHandler = (err, _instance, info) => {
    console.error('Vue error:', err, info)
    const errorCode = Date.now().toString(36).slice(-6)
    toast.error(
      `系统出现异常，请刷新页面重试。如问题持续，请联系支持。（错误代码：${errorCode}）`
    )
  }

  app.use(pinia)
  app.use(router)
  app.mount('#app')
})()
