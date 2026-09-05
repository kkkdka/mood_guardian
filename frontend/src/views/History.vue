<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteLog, getLogs, updateLog } from '../api/logs'

const router = useRouter()


const emotionOptions = ['愤怒', '尴尬', '喜悦', '平静', '焦虑', '孤独']
const eventOptions = ['熬夜', '运动', '社交', '加班', '阅读', '旅行']


const loading = ref(false)
const groups = ref([])

function formatDate(date) {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

function currentWeekRange() {
  const monday = new Date()
  const day = monday.getDay()
  monday.setDate(monday.getDate() - (day === 0 ? 6 : day - 1))
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  return [formatDate(monday), formatDate(sunday)]
}

const dateRange = ref(currentWeekRange())


const editVisible = ref(false)
const editingId = ref(null)
const editDate = ref('')
const editMood = ref(5)
const editContent = ref('')
const editEmotionTags = ref([])
const editEventTags = ref([])
const newEditEmotion = ref([])
const newEditEvent = ref([])
const saving = ref(false)


function mmdd(dateStr) {
  if (!dateStr) return ''
  const parts = dateStr.split('-')
  return parts.length >= 3 ? `${parts[1]}-${parts[2]}` : dateStr
}

function summary(content) {
  if (!content) return ''
  return content.length > 40 ? `${content.slice(0, 40)}…` : content
}

function timeOf(log) {
  if (!log.created_at) return ''
  const date = new Date(log.created_at)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}


async function loadLogs() {
  loading.value = true
  try {
    const params = {}
    if (dateRange.value?.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const data = await getLogs(params)
    groupLogs(Array.isArray(data) ? data : [])
  } catch (error) {
    ElMessage.error(`加载日志失败：${error.message || error}`)
  } finally {
    loading.value = false
  }
}


function clearDateRange() {
  dateRange.value = []
  loadLogs()
}


function groupLogs(logs) {
  const map = new Map()
  logs.forEach((log) => {
    if (!map.has(log.date)) map.set(log.date, [])
    map.get(log.date).push(log)
  })

  groups.value = [...map.entries()]
    .sort(([dateA], [dateB]) => dateB.localeCompare(dateA))
    .map(([date, items]) => {
      const sortedItems = [...items].sort((a, b) => {
        if (a.created_at && b.created_at) {
          return b.created_at.localeCompare(a.created_at)
        }
        return Number(b.id) - Number(a.id)
      })
      const scores = sortedItems
        .map((item) => Number(item.mood_score))
        .filter((score) => Number.isFinite(score))
      return {
        date,
        items: sortedItems,
        averageStars: scores.length
          ? (scores.reduce((sum, score) => sum + score, 0) / scores.length / 2).toFixed(1)
          : null,
      }
    })
}

function scoreLevel(score) {
  const stars = Math.ceil(Number(score) / 2)
  if (stars >= 4) return 'score-high'
  if (stars <= 2) return 'score-low'
  return 'score-medium'
}

function openEdit(log) {
  editingId.value = log.id
  editDate.value = log.date
  editMood.value = log.mood_score
  editContent.value = log.content || ''

  const scoreMap = {}
  ;(log.emotion_scores || []).forEach((item) => {
    scoreMap[item.emotion_name] = item.score
  })

  const emotions = []
  const events = []
  ;(log.tags || []).forEach((name) => {
    if (name in scoreMap) emotions.push({ name, score: scoreMap[name] })
    else events.push(name)
  })

  editEmotionTags.value = emotions
  editEventTags.value = events
  newEditEmotion.value = []
  newEditEvent.value = []
  editVisible.value = true
}

function removeEditEmotion(index) {
  editEmotionTags.value.splice(index, 1)
}

function removeEditEvent(index) {
  editEventTags.value.splice(index, 1)
}

function onEditEmotionSelect() {
  newEditEmotion.value.forEach((name) => {
    if (name && !editEmotionTags.value.some((item) => item.name === name)) {
      editEmotionTags.value.push({ name, score: 5 })
    }
  })
  newEditEmotion.value = []
}

function onEditEventSelect() {
  newEditEvent.value.forEach((name) => {
    if (name && !editEventTags.value.includes(name)) editEventTags.value.push(name)
  })
  newEditEvent.value = []
}

async function saveEdit() {
  if (!editContent.value.trim()) {
    ElMessage.warning('请填写日记正文')
    return
  }
  if (!editMood.value || editMood.value < 1 || editMood.value > 10) {
    ElMessage.warning('请选择 1-10 的心情分数')
    return
  }

  saving.value = true
  try {
    await updateLog(editingId.value, {
      content: editContent.value.trim(),
      mood_score: editMood.value,
      tags: [
        ...editEmotionTags.value.map((item) => item.name),
        ...editEventTags.value,
      ],
      emotion_scores: editEmotionTags.value.map((item) => ({
        emotion_name: item.name,
        score: item.score,
      })),
    })
    ElMessage.success('更新成功')
    editVisible.value = false
    await loadLogs()
  } catch (error) {
    ElMessage.error(`更新失败：${error.message || error}`)
  } finally {
    saving.value = false
  }
}

async function handleDelete(log) {
  try {
    await ElMessageBox.confirm(
      '确定删除这条日志吗？删除后不可恢复。',
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
    await deleteLog(log.id)
    ElMessage.success('删除成功')
    await loadLogs()
  } catch (error) {
    ElMessage.error(`删除失败：${error.message || error}`)
  }
}

onMounted(loadLogs)
</script>

<template>
  <div class="history-page">
    <div class="header">
      <div class="header-copy">
        <h2>历史日志</h2>
        <p>回望每一个值得被记住的日子</p>
      </div>
      <el-button :loading="loading" @click="loadLogs">刷新</el-button>
    </div>

    
    <div class="toolbar">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        value-format="YYYY-MM-DD"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        clearable
        @change="loadLogs"
        @clear="clearDateRange"
      />
      <el-button type="primary" plain @click="router.push('/stats')">
        查看心情图表
      </el-button>
    </div>

    <div v-loading="loading">
      <el-empty v-if="groups.length === 0" description="暂无日志" />

      
      <el-card
        v-for="group in groups"
        :key="group.date"
        class="date-group"
        shadow="never"
      >
        <div class="date-header">
          <strong class="date-title">{{ mmdd(group.date) }}</strong>
          <span class="average-score">
            当日平均
            <template v-if="group.averageStars !== null">
              {{ group.averageStars }} <span class="average-star" aria-hidden="true">★</span>
            </template>
            <template v-else>无评分</template>
          </span>
          <el-tag type="info" effect="plain">共 {{ group.items.length }} 条</el-tag>
        </div>

        <el-divider />

        <el-card
          v-for="log in group.items"
          :key="log.id"
          class="log-card"
          :class="scoreLevel(log.mood_score)"
          shadow="hover"
          @click="openEdit(log)"
        >
          <div class="log-head">
            <div class="log-main">
              <span class="log-time">{{ timeOf(log) }}</span>
              <div v-if="log.mood_score != null" class="history-stars" :aria-label="`${log.mood_score} 分`">
                <span v-for="star in 5" :key="star" :class="{ filled: star <= Math.ceil(log.mood_score / 2) }">★</span>
              </div>
              <div v-if="log.tags?.length" class="tags">
                <el-tag v-for="tag in log.tags" :key="tag" size="small">{{ tag }}</el-tag>
              </div>
            </div>
            <el-button class="del-btn" link type="danger" @click.stop="handleDelete(log)">删除</el-button>
          </div>
          <p class="content">{{ summary(log.content) }}</p>
        </el-card>
      </el-card>
    </div>

    
    <el-dialog
      v-model="editVisible"
      :title="`编辑日志（${mmdd(editDate)}）`"
      width="min(560px, 92vw)"
    >
      <el-form label-width="90px">
        <el-form-item label="心情">
          <el-rate
            v-model="editMood"
            :max="10"
            show-score
            score-template="{value} 分"
          />
        </el-form-item>

        <el-form-item label="内容">
          <el-input
            v-model="editContent"
            type="textarea"
            :rows="5"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="情绪标签">
          <div class="tag-list">
            <div
              v-for="(item, index) in editEmotionTags"
              :key="item.name"
              class="tag-score"
            >
              <el-input-number
                v-model="item.score"
                :min="1"
                :max="10"
                size="small"
                class="score-input"
              />
              <el-tag closable type="warning" @close="removeEditEmotion(index)">
                {{ item.name }}
              </el-tag>
            </div>
          </div>
          <el-select
            v-model="newEditEmotion"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入并回车可添加情绪标签"
            class="add-select"
            @change="onEditEmotionSelect"
          >
            <el-option
              v-for="option in emotionOptions"
              :key="option"
              :label="option"
              :value="option"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="事件标签">
          <div class="tag-list">
            <el-tag
              v-for="(name, index) in editEventTags"
              :key="name"
              closable
              type="info"
              @close="removeEditEvent(index)"
            >
              {{ name }}
            </el-tag>
          </div>
          <el-select
            v-model="newEditEvent"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入并回车可添加事件标签"
            class="add-select"
            @change="onEditEventSelect"
          >
            <el-option
              v-for="option in eventOptions"
              :key="option"
              :label="option"
              :value="option"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.history-page { max-width: 1080px; margin: 0 auto; padding: 40px 24px 64px; }
.header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 28px; }
.header-copy { min-width: 0; }
.header h2 { margin: 0; color: var(--app-text); font-size: 28px; line-height: 1.35; letter-spacing: .02em; }
.header p { margin: 6px 0 0; color: var(--app-text-light); font-size: 13px; line-height: 1.5; }
.toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 28px; padding: 16px; background: color-mix(in srgb, var(--app-card-bg) 82%, var(--app-primary-light)); border: 1px solid var(--app-border); border-radius: 16px; }
.toolbar :deep(.el-date-editor) { width: 280px; }
.date-group { margin-bottom: 20px; border: 1px solid var(--app-border); border-radius: 16px; overflow: hidden; }
.date-group :deep(.el-card__body) { padding: 22px; }
.date-header { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.date-title { color: var(--app-text); font-size: 22px; }
.average-score { color: var(--app-primary-dark); font-size: 14px; font-weight: 600; }
.average-star { color: #e2b33f; font-family: Georgia, serif; font-size: 17px; }
.date-group :deep(.el-divider--horizontal) { margin: 18px 0; border-color: var(--app-border); }
.log-card { position: relative; margin-bottom: 12px; border-color: var(--app-border); border-radius: 12px; cursor: pointer; transition: transform .2s ease, box-shadow .2s ease; }
.log-card::before { content: ''; position: absolute; inset: 0 auto 0 0; width: 4px; background: var(--app-warning); border-radius: 12px 0 0 12px; }
.log-card.score-high::before { background: var(--app-success); }
.log-card.score-low::before { background: var(--app-danger); }
.log-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px color-mix(in srgb, var(--app-primary) 18%, transparent); }
.log-card:last-child { margin-bottom: 0; }
.log-card :deep(.el-card__body) { padding: 17px 20px 17px 24px; }
.log-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.log-main { min-width: 0; display: flex; align-items: center; flex-wrap: wrap; gap: 10px 14px; }
.log-time { flex: 0 0 52px; color: var(--app-text-light); font-size: 15px; }
.history-stars { flex: 0 0 auto; display: inline-flex; align-items: center; gap: 2px; width: 112px; font-family: Georgia, serif; font-size: 22px; line-height: 1; letter-spacing: 1px; }
.history-stars span { display: inline-block; color: #b8bec7; }
.history-stars span.filled { color: #e2b33f; }
.tags { min-width: 0; display: flex; flex: 1 1 180px; flex-wrap: wrap; gap: 6px; align-items: center; }
.del-btn { flex: 0 0 auto; color: var(--app-danger); }
.content { margin: 10px 0 0; color: var(--app-text-light); font-size: 14px; line-height: 1.7; }
.tag-list, .tag-score { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.tag-list { margin-bottom: 8px; } .tag-score { gap: 6px; } .score-input { width: 90px; } .add-select { width: 100%; }
@media (max-width: 640px) { .history-page { padding: 28px 16px 48px; } .header { align-items: flex-start; } .header h2 { font-size: 24px; } .toolbar :deep(.el-date-editor), .toolbar > .el-button { width: 100%; } .log-head { align-items: flex-start; flex-wrap: wrap; } }
</style>
