<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getReportSummary } from '../api/report'

const period = ref('week')
const selectedDate = ref(new Date())
const currentPeriod = ref(null)
const loading = ref(false)

function formatDate(date) {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

function parseDate(value) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function getMonday(date) {
  const result = new Date(date)
  const day = result.getDay()
  result.setDate(result.getDate() - (day === 0 ? 6 : day - 1))
  return result
}

function movePeriod(offset) {
  const next = new Date(selectedDate.value)
  if (period.value === 'week') next.setDate(next.getDate() + offset * 7)
  else next.setMonth(next.getMonth() + offset)
  selectedDate.value = next
  loadReport()
}

function goCurrentPeriod() {
  selectedDate.value = new Date()
  loadReport()
}

function displayRange(report) {
  if (!report) return ''
  if (period.value === 'week') {
    return `${mmdd(report.start_date)} 至 ${mmdd(report.end_date)}`
  }
  const date = parseDate(report.start_date)
  return `${date.getFullYear()}年${date.getMonth() + 1}月`
}

function mmdd(value) {
  return value ? value.slice(5) : ''
}

const rangeText = computed(() => displayRange(currentPeriod.value))

async function loadReport() {
  loading.value = true
  try {
    const date = period.value === 'week'
      ? formatDate(getMonday(selectedDate.value))
      : formatDate(selectedDate.value)
    currentPeriod.value = await getReportSummary(period.value, date)
  } catch (error) {
    ElMessage.error(`加载心情报告失败：${error.message || error}`)
  } finally {
    loading.value = false
  }
}

function changePeriod(value) {
  period.value = value
  loadReport()
}

function dayText(day) {
  return day ? `${mmdd(day.date)} · ${day.avg_score} 分` : '暂无数据'
}

function tagType(category) {
  return category === 'emotion' ? 'warning' : 'info'
}

onMounted(loadReport)
</script>

<template>
  <div class="report-page">
    <div class="report-header">
      <div>
        <h2>心情报告</h2>
        <p class="range-text">{{ rangeText }}</p>
      </div>
    </div>

    <div class="period-toolbar">
      <div class="period-nav">
        <el-button class="period-arrow" circle @click="movePeriod(-1)">‹</el-button>
        <el-button type="primary" plain class="current-period" @click="goCurrentPeriod">
          {{ period === 'week' ? '本周' : '本月' }}
        </el-button>
        <el-button class="period-arrow" circle @click="movePeriod(1)">›</el-button>
      </div>
      <el-radio-group :model-value="period" class="period-switch" @update:model-value="changePeriod">
        <el-radio-button value="week">周报</el-radio-button>
        <el-radio-button value="month">月报</el-radio-button>
      </el-radio-group>
    </div>

    <div v-loading="loading">
      <el-empty
        v-if="!loading && currentPeriod && currentPeriod.avg_mood === null"
        description="该周期暂无记录"
      />

      <template v-if="currentPeriod && currentPeriod.avg_mood !== null">
        <el-row :gutter="16" class="report-grid">
          <el-col :xs="24" :sm="12" :md="12">
            <el-card class="metric-card">
              <div class="metric-label">平均心情</div>
              <div class="metric-value">{{ currentPeriod.avg_mood }}</div>
              <div class="mood-stars" aria-label="平均心情星级">
                <span v-for="star in 5" :key="star" :class="{ active: star <= Math.round(currentPeriod.avg_mood / 2) }">★</span>
              </div>
              <div class="metric-note">共记录 {{ currentPeriod.log_count }} 条</div>
            </el-card>
          </el-col>
          <el-col :xs="24" :sm="12" :md="12">
            <el-card class="metric-card">
              <div class="metric-label">最好的一天</div>
              <div class="day-value">{{ dayText(currentPeriod.highest_day) }}</div>
            </el-card>
          </el-col>
          <el-col :xs="24" :sm="12" :md="12">
            <el-card class="metric-card">
              <div class="metric-label">最低落的一天</div>
              <div class="day-value">{{ dayText(currentPeriod.lowest_day) }}</div>
            </el-card>
          </el-col>
          <el-col :xs="24" :sm="12" :md="12">
            <el-card class="metric-card">
              <div class="metric-label">日程完成率</div>
              <div class="metric-value">
                {{ currentPeriod.schedule.completion_rate === null ? '—' : `${currentPeriod.schedule.completion_rate}%` }}
              </div>
              <div class="metric-note">
                完成 {{ currentPeriod.schedule.completed_count }}/{{ currentPeriod.schedule.total_count }} 项
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-card class="section-card">
          <template #header>主要情绪/事件标签</template>
          <div v-if="currentPeriod.top_tags.length" class="tag-list">
            <el-tag
              v-for="tag in currentPeriod.top_tags"
              :key="`${tag.category}-${tag.name}`"
              :type="tagType(tag.category)"
              effect="light"
            >
              {{ tag.name }} × {{ tag.count }}
            </el-tag>
          </div>
          <el-empty v-else description="暂无标签记录" :image-size="80" />
        </el-card>
      </template>
    </div>
  </div>
</template>

<style scoped>
.report-page { max-width: 1080px; margin: 0 auto; padding: 40px 24px 64px; }
.report-header { margin-bottom: 18px; }
.report-header h2 { margin: 0; color: var(--app-text); font-size: 28px; }
.range-text { margin: 8px 0 0; color: var(--app-text-light); font-size: 13px; }
.period-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin: 0 0 28px; padding: 12px 16px; background: var(--app-card-bg); border: 1px solid var(--app-border); border-radius: 16px; }
.period-nav { display: flex; align-items: center; gap: 10px; }
.period-arrow { width: 34px; height: 34px; padding: 0; color: var(--app-text); border-color: var(--app-border); font-size: 24px; line-height: 1; }
.current-period { min-width: 76px; border-radius: 10px; }
.period-switch { flex-shrink: 0; }
.report-grid { margin-bottom: 8px; }
.metric-card, .section-card { margin-bottom: 16px; border: 1px solid var(--app-border); border-radius: 16px; }
.metric-card { min-height: 182px; }
.metric-label, .metric-note { color: var(--app-text-light); font-size: 13px; }
.metric-value { margin: 14px 0 4px; color: var(--app-primary-dark); font-size: 34px; font-weight: 700; }
.mood-stars { display: flex; gap: 3px; margin: 2px 0 8px; color: var(--app-border); font-size: 17px; }
.mood-stars .active { color: #f5b544; }
.day-value { margin-top: 18px; color: var(--app-text); font-size: 18px; font-weight: 600; line-height: 1.5; }
.section-card { width: 100%; }
.section-card :deep(.el-card__header) { color: var(--app-text); font-size: 16px; font-weight: 600; border-color: var(--app-border); }
.tag-list { display: flex; flex-wrap: wrap; gap: 10px; }
@media (max-width: 600px) {
  .report-page { padding: 28px 16px 48px; }
  .report-header h2 { font-size: 24px; }
  .period-toolbar { align-items: stretch; flex-direction: column; gap: 12px; }
  .period-nav { justify-content: center; }
  .period-switch { align-self: center; }
}
</style>
