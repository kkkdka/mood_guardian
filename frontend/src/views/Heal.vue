<script setup>
import { ref, computed, watch } from 'vue'
import { getRecommend, acceptRecommendation } from '../api/recommend'
import { ElMessage } from 'element-plus'
import HealHistory from './HealHistory.vue'


const activeTab = ref('heal')

const loading = ref(false) 
const result = ref(null)   
const error = ref(false)   
const accepting = ref(false) 
const accepted = ref(false)  
const acceptDialogVisible = ref(false) 
const adjustedStartTime = ref(null) 
const adjustedEndTime = ref(null) 


const hasSuggestedTime = computed(() => (
  Boolean(result.value?.suggested_start_time && result.value?.suggested_end_time)
))


function toPickerDateTime(value) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

watch(acceptDialogVisible, (visible) => {
  if (visible) {
    adjustedStartTime.value = toPickerDateTime(result.value?.suggested_start_time)
    adjustedEndTime.value = toPickerDateTime(result.value?.suggested_end_time)
  }
})


const typeMap = {
  movie: { label: '电影', icon: '🎬', type: 'primary' },
  book: { label: '读书', icon: '📚', type: 'success' },
  exercise: { label: '运动', icon: '🏃', type: 'warning' },
  relax: { label: '放松', icon: '🧘', type: 'info' },
}


const typeInfo = computed(() => {
  const t = result.value?.activity_type
  return typeMap[t] || { label: t || '建议', icon: '💡', type: 'info' }
})

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


async function heal() {
  loading.value = true
  error.value = false
  try {
    
    result.value = await getRecommend(result.value?.suggestion || '')
    accepted.value = false 
  } catch (err) {
    result.value = null
    error.value = true
  } finally {
    loading.value = false
  }
}


function openAcceptDialog() {
  if (!result.value || accepted.value || accepting.value) return
  acceptDialogVisible.value = true
}


async function accept() {
  if (!result.value || accepted.value || accepting.value) return
  accepting.value = true
  try {
    const payload = {}
    if (hasSuggestedTime.value) {
      payload.scheduled_start_time = adjustedStartTime.value?.replace(' ', 'T') || null
      payload.scheduled_end_time = adjustedEndTime.value?.replace(' ', 'T') || null
    }
    const response = await acceptRecommendation(result.value.id, payload)
    accepted.value = true
    acceptDialogVisible.value = false
    ElMessage.success(
      response.schedule_created ? '已加入日程，记得按时完成哦～' : '已记录，记得完成哦～',
    )
  } catch (err) {
    ElMessage.error('操作失败，请稍后再试')
  } finally {
    accepting.value = false
  }
}
</script>

<template>
  <div class="heal-page">
    <el-tabs v-model="activeTab" class="heal-tabs">
      
      <el-tab-pane label="获取建议" name="heal">
        <div class="heal-content">
          <div class="hero">
            <div class="activity-icons">
              <span
                v-for="item in Object.values(typeMap)"
                :key="item.label"
                class="activity-icon"
              >{{ item.icon }}</span>
            </div>
            <h2>治愈助手</h2>
            <p>心情不太好的时候，让我来陪陪你</p>
          </div>

          
          <div class="action">
            <el-button
              type="primary"
              size="large"
              round
              class="heal-button"
              :class="{ 'breathe-glow': !loading }"
              :loading="loading"
              @click="heal"
            >
              {{ loading ? '正在为你准备…' : '帮我治愈一下' }}
            </el-button>
            <el-button
              v-if="result"
              size="large"
              round
              :disabled="loading"
              @click="heal"
            >
              换一个
            </el-button>
          </div>

          
          <el-alert
            v-if="error"
            class="error-box"
            title="AI 暂时离线，请稍后再试"
            type="warning"
            :closable="false"
            show-icon
          />

          
          <el-card v-if="result" class="result-card" shadow="hover">
            <div class="result-header">
              <el-tag :type="typeInfo.type" effect="dark" size="large">{{ typeInfo.icon }} {{ typeInfo.label }}</el-tag>
              <span class="duration">建议时长：{{ result.duration_minutes }} 分钟</span>
            </div>
            <p class="suggestion">{{ result.suggestion }}</p>
            <p
              v-if="result.suggested_start_time && result.suggested_end_time"
              class="time-slot"
            >
              建议时间：{{ formatDateTime(result.suggested_start_time) }} 至 {{ formatDateTime(result.suggested_end_time) }}
            </p>
            <div class="result-footer">
              <el-button
                type="primary"
                size="small"
                round
                :loading="accepting"
                :disabled="accepted"
                @click="openAcceptDialog"
              >
                {{ accepted ? '已采纳' : '就它了' }}
              </el-button>
            </div>
          </el-card>

          
          <el-dialog
            v-model="acceptDialogVisible"
            title="加入日程"
            width="min(92vw, 520px)"
            destroy-on-close
          >
            <div class="accept-dialog-content">
              <p class="dialog-suggestion">{{ result?.suggestion }}</p>
              <template v-if="hasSuggestedTime">
                <el-form label-position="top">
                  <el-form-item label="开始时间">
                    <el-date-picker
                      v-model="adjustedStartTime"
                      type="datetime"
                      format="YYYY-MM-DD HH:mm"
                      value-format="YYYY-MM-DD HH:mm"
                      placeholder="选择开始时间"
                      style="width: 100%"
                    />
                  </el-form-item>
                  <el-form-item label="结束时间">
                    <el-date-picker
                      v-model="adjustedEndTime"
                      type="datetime"
                      format="YYYY-MM-DD HH:mm"
                      value-format="YYYY-MM-DD HH:mm"
                      placeholder="选择结束时间"
                      style="width: 100%"
                    />
                  </el-form-item>
                </el-form>
              </template>
              <p v-else class="no-schedule-hint">该建议无需安排具体时间</p>
            </div>
            <template #footer>
              <el-button @click="acceptDialogVisible = false">取消</el-button>
              <el-button type="primary" :loading="accepting" @click="accept">
                确认加入日程
              </el-button>
            </template>
          </el-dialog>
        </div>
      </el-tab-pane>

      
      <el-tab-pane label="治愈历史" name="history" lazy>
        <HealHistory />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.heal-page {
  max-width: 1080px;
  margin: 0 auto;
  padding: 20px 16px 32px;
}

