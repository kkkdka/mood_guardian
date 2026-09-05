<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMe } from '../api/auth'
import { savePreferences, loadPreferences } from '../api/preferences'
import { useTheme } from '../composables/useTheme'

const router = useRouter()
const { currentTheme, setTheme } = useTheme()


const themes = [
  { name: 'dreamy-blue', label: '梦幻蓝', color: '#99A4BC' },
  { name: 'grey-pink', label: '灰粉', color: '#D4A5A5' },
  { name: 'sage-green', label: '鼠尾草绿', color: '#A8B9A3' },
  { name: 'grey-purple', label: '灰紫', color: '#B5A8C0' },
  { name: 'warm-apricot', label: '暖杏', color: '#D4B896' },
]


const userInfo = reactive({
  id: null,
  username: '',
})


const MOVIE_OPTIONS = ['科幻', '悬疑', '喜剧', '爱情', '动作', '动画', '纪录片', '恐怖']
const BOOK_OPTIONS = ['科幻', '悬疑', '文学', '历史', '心理', '传记', '诗歌', '艺术', '自然科学']


const EXERCISE_CASCADER = [
  { value: '球类运动', label: '球类运动', children: [
    { value: '乒乓球', label: '乒乓球' }, { value: '羽毛球', label: '羽毛球' },
    { value: '篮球', label: '篮球' }, { value: '足球', label: '足球' },
    { value: '网球', label: '网球' }, { value: '排球', label: '排球' },
  ]},
  { value: '有氧运动', label: '有氧运动', children: [
    { value: '跑步', label: '跑步' }, { value: '游泳', label: '游泳' },
    { value: '骑行', label: '骑行' }, { value: '跳绳', label: '跳绳' },
    { value: '有氧操', label: '有氧操' },
  ]},
  { value: '力量训练', label: '力量训练', children: [
    { value: '举重', label: '举重' }, { value: '俯卧撑', label: '俯卧撑' },
    { value: '深蹲', label: '深蹲' }, { value: '引体向上', label: '引体向上' },
  ]},
  { value: '柔韧与平衡', label: '柔韧与平衡', children: [
    { value: '瑜伽', label: '瑜伽' }, { value: '普拉提', label: '普拉提' },
    { value: '太极', label: '太极' },
  ]},
  { value: '其他', label: '其他', children: [
    { value: '徒步', label: '徒步' }, { value: '舞蹈', label: '舞蹈' },
    { value: '武术', label: '武术' },
  ]},
]


const prefForm = reactive({
  movie_genre: [],
  book_genre: [],
  exercise_type: [], 
})

const loading = ref(false)   
const submitting = ref(false) 


function splitToArray(str) {
  if (!str) return []
  return str
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
}


function parseExerciseType(raw) {
  if (!raw) return []
  try {
    return JSON.parse(raw)
  } catch {
    return [] 
  }
}


onMounted(async () => {
  loading.value = true
  try {
    
    const user = await getMe()
    userInfo.id = user.id
    userInfo.username = user.username

    
    const saved = await loadPreferences()
    if (saved) {
      prefForm.movie_genre = splitToArray(saved.movie_genre)
      prefForm.book_genre = splitToArray(saved.book_genre)
      prefForm.exercise_type = parseExerciseType(saved.exercise_type)
    }
  } catch (err) {
    ElMessage.error('加载用户信息失败')
  } finally {
    loading.value = false
  }
})


async function handleSavePrefs() {
  submitting.value = true
  try {
    await savePreferences({
      movie_genre: prefForm.movie_genre.join(','),
      book_genre: prefForm.book_genre.join(','),
      exercise_type: JSON.stringify(prefForm.exercise_type),
    })
    ElMessage.success('偏好已保存')
  } catch (err) {
    const msg = err.response?.data?.detail || err.message || '保存失败'
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}


function handleLogout() {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    ElMessage.success('已退出登录')
    router.push('/login')
  }).catch(() => {})
}
</script>

