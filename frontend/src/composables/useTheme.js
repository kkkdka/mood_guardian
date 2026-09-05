import { ref, watch } from 'vue'

const savedTheme = localStorage.getItem('app_theme') || 'sage-green'
const currentTheme = ref(savedTheme)


watch(
  currentTheme,
  (theme) => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('app_theme', theme)
  },
  { immediate: true },
)

export function useTheme() {
  function setTheme(name) {
    currentTheme.value = name
  }

  return { currentTheme, setTheme }
}
