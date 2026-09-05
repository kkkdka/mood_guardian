<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getDailyAvg } from '../api/stats'
import { getRecommend } from '../api/recommend'


const visible = ref(false)

const loading = ref(false)

const result = ref(null)

const STORAGE_KEY = 'auto_heal_last_shown'


const typeMap = {
  movie: { label: '电影', type: 'primary' },
  book: { label: '读书', type: 'success' },
  exercise: { label: '运动', type: 'warning' },
  relax: { label: '放松', type: 'info' },
}
const typeInfo = computed(() => {
  const t = result.value?.activity_type
  return typeMap[t] || { label: t || '建议', type: 'info' }
})


function formatDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}


async function viewSuggestion() {
  loading.value = true
  try {
    result.value = await getRecommend(result.value?.suggestion || '')
  } catch (err) {
    ElMessage.error('AI 暂时离线，请稍后再试')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const today = formatDate(new Date())
  
  if (localStorage.getItem(STORAGE_KEY) === today) return

  try {
    
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - 2)

    const data = await getDailyAvg({
      start_date: formatDate(start),
      end_date: today,
    })

    const scores = (data.avg_scores || []).filter((n) => typeof n === 'number')
    if (scores.length === 0) return 

    
    const avg = scores.reduce((a, b) => a + b, 0) / scores.length
    if (avg < 5) {
      localStorage.setItem(STORAGE_KEY, today) 
      visible.value = true
    }
  } catch (err) {
    
  }
})
</script>

<template>
  <el-dialog v-model="visible" title="小提醒" width="420px">
    <p class="popup-msg">最近心情有些低落，要不要休息一下？</p>

    
    <template v-if="result">
      <el-divider />
      <div class="popup-head">
        <el-tag :type="typeInfo.type" effect="dark">{{ typeInfo.label }}</el-tag>
        <span class="popup-duration">建议时长：{{ result.duration_minutes }} 分钟</span>
      </div>
      <p class="popup-suggestion">{{ result.suggestion }}</p>
    </template>

    <template #footer>
      <el-button @click="visible = false">下次再说</el-button>
      <el-button v-if="!result" type="primary" :loading="loading" @click="viewSuggestion">查看治愈建议</el-button>
      <el-button v-else type="primary" @click="visible = false">知道了</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.popup-msg {
  margin: 0;
  font-size: 16px;
  color: #303133;
}
.popup-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.popup-duration {
  color: #909399;
  font-size: 13px;
}
.popup-suggestion {
  margin: 0;
  font-size: 15px;
  line-height: 1.8;
  color: #303133;
  white-space: pre-wrap;
}
</style>