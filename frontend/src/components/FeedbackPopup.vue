<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getPendingFeedback,
  submitRecommendationFeedback,
} from '../api/recommend'

const route = useRoute()
const visible = ref(false)
const loading = ref(false)
const submitting = ref(false)
const pendingItems = ref([])
const rating = ref(0)
const feedbackText = ref('')
const loadedToken = ref('')

const currentItem = computed(() => pendingItems.value[0] || null)


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

function resetForm() {
  rating.value = 0
  feedbackText.value = ''
}


async function loadPendingFeedback() {
  const token = localStorage.getItem('token')
  if (!token || loading.value) return
  loading.value = true
  try {
    const data = await getPendingFeedback()
    pendingItems.value = Array.isArray(data) ? data : []
    if (pendingItems.value.length > 0) {
      resetForm()
      visible.value = true
    }
    loadedToken.value = token
  } catch (_error) {
    
  } finally {
    loading.value = false
  }
}


async function submitFeedback() {
  if (!currentItem.value || !Number.isInteger(rating.value) || rating.value < 1) {
    ElMessage.warning('请先选择 1-10 分')
    return
  }

  submitting.value = true
  try {
    await submitRecommendationFeedback(currentItem.value.id, {
      rating: rating.value,
      feedback_text: feedbackText.value.trim() || null,
    })
    ElMessage.success('反馈已提交，谢谢你的分享')
    pendingItems.value.shift()
    if (pendingItems.value.length > 0) {
      resetForm()
    } else {
      visible.value = false
    }
    await loadPendingFeedback()
  } catch (_error) {
    ElMessage.error('提交反馈失败，请稍后再试')
  } finally {
    submitting.value = false
  }
}


function postpone() {
  visible.value = false
}


watch(
  () => route.path,
  () => {
    const token = localStorage.getItem('token')
    if (token && token !== loadedToken.value) loadPendingFeedback()
  },
  { immediate: true },
)
</script>

<template>
  <el-dialog v-model="visible" title="完成后的感受如何？" width="460px" :close-on-click-modal="false">
    <template v-if="currentItem">
      <el-tag type="success" effect="plain">治愈建议</el-tag>
      <p class="suggestion">{{ currentItem.recommendation_text }}</p>
      <p v-if="currentItem.scheduled_start_time && currentItem.scheduled_end_time" class="time">
        建议时间：{{ formatDateTime(currentItem.scheduled_start_time) }} 至 {{ formatDateTime(currentItem.scheduled_end_time) }}
      </p>

      <el-form label-position="top">
        <el-form-item label="本次体验评分">
          <el-rate v-model="rating" :max="10" show-score score-template="{value} 分" />
        </el-form-item>
        <el-form-item label="感想（可选）">
          <el-input
            v-model="feedbackText"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
            placeholder="说说这次建议对你的帮助吧"
          />
        </el-form-item>
      </el-form>
    </template>

    <template #footer>
      <el-button @click="postpone">稍后再说</el-button>
      <el-button type="primary" :loading="submitting" @click="submitFeedback">提交反馈</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.suggestion {
  margin: 16px 0 10px;
  color: #303133;
  line-height: 1.8;
  white-space: pre-wrap;
}
.time {
  margin: 0 0 18px;
  color: #909399;
  font-size: 14px;
}
</style>
