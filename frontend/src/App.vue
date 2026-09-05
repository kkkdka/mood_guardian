<script setup>
import { useTheme } from './composables/useTheme'
import FeedbackPopup from './components/FeedbackPopup.vue'

const { currentTheme, setTheme } = useTheme()
const themes = { 'sage-green': '#A8B5A0', 'dreamy-blue': '#99A4BC', 'grey-pink': '#D4A5A5', 'grey-purple': '#B5A8C0', 'warm-apricot': '#D4B896' }
const navItems = [
  { to: '/diary', icon: '📔', label: '心情日记' },
  { to: '/schedule', icon: '📅', label: '日程管理' },
  { to: '/heal', icon: '✨', label: '治愈助手' },
  { to: '/library', icon: '🎬', label: '片单书单' },
]
</script>

<template>
  <div class="layout">
    <header v-if="$route.path !== '/login'" class="layout-header">
      <router-link to="/diary" class="brand-link"><span class="brand-mark">🌿</span><span>心情守护</span></router-link>
      <nav class="nav-links" aria-label="主导航">
        <router-link v-for="item in navItems" :key="item.to" :to="item.to">
          <span>{{ item.icon }}</span><span>{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="header-right">
        <div class="theme-dots">
          <button v-for="(color, name) in themes" :key="name" class="theme-dot" :class="{ active: currentTheme === name }" :style="{ background: color }" :aria-label="`切换${name}主题`" @click="setTheme(name)" />
        </div>
        <router-link to="/settings" class="settings-link" aria-label="个人设置">👤</router-link>
      </div>
    </header>
    <main class="layout-main"><router-view /></main>
    <FeedbackPopup />
  </div>
</template>

<style scoped>
.layout-header { position: sticky; top: 0; z-index: 10; height: 64px; padding: 0 40px; display: flex; align-items: center; justify-content: space-between; background: var(--app-card-bg); border-bottom: 1px solid var(--app-border); }
.brand-link { display: flex; align-items: center; gap: 12px; min-width: 220px; color: var(--app-text); font-size: 18px; font-weight: 600; text-decoration: none; white-space: nowrap; }
.brand-mark { font-size: 23px; line-height: 1; }
.nav-links { display: flex; align-items: center; gap: 8px; }
.nav-links a { display: flex; align-items: center; gap: 8px; padding: 12px 18px; border-radius: 999px; color: var(--app-text); font-size: 16px; text-decoration: none; transition: .2s ease; }
.nav-links a:hover { background: var(--app-primary-light); }
.nav-links a.router-link-active { color: var(--app-card-bg); background: var(--app-primary); font-weight: 600; }
.header-right { display: flex; align-items: center; gap: 18px; min-width: 220px; justify-content: flex-end; }
.theme-dots { display: flex; gap: 8px; }
.theme-dot { width: 19px; height: 19px; padding: 0; border: 2px solid transparent; border-radius: 50%; cursor: pointer; }
.theme-dot.active { border-color: var(--app-text); box-shadow: 0 0 0 2px var(--app-card-bg); }
.settings-link { display: grid; place-items: center; width: 42px; height: 42px; border: 2px solid var(--app-border); border-radius: 50%; color: var(--app-text); text-decoration: none; background: var(--app-card-bg); font-size: 18px; }
.settings-link.router-link-active { border-color: var(--app-primary); background: var(--app-primary-light); }
.layout-main { padding: 0; }
@media (max-width: 900px) { .layout-header { padding: 0 18px; } .brand-link { min-width: auto; } .nav-links a { padding: 10px; font-size: 14px; } .nav-links a span:first-child { display: none; } .header-right { min-width: auto; } }
@media (max-width: 620px) { .brand-link span:last-child { display: none; } .theme-dots { display: none; } .nav-links { gap: 0; } .nav-links a { font-size: 12px; padding: 8px 6px; } }
</style>
