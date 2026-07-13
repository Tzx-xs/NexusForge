import request from './http'

export interface ExportFormat {
  format: string
  label: string
  description: string
}

export interface ExportScope {
  scope: string
  label: string
}

export function listExportFormats(novelId: string) {
  return request.get<ExportFormat[]>(`/novels/${novelId}/export/formats`)
}

export function listExportScopes(novelId: string) {
  return request.get<ExportScope[]>(`/novels/${novelId}/export/scopes`)
}

export function exportNovel(
  novelId: string,
  data: {
    format: string
    scope: string
    include_title_page?: boolean
    include_chapter_numbers?: boolean
    include_toc?: boolean
    start_chapter?: number
    end_chapter?: number
    title?: string
    author?: string
  }
) {
  return request.post<Blob>(`/novels/${novelId}/export`, data, {
    responseType: 'blob',
  })
}

export interface ExportOptions {
  format: string
  scope: string
  include_title_page?: boolean
  include_chapter_numbers?: boolean
  include_toc?: boolean
  start_chapter?: number
  end_chapter?: number
  title?: string
  author?: string
}

export function downloadExport(novelId: string, options: ExportOptions, filename: string) {
  return request
    .post<Blob>(`/novels/${novelId}/export`, options, {
      responseType: 'blob',
    })
    .then((res) => {
      const url = window.URL.createObjectURL(new Blob([res]))
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      return res
    })
}