<template>
  <div class="settings-page" v-loading="loading">
    
    <el-card class="section-card">
      <template #header>
        <span>基本信息</span>
      </template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户 ID">{{ userInfo.id }}</el-descriptions-item>
        <el-descriptions-item label="用户名">{{ userInfo.username }}</el-descriptions-item>
      </el-descriptions>
      <div style="margin-top: 16px; text-align: right">
        <el-button type="danger" plain @click="handleLogout">退出登录</el-button>
      </div>
    </el-card>

    
    <el-card class="section-card theme-card">
      <template #header>
        <span>主题色</span>
      </template>
      <div class="theme-options">
        <button
          v-for="theme in themes"
          :key="theme.name"
          type="button"
          class="theme-option"
          :class="{ selected: currentTheme === theme.name }"
          :style="{ '--theme-color': theme.color }"
          :aria-label="`切换到${theme.label}主题`"
          @click="setTheme(theme.name)"
        >
          <span class="theme-swatch">{{ currentTheme === theme.name ? '✓' : '' }}</span>
          <span>{{ theme.label }}</span>
        </button>
      </div>
    </el-card>

    
    <el-card class="section-card">
      <template #header>
        <span>偏好设置</span>
      </template>
      <p class="tip">这些偏好会用于「治愈助手」为你推荐更合适的内容。</p>

      <el-form label-width="140px" @submit.prevent>
        <el-form-item label="喜欢的电影类型">
          <el-select
            v-model="prefForm.movie_genre"
            multiple
            clearable
            placeholder="请选择电影类型"
            style="width: 100%"
          >
            <el-option v-for="o in MOVIE_OPTIONS" :key="o" :label="o" :value="o" />
          </el-select>
        </el-form-item>

        <el-form-item label="喜欢的书籍类型">
          <el-select
            v-model="prefForm.book_genre"
            multiple
            clearable
            placeholder="请选择书籍类型"
            style="width: 100%"
          >
            <el-option v-for="o in BOOK_OPTIONS" :key="o" :label="o" :value="o" />
          </el-select>
        </el-form-item>

        <el-form-item label="喜欢的运动方式">
          <el-cascader
            v-model="prefForm.exercise_type"
            :options="EXERCISE_CASCADER"
            :props="{ multiple: true }"
            clearable
            placeholder="请选择运动方式"
            style="width: 100%"
            collapse-tags
            collapse-tags-tooltip
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSavePrefs">
            保存偏好
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.settings-page {
  max-width: 860px;
  margin: 0 auto;
  padding: 40px 32px 64px;
}
.section-card {
  margin-bottom: 24px;
  border: 1px solid var(--app-border);
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(74, 82, 72, .04);
}
.section-card :deep(.el-card__header) {
  padding: 20px 24px;
  border-bottom-color: var(--app-border);
  color: var(--app-text);
  font-size: 16px;
  font-weight: 600;
}
.section-card :deep(.el-card__body) {
  padding: 24px;
}
.tip {
  margin: 0 0 22px;
  color: var(--app-text-light);
  font-size: 13px;
  line-height: 21px;
}
.section-card :deep(.el-descriptions__label) {
  width: 120px;
  color: var(--app-text-light);
  background: color-mix(in srgb, var(--app-primary) 7%, var(--app-card-bg));
}
.section-card :deep(.el-descriptions__content) {
  color: var(--app-text);
}
.section-card :deep(.el-descriptions__cell) {
  border-color: var(--app-border);
}
.theme-options {
  display: grid;
  grid-template-columns: repeat(5, minmax(80px, 1fr));
  gap: 14px;
}
.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 12px 8px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  color: var(--app-text-light);
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  transition: background .2s ease, border-color .2s ease, color .2s ease;
}
.theme-option:hover,
.theme-option.selected {
  border-color: var(--app-primary-light);
  background: color-mix(in srgb, var(--app-primary) 8%, var(--app-card-bg));
  color: var(--app-text);
}
.theme-swatch {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--theme-color);
  color: var(--app-card-bg);
  font-size: 20px;
  font-weight: 700;
  box-shadow: 0 3px 10px color-mix(in srgb, var(--theme-color) 28%, transparent);
  transition: box-shadow .2s ease, transform .2s ease;
}
.theme-option:hover .theme-swatch { transform: translateY(-2px); }
.theme-option.selected .theme-swatch {
  box-shadow: 0 0 0 3px var(--app-card-bg), 0 0 0 5px var(--app-primary), 0 5px 14px color-mix(in srgb, var(--theme-color) 32%, transparent);
}
.section-card :deep(.el-form-item) { margin-bottom: 22px; }
.section-card :deep(.el-form-item__label) { color: var(--app-text); font-size: 14px; }
.section-card :deep(.el-input__wrapper),
.section-card :deep(.el-select__wrapper),
.section-card :deep(.el-cascader .el-input__wrapper) {
  min-height: 40px;
  box-shadow: 0 0 0 1px var(--app-border) inset;
}
.section-card :deep(.el-input__wrapper:hover),
.section-card :deep(.el-select__wrapper:hover) { box-shadow: 0 0 0 1px var(--app-primary-light) inset; }
.section-card :deep(.el-input__wrapper.is-focus),
.section-card :deep(.el-select__wrapper.is-focused) { box-shadow: 0 0 0 1px var(--app-primary) inset; }
.section-card :deep(.el-button) { border-radius: 10px; }
@media (max-width: 680px) {
  .settings-page { padding: 28px 16px 48px; }
  .section-card :deep(.el-card__header), .section-card :deep(.el-card__body) { padding: 18px; }
  .theme-options { grid-template-columns: repeat(3, 1fr); }
  .section-card :deep(.el-form-item) { display: block; }
  .section-card :deep(.el-form-item__label) { display: block; width: auto !important; margin-bottom: 8px; text-align: left; }
}
</style>