.heal-tabs {
  width: 100%;
}
.heal-tabs :deep(.el-tabs__header) {
  height: 48px;
  margin: 0 0 38px;
}
.heal-tabs :deep(.el-tabs__nav) {
  display: flex;
  gap: 4px;
}
.heal-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background-color: var(--app-border);
}
.heal-tabs :deep(.el-tabs__item) {
  box-sizing: border-box;
  height: 48px;
  padding: 0 22px;
  color: var(--app-text-light);
  font-size: 20px;
  font-weight: 400;
  line-height: 28px;
}
.heal-tabs :deep(.el-tabs__item.is-active) {
  font-weight: 600;
}
.heal-tabs :deep(.el-tabs__item.is-active),
.heal-tabs :deep(.el-tabs__item:hover) {
  color: var(--app-text);
}
.heal-tabs :deep(.el-tabs__active-bar) {
  height: 2px;
  background-color: var(--app-primary);
}

.heal-content {
  max-width: 560px;
  min-height: 520px;
  margin: 0 auto;
  padding-top: 72px;
  text-align: center;
}

.activity-icons {
  display: flex;
  justify-content: center;
  gap: 18px;
  margin-bottom: 20px;
}
.activity-icon {
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  border: 1px solid var(--app-border);
  border-radius: 50%;
  background: var(--app-card-bg);
  font-size: 25px;
}
.time-slot {
  color: var(--app-primary-dark);
  font-size: 13px;
}
.hero h2 {
  margin: 0 0 8px;
  font-size: 28px;
  color: var(--app-text);
}
.hero p {
  margin: 0;
  color: var(--app-text-light);
}
.action {
  margin: 32px 0 28px;
  display: flex;
  gap: 12px;
  justify-content: center;
}
.action :deep(.el-button--primary) {
  min-width: 176px;
  box-shadow: 0 8px 24px color-mix(in srgb, var(--app-primary) 28%, transparent);
}
.error-box {
  max-width: 420px;
  margin: 0 auto;
}
.result-card {
  border: 1px solid transparent;
  background: linear-gradient(var(--app-card-bg), var(--app-card-bg)) padding-box, linear-gradient(135deg, var(--app-primary-light), var(--app-success)) border-box;
}
.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.duration {
  color: var(--app-text-light);
  font-size: 14px;
}
.suggestion {
  margin: 0;
  font-size: 16px;
  line-height: 1.8;
  color: var(--app-text);
}
.result-footer {
  margin-top: 20px;
  text-align: right;
}
.accept-dialog-content {
  color: var(--app-text);
}
.dialog-suggestion {
  margin: 0 0 20px;
  line-height: 1.8;
  white-space: pre-wrap;
}
.no-schedule-hint {
  margin: 8px 0;
  color: var(--app-text-light);
}
@media (max-width: 600px) {
  .heal-page { padding: 20px 16px 32px; }
  .heal-content { min-height: 0; padding-top: 52px; }
  .result-header { align-items: flex-start; flex-direction: column; }
}
</style>
