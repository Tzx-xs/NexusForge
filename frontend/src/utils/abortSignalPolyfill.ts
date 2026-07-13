/** AbortSignal.timeout() 的 Firefox 兼容 polyfill。
 *
 * Firefox (< 130) 不支持 AbortSignal.timeout() 和 AbortSignal.any()。
 * 此 polyfill 使用 AbortController + setTimeout 模拟超时信号。
 */

/**
 * 创建一个在指定毫秒后自动 abort 的 AbortSignal。
 *
 * @param ms 超时毫秒数
 * @returns 在 ms 毫秒后自动 abort 的 AbortSignal 及其清理函数
 */
export function createTimeoutSignal(ms: number): { signal: AbortSignal; cleanup: () => void } {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(new DOMException('Timeout', 'TimeoutError')), ms)
  return {
    signal: controller.signal,
    cleanup: () => clearTimeout(timer),
  }
}

/**
 * 合并多个 AbortSignal — 任意一个 signal abort 时，合并后的 signal 也会 abort。
 *
 * Firefox 兼容的 AbortSignal.any() 替代方案。
 *
 * @param signals 要合并的 AbortSignal 数组
 * @returns 合并后的 AbortSignal + AbortController（用于传递给 fetch 的 signal 参数）
 */
export function combineAbortSignals(
  signals: AbortSignal[]
): { signal: AbortSignal; cleanup: () => void } {
  if (typeof AbortSignal.any === 'function') {
    return {
      signal: AbortSignal.any(signals),
      cleanup: () => {},
    }
  }

  const controller = new AbortController()
  const onAbort = () => {
    const reason = signals.find((s) => s.aborted)?.reason
    controller.abort(reason)
  }
  for (const signal of signals) {
    if (signal.aborted) {
      controller.abort(signal.reason)
      break
    }
    signal.addEventListener('abort', onAbort, { once: true })
  }
  return {
    signal: controller.signal,
    cleanup: () => {
      for (const signal of signals) {
        signal.removeEventListener('abort', onAbort)
      }
    },
  }
}
