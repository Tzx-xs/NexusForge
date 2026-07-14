import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAppInit } from './core'
import './style.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// 初始化主题等核心模块
useAppInit().init()

app.mount('#app')
