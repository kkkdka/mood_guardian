<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { createLog, updateLog, analyzeLog } from '../api/logs'
import { getTags } from '../api/stats'
import History from './History.vue'
import Report from './Report.vue'


const activeTab = ref('write')


const emotionOptions = ref(['愤怒', '尴尬', '喜悦', '平静', '焦虑', '孤独', '悲伤', '烦躁', '疲惫', '兴奋'])
const eventOptions = ref(['学习', '工作', '社交', '阅读', '旅行', '饮食', '娱乐', '加班', '熬夜', '运动', '睡眠', '购物', '家务', '就医', '争吵', '失眠'])


onMounted(async () => {
  try {
    const tags = await getTags()
    if (tags.emotion?.length) emotionOptions.value = tags.emotion
    if (tags.event?.length) eventOptions.value = tags.event
  } catch {
    
  }
})


const form = reactive({
  date: todayStr(),
  mood: 0,
  hoverMood: 0,
  content: '',
})


const saving = ref(false)          
const confirmVisible = ref(false)  
const logId = ref(null)            


const emotionTags = ref([]) 
const eventTags = ref([])   
const newEmotion = ref([])  
const newEvent = ref([])    



function todayStr() {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}


function disabledDate(date) {
  return date.getTime() > Date.now()
}


async function handleSubmit() {
  if (saving.value) return 

  
  if (!form.date) {
    ElMessage.warning('请选择日期')
    return
  }
  if (!form.mood || form.mood < 1 || form.mood > 10) {
    ElMessage.warning('请选择 1-10 的心情分数')
    return
  }
  if (!form.content.trim()) {
    ElMessage.warning('请填写日记正文')
    return
  }

  saving.value = true
  try {
    
    const created = await createLog({
      date: form.date,
      mood_score: form.mood,
      content: form.content.trim(),
    })
    logId.value = created.id

    
    let ai = { emotions: [], events: [] }
    try {
      ai = await analyzeLog(form.content.trim())
    } catch (e) {
      ElMessage.warning('AI 分析失败，您可以手动添加标签')
    }

    
    emotionTags.value = (ai.emotions || []).map((name) => ({ name, score: 5 }))
    eventTags.value = ai.events || []
    newEmotion.value = []
    newEvent.value = []
    confirmVisible.value = true
  } catch (err) {
    ElMessage.error('保存失败：' + (err.message || err))
  } finally {
    saving.value = false
  }
}



function removeEmotion(index) {
  emotionTags.value.splice(index, 1)
}


function removeEvent(index) {
  eventTags.value.splice(index, 1)
}


function onEmotionSelect() {
  newEmotion.value.forEach((name) => {
    if (name && !emotionTags.value.some((t) => t.name === name)) {
      emotionTags.value.push({ name, score: 5 })
    }
  })
  newEmotion.value = []
}


function onEventSelect() {
  newEvent.value.forEach((name) => {
    if (name && !eventTags.value.includes(name)) {
      eventTags.value.push(name)
    }
  })
  newEvent.value = []
}


async function confirmTags() {
  const tags = [
    ...emotionTags.value.map((t) => t.name), 
    ...eventTags.value,                      
  ]
  const emotion_scores = emotionTags.value.map((t) => ({
    emotion_name: t.name,
    score: t.score,
  }))

  saving.value = true
  try {
    await updateLog(logId.value, { tags, emotion_scores })
    ElMessage.success('日志保存成功')
    confirmVisible.value = false
    resetForm()
  } catch (err) {
    ElMessage.error('标签保存失败：' + (err.message || err))
  } finally {
    saving.value = false
  }
}


function resetForm() {
  form.content = ''
  form.mood = 0
  form.hoverMood = 0
  emotionTags.value = []
  eventTags.value = []
  logId.value = null
}
</script>

