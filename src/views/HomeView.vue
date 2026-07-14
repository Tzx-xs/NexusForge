<template>
  <div class="home-view h-full flex flex-col items-center justify-center px-8">
    <div class="relative mb-8">
      <div class="absolute inset-0 bg-cyan-500/5 blur-3xl rounded-full" />
      <div class="relative w-24 h-24 rounded-2xl bg-gradient-to-br from-zinc-800 to-zinc-900 border border-zinc-700/50 flex items-center justify-center shadow-2xl">
        <svg class="w-12 h-12 text-cyan-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        <div class="absolute -top-2 -right-2 w-4 h-4 rounded-full bg-cyan-500/20 border border-cyan-500/30" />
      </div>
    </div>
    <h1 class="text-2xl font-bold text-zinc-200 mb-2">Nexus 本地知识库</h1>
    <p class="text-sm text-zinc-500 text-center max-w-md mb-8 leading-relaxed">
      私有化部署的 AI 知识管理平台，支持多源数据采集与智能问答。
    </p>
    <router-link
      to="/notes"
      class="px-6 py-2.5 rounded-lg text-sm font-medium bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-400 hover:to-blue-500 transition-all shadow-lg shadow-cyan-500/20"
    >
      进入笔记
    </router-link>
  </div>
</template>
