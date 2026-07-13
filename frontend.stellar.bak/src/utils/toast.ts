import { createDiscreteApi } from 'naive-ui'

// toast 弹窗主题由 App.vue 的 NConfigProvider 统一控制，此处不再持有 theme ref
const { message, notification, dialog, loadingBar } = createDiscreteApi(
  ['message', 'notification', 'dialog', 'loadingBar']
)

export const toast = {
  success(content: string) {
    message.success(content)
  },
  error(content: string) {
    message.error(content)
  },
  warning(content: string) {
    message.warning(content)
  },
  info(content: string) {
    message.info(content)
  },
}

export { message, notification, dialog, loadingBar }