<template>
  <div class="write-page">
    <div class="mood-tabs" role="tablist">
      <button v-for="tab in [{ label: '写日记', name: 'write' }, { label: '历史日志', name: 'history' }, { label: '心情报告', name: 'report' }]" :key="tab.name" class="mood-tab" :class="{ active: activeTab === tab.name }" @click="activeTab = tab.name"><span>{{ tab.label }}</span></button>
    </div>

    <div v-if="activeTab === 'write'" class="write-form-wrap">
      <section class="diary-card date-card"><span>记录日期</span><el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" :disabled-date="disabledDate" placeholder="请选择日期" /></section>
      <section class="diary-card mood-card"><p>今天心情如何？</p><div class="star-picker"><button v-for="star in 5" :key="star" type="button" :class="{ selected: star <= (form.hoverMood || Math.ceil(form.mood / 2)) }" @mouseenter="form.hoverMood = star" @mouseleave="form.hoverMood = 0" @click="form.mood = star * 2">⭐</button></div><div v-if="form.hoverMood || form.mood" class="mood-caption">{{ form.hoverMood || Math.ceil(form.mood / 2) }} 分 · {{ ['很糟糕', '不太好', '一般般', '还不错', '超开心'][(form.hoverMood || Math.ceil(form.mood / 2)) - 1] }}</div></section>
      <section class="diary-card content-card"><label>写下你的心情…</label><el-input v-model="form.content" type="textarea" :rows="7" maxlength="500" show-word-limit placeholder="今天发生了什么？有什么感受想记录下来？" /></section>
      <el-button class="save-diary" type="primary" :loading="saving" :disabled="saving" @click="handleSubmit">保存日记</el-button>
    </div>
    <History v-else-if="activeTab === 'history'" />
    <Report v-else />

    <el-dialog v-model="confirmVisible" title="确认标签" width="560px">
      <p class="tip">AI 识别出以下标签，如不准确可进行修正</p>
      <div class="section"><h4>情绪标签（可打 1-10 分）</h4><div class="tag-list"><div v-for="(item, index) in emotionTags" :key="item.name" class="tag-score"><el-input-number v-model="item.score" :min="1" :max="10" size="small" class="score-input" /><el-tag closable type="warning" @close="removeEmotion(index)">{{ item.name }}</el-tag></div><span v-if="emotionTags.length === 0" class="empty">暂无情绪标签</span></div><el-select v-model="newEmotion" multiple filterable allow-create default-first-option placeholder="输入并回车可添加自定义情绪标签" class="add-select" @change="onEmotionSelect"><el-option v-for="o in emotionOptions" :key="o" :label="o" :value="o" /></el-select></div>
      <div class="section"><h4>事件标签</h4><div class="tag-list"><el-tag v-for="(name, index) in eventTags" :key="name" closable type="info" @close="removeEvent(index)">{{ name }}</el-tag><span v-if="eventTags.length === 0" class="empty">暂无事件标签</span></div><el-select v-model="newEvent" multiple filterable allow-create default-first-option placeholder="输入并回车可添加自定义事件标签" class="add-select" @change="onEventSelect"><el-option v-for="o in eventOptions" :key="o" :label="o" :value="o" /></el-select></div>
      <template #footer><el-button @click="confirmVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="confirmTags">确认保存</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.write-page { max-width: 1080px; margin: 0 auto; padding: 42px 24px 56px; }
.mood-tabs { display: flex; gap: 26px; border-bottom: 1px solid var(--app-border); margin-bottom: 38px; }
.mood-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  height: 48px;
  padding: 0;
  border: 0;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  background: transparent;
  color: var(--app-text-light);
  font-size: 20px;
  font-weight: 400;
  line-height: 28px;
  cursor: pointer;
}
.mood-tab span { padding: 0 4px; }
.mood-tab.active { color: var(--app-text); border-bottom-color: var(--app-primary); font-weight: 600; }
.write-form-wrap { max-width: 680px; margin: 0 auto; display: flex; flex-direction: column; gap: 28px; }
.diary-card { background: var(--app-card-bg); border: 1px solid var(--app-border); border-radius: 16px; box-shadow: var(--app-shadow); }
.date-card { min-height: 88px; padding: 22px 26px; display: flex; align-items: center; justify-content: space-between; color: var(--app-text-light); font-size: 14px; }
.date-card :deep(.el-input__wrapper) { background: var(--app-bg); box-shadow: none; }
.mood-card { padding: 30px 24px 26px; text-align: center; }
.mood-card p { margin: 0 0 22px; color: var(--app-text-light); font-size: 15px; }
.star-picker { display: flex; justify-content: center; gap: 14px; }
.star-picker button { border: 0; padding: 0; background: transparent; font-size: 40px; line-height: 1; cursor: pointer; opacity: .38; filter: grayscale(1); transition: transform .15s ease, opacity .15s ease, filter .15s ease; }
.star-picker button:hover, .star-picker button.selected { opacity: 1; filter: none; transform: scale(1.08); }
.mood-caption { margin-top: 14px; color: var(--app-primary); font-size: 15px; font-weight: 600; }
.content-card { padding: 24px 26px 18px; }
.content-card label { display: block; margin-bottom: 12px; color: var(--app-text-light); font-size: 15px; }
.content-card :deep(.el-textarea__inner) { min-height: 180px !important; padding: 0; border: 0; box-shadow: none; resize: vertical; color: var(--app-text); background: transparent; font-size: 15px; line-height: 1.8; }
.save-diary { width: 100%; height: 58px; border: 0; border-radius: 16px; font-size: 16px; font-weight: 600; }
.tip { color: var(--app-text-light); font-size: 14px; margin-bottom: 8px; }
.section { margin-bottom: 16px; }
.section h4 { margin: 0 0 8px; font-size: 14px; color: var(--app-text); }
.tag-list { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 8px; }
.tag-score { display: flex; align-items: center; gap: 6px; }
.score-input { width: 90px; }
.add-select { width: 100%; }
.empty { color: var(--app-text-light); font-size: 13px; }
@media (max-width: 700px) { .write-page { padding: 28px 14px 40px; } .mood-tabs { gap: 18px; margin-bottom: 26px; } .mood-tab { height: 48px; padding: 0; font-size: 20px; line-height: 28px; } .star-picker { gap: 6px; } .star-picker button { font-size: 40px; } .date-card, .analysis-card { padding: 18px; } }
</style>
