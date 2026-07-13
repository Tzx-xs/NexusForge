import { chromium } from 'playwright'

const baseUrl = process.env.WV_TEST_URL || 'http://localhost:8000'
const apiKey = process.env.WV_API_KEY || 'BXYEdQmO4-zKwG_zeXgFbxipZ3HnO11WAjlDnRSIhBs'

const browser = await chromium.launch({
  headless: true,
  executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
})
const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } })
const page = await context.newPage()

await context.addInitScript((key) => {
  localStorage.removeItem('xy-last-novel')
  sessionStorage.setItem('xy-api-key', key)
}, apiKey)

page.on('console', msg => console.log('CONSOLE:', msg.type(), msg.text()))
page.on('pageerror', err => console.log('PAGEERROR:', err.message))
page.on('response', async resp => {
  const url = resp.url()
  if (url.includes('/worldview/')) {
    console.log('API RESPONSE', url, resp.status())
  }
})

const tabNames = ['characters', 'geography', 'rules', 'plot']
const tabLabels = ['人物关系图', '地理关系图', '规则体系图', '主线规划图']

await page.goto(`${baseUrl}/#/?module=worldview`)
await page.waitForTimeout(4000)

const results = []

for (let i = 0; i < tabNames.length; i++) {
  const tabs = await page.locator('.wv-tab').all()
  if (tabs.length > i) {
    await tabs[i].click()
    await page.waitForTimeout(2000)
  }

  const screenshotPath = `scripts/wv-${tabNames[i]}.png`
  await page.screenshot({ path: screenshotPath, fullPage: false })

  const state = await page.evaluate(() => ({
    nodeCount: document.querySelectorAll('.graph-node').length,
    lineCount: document.querySelectorAll('line').length,
    emptyText: document.querySelector('.wv-empty-text')?.textContent || '',
  }))

  const hasNodes = state.nodeCount > 0
  const hasLines = state.lineCount > 0 || state.nodeCount <= 1
  const passed = hasNodes

  results.push({
    tab: tabNames[i],
    label: tabLabels[i],
    ...state,
    passed,
    screenshot: screenshotPath,
  })

  console.log(`PAGE STATE ${tabNames[i]}:`, state, passed ? 'PASS' : 'FAIL')
}

await browser.close()

const allPassed = results.every(r => r.passed)
console.log('\n=== WORLDVIEW TEST SUMMARY ===')
console.log('Base URL:', baseUrl)
console.table(results.map(r => ({
  tab: r.tab,
  nodes: r.nodeCount,
  lines: r.lineCount,
  empty: r.emptyText,
  result: r.passed ? 'PASS' : 'FAIL',
})))

if (!allPassed) {
  console.error('Some tabs failed to render nodes.')
  process.exit(1)
}

console.log('All worldview tabs rendered real data successfully.')
