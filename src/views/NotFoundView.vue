<template>
  <div class="not-found h-full flex flex-col items-center justify-center px-8">
    <div class="text-6xl font-bold text-zinc-700 mb-4">404</div>
    <p class="text-zinc-500 mb-6">页面不存在</p>
    <router-link
      to="/"
      class="px-4 py-2 rounded-lg text-sm font-medium bg-zinc-800 text-zinc-300 hover:bg-zinc-700 hover:text-white transition-colors border border-zinc-700"
    >
      返回首页
    </router-link>
  </div>
</template>
