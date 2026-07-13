export const BRAND = {
  productName: 'NexusForge',
  chineseName: '星枢',
  displayName: 'NexusForge · 星枢',
  tagline: '作者的领航员',
  descriptor: 'AI 长篇小说创作平台',
  team: 'NexusForge（星枢）团队',
  credit: '由 NexusForge（星枢）团队倾力开发',
} as const

export const BRAND_COPY = {
  short: BRAND.displayName,
  compact: `${BRAND.chineseName} · ${BRAND.tagline}`,
  full: `${BRAND.displayName}｜${BRAND.credit}`,
} as const
