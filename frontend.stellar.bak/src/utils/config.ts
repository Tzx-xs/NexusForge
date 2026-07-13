export async function fetchApiConfig(): Promise<string | null> {
  const viteKey = import.meta.env.VITE_API_KEY
  if (viteKey) {
    sessionStorage.setItem('xy-api-key', viteKey)
    return viteKey
  }
  return null
}
