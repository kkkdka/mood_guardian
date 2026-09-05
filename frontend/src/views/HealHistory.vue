<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteRecommendation, getRecommendationHistory, submitRecommendationFeedback } from '../api/recommend'

const loading = ref(false)
const recommendations = ref([])
const feedbackVisible = ref(false)
const feedbackItem = ref(null)
const feedbackRating = ref(0)
const feedbackText = ref('')
const feedbackSaving = ref(false)

const activeType = ref('all')

const typeTabs = [
  { name: 'all', label: '全部' },
  { name: 'movie', label: '电影' },
  { name: 'book', label: '读书' },
  { name: 'exercise', label: '运动' },
  { name: 'relax', label: '放松' },
  { name: 'pending', label: '待反馈' },
]

const activityMap = Object.freeze({
  movie: { label: '电影', icon: '🎬', type: 'primary' },
  book: { label: '读书', icon: '📚', type: 'success' },
  exercise: { label: '运动', icon: '🏃', type: 'warning' },
  relax: { label: '放松', icon: '🧘', type: 'info' },
})

const statusMap = {
  pending: { label: '未采纳', type: 'info' },
  accepted: { label: '已采纳', type: 'warning' },
  completed: { label: '待反馈', type: 'danger' },
  feedback_given: { label: '已反馈', type: 'success' },
}


const filteredRecommendations = computed(() => {
  if (activeType.value === 'pending') {
    return recommendations.value.filter((item) => item.status === 'completed')
  }
  if (activeType.value === 'all') return recommendations.value
  return recommendations.value.filter((item) => item.activity_type === activeType.value)
})


function typeCount(type) {
  if (type === 'all') return recommendations.value.length
  if (type === 'pending') return recommendations.value.filter((item) => item.status === 'completed').length
  return recommendations.value.filter((item) => item.activity_type === type).length
}


function formatDateTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hours}:${minutes}`
}

function activityInfo(item) {
  return activityMap[item.activity_type] || { label: item.activity_type || '建议', icon: '💡', type: 'info' }
}

function statusInfo(item) {
  return statusMap[item.status] || { label: item.status || '未知状态', type: 'info' }
}

const typeTitleFallback = {
  movie: '电影推荐',
  book: '读书推荐',
  exercise: '运动放松',
  relax: '舒缓放松',
}

function recommendationTitle(item) {
  if (item.title) return item.title
  return typeTitleFallback[item.activity_type] || '治愈建议'
}


async function loadHistory() {
  loading.value = true
  try {
    const data = await getRecommendationHistory()
    recommendations.value = Array.isArray(data) ? data : []
  } catch (_error) {
    ElMessage.error('加载治愈建议历史失败')
  } finally {
    loading.value = false
  }
}

function openFeedback(item) {
  feedbackItem.value = item
  feedbackRating.value = item.rating || 0
  feedbackText.value = item.feedback_text || ''
  feedbackVisible.value = true
}

const feedbackReadonly = computed(() => feedbackItem.value?.status === 'feedback_given')

async function saveFeedback() {
  if (!feedbackItem.value || !feedbackRating.value) {
    ElMessage.warning('请先选择评分')
    return
  }
  feedbackSaving.value = true
  try {
    const updated = await submitRecommendationFeedback(feedbackItem.value.id, {
      rating: feedbackRating.value,
      feedback_text: feedbackText.value.trim(),
    })
    const index = recommendations.value.findIndex((item) => item.id === feedbackItem.value.id)
    if (index !== -1) recommendations.value[index] = updated
    feedbackItem.value = updated
    ElMessage.success('反馈已保存')
    feedbackVisible.value = false
  } catch (_error) {
    ElMessage.error('反馈保存失败，请稍后再试')
  } finally {
    feedbackSaving.value = false
  }
}


async function handleDelete(item) {
  try {
    await ElMessageBox.confirm(
      '确定删除这条建议吗？删除后不可恢复。',
      '删除确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch (_error) {
    return
  }

  try {
    await deleteRecommendation(item.id)
    ElMessage.success('已删除')
    await loadHistory()
  } catch (_error) {
    ElMessage.error('删除失败，请稍后再试')
  }
}

onMounted(loadHistory)
</script>

<template>
  <section class="heal-history-page">
    <div class="page-header">
      <div>
        <h2>治愈建议历史</h2>
        <p>回顾每一次为自己安排的休息与调整。</p>
      </div>
      <el-button :loading="loading" @click="loadHistory">刷新</el-button>
    </div>

    
    <div class="type-filter">
      <el-radio-group v-model="activeType">
        <el-radio-button v-for="tab in typeTabs" :key="tab.name" :value="tab.name">
          {{ tab.label }} · {{ typeCount(tab.name) }}
        </el-radio-button>
      </el-radio-group>
    </div>

    <div v-loading="loading" class="history-content">
      <el-empty
        v-if="!loading && filteredRecommendations.length === 0"
        :description="activeType === 'all' ? '暂无治愈建议记录' : activeType === 'pending' ? '暂无待反馈建议' : '该分类暂无记录'"
      />

      <div v-else class="card-list">
        <el-card
          v-for="item in filteredRecommendations"
          :key="item.id"
          shadow="hover"
          class="recommendation-card"
          :class="`type-${item.activity_type}`"
        >
          <div class="type-icon" :class="`type-icon-${item.activity_type}`" aria-hidden="true">
            {{ activityInfo(item).icon }}
          </div>
          <div class="card-body">
            <div class="card-head">
              <div class="title-line">
                <h3>{{ recommendationTitle(item) }}</h3>
                <el-tag :type="statusInfo(item).type" effect="plain">
                  {{ statusInfo(item).label }}
                </el-tag>
              </div>
              <span class="time">{{ formatDateTime(item.created_at) }}</span>
            </div>
            <div class="meta">
              <span class="meta-item">◷ {{ item.duration_minutes || 0 }} 分钟</span>
              <span v-if="item.scheduled_start_time && item.scheduled_end_time" class="meta-item">
                📍 {{ formatDateTime(item.scheduled_start_time) }}–{{ formatDateTime(item.scheduled_end_time) }}
              </span>
              <span v-else class="meta-item">📍 随时</span>
            </div>
            <div v-if="item.rating || item.feedback_text" class="feedback">
              <div v-if="item.rating" class="rating-line">
                <span>评分</span>
                <el-rate :model-value="item.rating" :max="10" disabled show-score score-template="{value} 分" />
              </div>
              <p v-if="item.feedback_text" class="feedback-text">{{ item.feedback_text }}</p>
            </div>
            <div class="card-footer">
              <el-button
                v-if="item.status === 'completed'"
                link
                type="primary"
                size="small"
                @click="openFeedback(item)"
              >填写反馈</el-button>
              <el-button
                v-else-if="item.status === 'feedback_given'"
                link
                type="primary"
                size="small"
                @click="openFeedback(item)"
              >查看评价</el-button>
              <el-button link type="danger" size="small" @click.stop="handleDelete(item)">删除</el-button>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <el-dialog
      v-model="feedbackVisible"
      :title="feedbackReadonly ? '查看我的评价' : '填写反馈'"
      width="min(480px, 92vw)"
    >
      <template v-if="feedbackItem">
        <p class="feedback-target">{{ feedbackItem.recommendation_text }}</p>
        <div class="feedback-form-item">
          <span>我的评分</span>
          <el-rate v-model="feedbackRating" :max="10" :disabled="feedbackReadonly" show-score score-template="{value} 分" />
        </div>
        <div class="feedback-form-item">
          <span>感想</span>
          <el-input v-model="feedbackText" type="textarea" :rows="4" :disabled="feedbackReadonly" placeholder="记录这次体验带给你的感受" />
        </div>
      </template>
      <template #footer>
        <el-button @click="feedbackVisible = false">关闭</el-button>
        <el-button v-if="!feedbackReadonly" type="primary" :loading="feedbackSaving" @click="saveFeedback">保存反馈</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.heal-history-page {
  max-width: 1080px;
  margin: 0 auto;
  padding: 16px 0;
}
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 22px;
}
.page-header > div {
  min-width: 0;
}
.page-header h2 {
  margin: 0;
  color: var(--app-text);
  font-size: 28px;
  line-height: 1.35;
}
.page-header p {
  margin: 10px 0 0;
  color: var(--app-text-light);
  font-size: 15px;
  line-height: 1.5;
}
.page-header > .el-button {
  flex: 0 0 auto;
  margin-left: auto;
}
.type-filter {
  margin-bottom: 20px;
  overflow-x: auto;
}
.type-filter :deep(.el-radio-group) {
  display: flex;
  gap: 10px;
  min-width: max-content;
}
.type-filter :deep(.el-radio-button__inner) {
  border: 1px solid var(--app-border);
  border-radius: 999px;
  box-shadow: none;
  color: var(--app-text-light);
  padding: 9px 18px;
}
.type-filter :deep(.el-radio-button:first-child .el-radio-button__inner),
.type-filter :deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 999px;
}
.type-filter :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  border-color: var(--app-primary);
  background: var(--app-primary);
  color: #fff;
  box-shadow: none;
}
.history-content {
  min-height: 160px;
}
.card-list {
  display: grid;
  gap: 14px;
}
.recommendation-card {
  display: flex;
  align-items: flex-start;
  border: 1px solid var(--app-border);
  border-left: 3px solid var(--app-primary-light);
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(74, 82, 72, .04);
  transition: box-shadow .2s ease, transform .2s ease;
}
.recommendation-card :deep(.el-card__body) {
  display: flex;
  align-items: flex-start;
  width: 100%;
}
.type-icon {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  flex: 0 0 52px;
  margin: 2px 16px 0 0;
  border-radius: 50%;
  background: var(--app-bg);
  font-size: 24px;
}
.card-body {
  min-width: 0;
  flex: 1;
}
.recommendation-card[role='button'] { cursor: pointer; }
.recommendation-card[role='button']:focus-visible { outline: 2px solid var(--app-primary); outline-offset: 2px; }
.recommendation-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px color-mix(in srgb, var(--app-primary) 12%, transparent);
}

.recommendation-card.type-movie {
  border-top: 3px solid var(--app-primary);
}
.recommendation-card.type-book {
  border-top: 3px solid #67c23a;
}
.recommendation-card.type-exercise {
  border-top: 3px solid var(--app-warning);
}
.recommendation-card.type-relax {
  border-top: 3px solid #909399;
}

.title-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.title-line h3 {
  margin: 0;
  color: var(--app-text);
  font-size: 18px;
  font-weight: 600;
  line-height: 1.4;
}
.card-head,
.title-line,
.rating-line {
  display: flex;
  align-items: center;
}
.card-head {
  justify-content: space-between;
  gap: 12px;
}
.time {
  color: var(--app-text-light);
  font-size: 13px;
  flex-shrink: 0;
}
.recommendation-text {
  display: none;
}
.meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 0;
  border-top: 1px solid var(--app-border);
}
.meta-item {
  color: #909399;
  font-size: 13px;
}
.feedback {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--app-border);
}
.rating-line {
    gap: 8px;
  color: var(--app-text);
  font-size: 14px;
}
.feedback-text {
  display: -webkit-box;
  margin: 8px 0 0;
  overflow: hidden;
  color: var(--app-text);
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.feedback-target { margin: 0 0 18px; padding: 12px; color: var(--app-text); background: var(--app-bg); border-radius: 8px; line-height: 1.7; }
.feedback-form-item { display: flex; flex-direction: column; gap: 8px; margin-top: 16px; color: var(--app-text); font-size: 14px; }
.feedback-form-item :deep(.el-rate) { align-self: flex-start; }

@media (max-width: 600px) {
  .heal-history-page { padding: 12px 0; }
  .recommendation-card :deep(.el-card__body) { padding: 14px; }
  .type-icon { width: 40px; height: 40px; flex-basis: 40px; margin-right: 10px; font-size: 19px; }
  .card-head { align-items: flex-start; flex-direction: column; gap: 6px; }
  .time { font-size: 12px; }
}
</style>
