<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listSchedules, createSchedule, updateSchedule, deleteSchedule, toggleSchedule, completeAllSchedules } from '../api/schedules'

const HOUR_HEIGHT = 60   
const START_HOUR = 6     
const END_HOUR = 23      

const BODY_HEIGHT = (END_HOUR - START_HOUR + 1) * HOUR_HEIGHT // 18*60 = 1080px


const CATEGORY_OPTIONS = [
  { value: 'study', label: '学习' },
  { value: 'work', label: '工作' },
  { value: 'life', label: '生活' },
]



const WEEK_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']


function formatDate(d) {
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}


function parseDateStr(str) {
  const [y, m, d] = str.split('-').map(Number)
  return new Date(y, m - 1, d)
}


function mmdd(d) {
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${m}-${day}`
}


function monthDayCn(d) {
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function weekdayName(d) {
  return WEEK_NAMES[d.getDay()]
}


function getMonday(d) {
  const date = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const day = date.getDay() 
  const diff = day === 0 ? 6 : day - 1 
  date.setDate(date.getDate() - diff)
  return date
}


function toTime(dtStr) {
  return dtStr.slice(11, 16)
}


function toMinutes(dtStr) {
  const h = Number(dtStr.slice(11, 13))
  const m = Number(dtStr.slice(14, 16))
  return h * 60 + m
}


const loading = ref(false)                  
const schedules = ref([])                   
const weekStart = ref(getMonday(new Date())) 
const today = formatDate(new Date())        


const viewMode = ref('week')

const selectedDate = ref(today)


const weekDays = computed(() => {
  const days = []
  for (let i = 0; i < 7; i++) {
    const d = new Date(weekStart.value)
    d.setDate(weekStart.value.getDate() + i)
    days.push(d)
  }
  return days
})


const displayDays = computed(() => {
  if (viewMode.value === 'day') {
    return [parseDateStr(selectedDate.value)]
  }
  return weekDays.value
})


const periodRange = computed(() => {
  if (viewMode.value === 'day') {
    return monthDayCn(parseDateStr(selectedDate.value))
  }
  const start = weekStart.value
  const end = new Date(start)
  end.setDate(start.getDate() + 6)
  return `${mmdd(start)} 至 ${mmdd(end)}`
})


const hours = computed(() => {
  const arr = []
  for (let h = START_HOUR; h <= END_HOUR; h++) arr.push(h)
  return arr
})


function hourTop(h) {
  return `${(h - START_HOUR) * HOUR_HEIGHT}px`
}


function hourLabel(h) {
  return `${String(h).padStart(2, '0')}:00`
}


const dialogVisible = ref(false)    
const isEdit = ref(false)           
const editingId = ref(null)         
const editingCompleted = ref(false) 

const form = reactive({
  title: '',
  date: '',           // 'YYYY-MM-DD'
  start_time: '',     // 'HH:mm'
  end_time: '',       // 'HH:mm'
  category: 'life',   
})



async function loadSchedules() {
  loading.value = true
  const start = formatDate(weekStart.value)
  const endDate = new Date(weekStart.value)
  endDate.setDate(weekStart.value.getDate() + 6)
  try {
    schedules.value = await listSchedules({
      start_date: start,
      end_date: formatDate(endDate),
    })
  } catch (err) {
    ElMessage.error('加载日程失败')
  } finally {
    loading.value = false
  }
}


function changePeriod(offset) {
  if (viewMode.value === 'week') {
    const d = new Date(weekStart.value)
    d.setDate(d.getDate() + offset * 7)
    weekStart.value = d
    loadSchedules()
  } else {
    
    const d = parseDateStr(selectedDate.value)
    d.setDate(d.getDate() + offset)
    selectedDate.value = formatDate(d)
    
    const ws = formatDate(getMonday(d))
    if (ws !== formatDate(weekStart.value)) {
      weekStart.value = getMonday(d)
      loadSchedules()
    }
  }
}


function goToday() {
  weekStart.value = getMonday(new Date())
  selectedDate.value = today
  loadSchedules()
}


async function completeAll(dateStr) {
  try {
    await ElMessageBox.confirm('确定将当天所有日程标记为完成吗？', '一键完成', {
      type: 'warning',
      confirmButtonText: '一键完成',
      cancelButtonText: '取消',
    })
  } catch {
    return 
  }
  try {
    const res = await completeAllSchedules({ date: dateStr })
    ElMessage.success(`已完成 ${res.updated} 条日程`)
    loadSchedules() 
  } catch (err) {
    ElMessage.error('一键完成失败')
  }
}


function schedulesOf(dayStr) {
  return schedules.value
    .filter((s) => s.start_time.slice(0, 10) === dayStr)
    .sort((a, b) => a.start_time.localeCompare(b.start_time))
}




function layoutOf(dayStr) {
  const list = schedulesOf(dayStr)

  
  const clusters = []
  let cur = []
  let curEnd = -1
  for (const s of list) {
    const sMin = toMinutes(s.start_time)
    const eMin = toMinutes(s.end_time)
    if (cur.length && sMin >= curEnd) {
      
      clusters.push(cur)
      cur = [s]
      curEnd = eMin
    } else {
      cur.push(s)
      curEnd = Math.max(curEnd, eMin)
    }
  }
  if (cur.length) clusters.push(cur)

  
  const result = []
  for (const cluster of clusters) {
    const colEnds = [] 
    const assigned = cluster.map((s) => {
      const sMin = toMinutes(s.start_time)
      const eMin = toMinutes(s.end_time)
      let col = colEnds.findIndex((end) => end <= sMin)
      if (col === -1) {
        
        col = colEnds.length
        colEnds.push(eMin)
      } else {
        colEnds[col] = eMin
      }
      return { s, col }
    })
    const ncol = colEnds.length 
    assigned.forEach((a) => result.push({ s: a.s, col: a.col, ncol }))
  }
  return result
}


function blockStyle(item) {
  const { s, col, ncol } = item
  const startMin = toMinutes(s.start_time)
  const endMin = toMinutes(s.end_time)

  
  const topMin = Math.max(startMin, START_HOUR * 60)
  const botMin = Math.min(endMin, END_HOUR * 60)
  const top = ((topMin - START_HOUR * 60) / 60) * HOUR_HEIGHT
  
  const height = Math.max(22, ((botMin - topMin) / 60) * HOUR_HEIGHT)

  
  const leftPct = (col / ncol) * 100
  const widthPct = 100 / ncol
  return {
    top: `${top}px`,
    height: `${height}px`,
    left: `calc(${leftPct}% + 1px)`,
    width: `calc(${widthPct}% - 2px)`,
  }
}


function defaultDate() {
  const todayStr = formatDate(new Date())
  const weekStrs = weekDays.value.map((d) => formatDate(d))
  return weekStrs.includes(todayStr) ? todayStr : weekStrs[0]
}


function openAdd() {
  isEdit.value = false
  editingId.value = null
  form.title = ''
  
  form.date = viewMode.value === 'day' ? selectedDate.value : defaultDate()
  form.start_time = '09:00'
  form.end_time = '10:00'
  form.category = 'life'
  dialogVisible.value = true
}


function openEdit(s) {
  isEdit.value = true
  editingId.value = s.id
  editingCompleted.value = s.completed
  form.title = s.title
  form.date = s.start_time.slice(0, 10)
  form.start_time = s.start_time.slice(11, 16)
  form.end_time = s.end_time.slice(11, 16)
  form.category = s.category || 'life'
  dialogVisible.value = true
}


async function submitForm() {
  const { title, date, start_time, end_time } = form
  if (!title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  if (!date) {
    ElMessage.warning('请选择日期')
    return
  }
  if (!start_time || !end_time) {
    ElMessage.warning('请选择开始和结束时间')
    return
  }
  
  const start = `${date}T${start_time}`
  const end = `${date}T${end_time}`
  if (start >= end) {
    ElMessage.warning('结束时间要晚于开始时间')
    return
  }
  try {
    if (isEdit.value) {
      
      await updateSchedule(editingId.value, {
        title: title.trim(),
        start_time: start,
        end_time: end,
        completed: editingCompleted.value,
        category: form.category,
      })
      ElMessage.success('更新成功')
    } else {
      await createSchedule({
        title: title.trim(),
        start_time: start,
        end_time: end,
        category: form.category,
      })
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    loadSchedules()
  } catch (err) {
    const detail = err.response?.data?.detail
    ElMessage.error(detail || '保存失败')
  }
}


async function toggleCompleted(s) {
  try {
    const updated = await toggleSchedule(s.id)
    
    const idx = schedules.value.findIndex((x) => x.id === s.id)
    if (idx !== -1) schedules.value[idx] = updated
  } catch (err) {
    ElMessage.error('操作失败')
  }
}


async function handleDelete() {
  try {
    await ElMessageBox.confirm('确定删除该日程吗？', '提示', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return 
  }
  try {
    await deleteSchedule(editingId.value)
    ElMessage.success('删除成功')
    dialogVisible.value = false
    loadSchedules()
  } catch (err) {
    ElMessage.error('删除失败')
  }
}


watch(viewMode, (mode) => {
  if (mode === 'day') {
    const ws = formatDate(weekStart.value)
    const weDate = new Date(weekStart.value)
    weDate.setDate(weekStart.value.getDate() + 6)
    const we = formatDate(weDate)
    
    if (selectedDate.value < ws || selectedDate.value > we) {
      selectedDate.value = ws
    }
  }
})

onMounted(loadSchedules)
</script>

<template>
  <div class="schedule-page">
    <div class="sticky-top">
      <div class="schedule-toolbar">
        <div class="toolbar-left">
          <h2>日程管理</h2>
          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button value="day">日视图</el-radio-button>
            <el-radio-button value="week">周视图</el-radio-button>
          </el-radio-group>
          <div class="period-switch">
            <el-button class="period-button" @click="changePeriod(-1)" aria-label="上一个时间段">‹</el-button>
            <span class="period-range">{{ periodRange }}</span>
            <el-button class="period-button" @click="changePeriod(1)" aria-label="下一个时间段">›</el-button>
          </div>
          <el-button link type="primary" @click="goToday">今天</el-button>
        </div>
        <div class="toolbar-actions">
          <el-button type="primary" @click="openAdd">＋ 添加日程</el-button>
          <el-button type="success" @click="completeAll(viewMode === 'day' ? selectedDate : today)">✓ 一键完成</el-button>
        </div>
      </div>
      <div class="toolbar-meta">
        <div class="category-legend" aria-label="日程分类图例">
          <span class="legend-item"><i class="legend-dot study"></i>学习</span>
          <span class="legend-item"><i class="legend-dot work"></i>工作</span>
          <span class="legend-item"><i class="legend-dot life"></i>生活</span>
        </div>
      </div>
    </div>

    <div class="timeline-wrapper" :class="{ 'day-view': viewMode === 'day' }" v-loading="loading">
      <div class="timeline-head">
        <div class="axis-corner">时间</div>
        <div
          v-for="d in displayDays"
          :key="formatDate(d)"
          class="day-head"
          :class="{ today: formatDate(d) === today }"
        >
          <span class="weekday">{{ weekdayName(d) }}</span>
          <span class="date">{{ mmdd(d) }}</span>
        </div>
      </div>

      <div class="timeline-scroll">
        <div class="time-axis" :style="{ height: BODY_HEIGHT + 'px' }">
          <span
            v-for="h in hours"
            :key="h"
            class="hour-label"
            :class="{ first: h === START_HOUR }"
            :style="{ top: hourTop(h) }"
          >
            {{ hourLabel(h) }}
          </span>
        </div>
        <div
          v-for="d in displayDays"
          :key="formatDate(d)"
          class="day-body"
          :style="{ height: BODY_HEIGHT + 'px' }"
        >
          <div
            v-for="item in layoutOf(formatDate(d))"
            :key="item.s.id"
            class="sched-block"
            :class="['cat-' + (item.s.category || 'life'), { done: item.s.completed }]"
            :style="blockStyle(item)"
            @click="openEdit(item.s)"
          >
            <span class="circle" :class="{ checked: item.s.completed }" @click.stop="toggleCompleted(item.s)">✓</span>
            <div class="sched-info">
              <el-tooltip
                :content="`${item.s.title}（${toTime(item.s.start_time)} - ${toTime(item.s.end_time)}）`"
                placement="top"
                :show-after="150"
              >
                <div class="sched-title">{{ item.s.title }}</div>
              </el-tooltip>
              <div class="sched-time">{{ toTime(item.s.start_time) }} - {{ toTime(item.s.end_time) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑日程' : '添加日程'" width="440px">
      <el-form label-width="80px" @submit.prevent>
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="请输入日程标题" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" placeholder="请选择分类" style="width: 100%">
            <el-option
              v-for="c in CATEGORY_OPTIONS"
              :key="c.value"
              :label="c.label"
              :value="c.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="form.date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-time-picker
            v-model="form.start_time"
            format="HH:mm"
            value-format="HH:mm"
            placeholder="开始时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-time-picker
            v-model="form.end_time"
            format="HH:mm"
            value-format="HH:mm"
            placeholder="结束时间"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        
        <el-button v-if="isEdit" type="danger" plain style="float: left" @click="handleDelete">删除</el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<style scoped>
.schedule-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
  height: calc(100dvh - 64px);
  max-width: 1440px;
  margin: 0 auto;
  padding: 24px 20px 32px;
  overflow: hidden;
}
.sticky-top {
  flex-shrink: 0;
  position: relative;
  z-index: 10;
  padding: 8px 0 14px;
  margin-bottom: 16px;
  background: color-mix(in srgb, var(--app-bg) 96%, transparent);
}
.schedule-toolbar,
.toolbar-left,
.toolbar-actions,
.period-switch,
.toolbar-meta,
.category-legend,
.legend-item {
  display: flex;
  align-items: center;
}
.schedule-toolbar {
  justify-content: space-between;
  gap: 20px;
  min-height: 42px;
}
.toolbar-left { gap: 16px; min-width: 0; }
.toolbar-actions { gap: 10px; flex-shrink: 0; }
.period-switch { gap: 4px; }
.period-button {
  width: 30px;
  height: 30px;
  padding: 0;
  font-size: 22px;
  line-height: 1;
}
.period-range {
  min-width: 122px;
  color: var(--app-text);
  font-size: 14px;
  font-weight: 600;
  text-align: center;
  white-space: nowrap;
}
.toolbar-meta {
  justify-content: space-between;
  min-height: 28px;
  margin-top: 8px;
}
.category-legend { gap: 18px; color: var(--app-text-light); font-size: 13px; }
.legend-item { gap: 6px; }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; }
.legend-dot.study { background: var(--app-cat-study-dark); }
.legend-dot.work { background: var(--app-cat-work-dark); }
.legend-dot.life { background: var(--app-cat-life-dark); }

.timeline-wrapper {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--app-border);
  border-radius: 18px;
  background: var(--app-card-bg);
  box-shadow: 0 8px 24px rgba(74, 82, 72, .06);
}
.timeline-head,
.timeline-scroll {
  display: grid;
  grid-template-columns: 64px repeat(var(--day-count, 7), minmax(0, 1fr));
}
.timeline-head {
  box-sizing: border-box;
  grid-template-columns: 64px repeat(6, calc((100% - 64px - 4px) / 7)) calc((100% - 64px - 4px) / 7 + 4px);
}
.axis-corner {
  height: 58px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--app-text-light);
  background: var(--app-bg);
  border-right: 1px solid var(--app-border);
  border-bottom: 1px solid var(--app-border);
  font-size: 12px;
}
.day-head {
  height: 58px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-width: 0;
  border-bottom: 1px solid var(--app-border);
  border-left: 1px solid var(--app-border);
}
.day-head.today { background: color-mix(in srgb, var(--app-primary-light) 35%, var(--app-card-bg)); }
.weekday { color: var(--app-text); font-size: 13px; font-weight: 600; }
.date { color: var(--app-text-light); font-size: 11px; }
.timeline-scroll {
  --day-count: 7;
  flex: 1;
  min-height: 0;
  overflow: auto;
  align-items: start;
  background: var(--app-card-bg);
}
.timeline-wrapper.day-view .timeline-head,
.timeline-wrapper.day-view .timeline-scroll { grid-template-columns: 64px minmax(0, 1fr); }
.time-axis {
  position: relative;
  min-width: 0;
  background: var(--app-bg);
  border-right: 1px solid var(--app-border);
}
.hour-label {
  position: absolute;
  right: 9px;
  transform: translateY(-50%);
  color: var(--app-text-light);
  font-size: 11px;
  line-height: 1;
  white-space: nowrap;
}
.hour-label.first {
  transform: translateY(0);
}
.day-body {
  position: relative;
  min-width: 0;
  border-left: 1px solid var(--app-border);
  background-image: linear-gradient(to bottom, var(--app-border) 1px, transparent 1px);
  background-size: 100% 60px;
}
.sched-block {
  position: absolute;
  display: flex;
  align-items: flex-start;
  gap: 5px;
  box-sizing: border-box;
  overflow: hidden;
  padding: 5px 6px;
  border-left: 3px solid var(--app-primary);
  border-radius: 5px;
  background: var(--app-primary-light);
  cursor: pointer;
  transition: filter .15s, box-shadow .15s;
}
.sched-block:hover { filter: brightness(.98); box-shadow: 0 3px 10px rgba(0, 0, 0, .08); }
.sched-block.cat-study { border-left-color: var(--app-cat-study-dark); background: var(--app-cat-study); }
.sched-block.cat-work { border-left-color: var(--app-cat-work-dark); background: var(--app-cat-work); }
.sched-block.cat-life { border-left-color: var(--app-cat-life-dark); background: var(--app-cat-life); }
.sched-block.cat-study .sched-title { color: var(--app-cat-study-dark); }
.sched-block.cat-work .sched-title { color: var(--app-cat-work-dark); }
.sched-block.cat-life .sched-title { color: var(--app-cat-life-dark); }
.circle {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
  border: 1px solid var(--app-border);
  border-radius: 50%;
  color: transparent;
  font-size: 10px;
  cursor: pointer;
}
.circle.checked { border-color: var(--app-success); background: var(--app-success); color: var(--app-card-bg); }
.sched-info { min-width: 0; flex: 1; line-height: 1.25; }
.sched-title,
.sched-time { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sched-title { color: var(--app-text); font-size: 12px; font-weight: 500; }
.sched-time { color: var(--app-text-light); font-size: 10px; }
.sched-block.done .sched-title { color: var(--app-text-light); text-decoration: line-through; }
.timeline-wrapper.day-view .day-head .weekday { font-size: 16px; }
.timeline-wrapper.day-view .day-head .date { font-size: 13px; }
.timeline-wrapper.day-view .sched-block { padding: 7px 9px; }
.timeline-wrapper.day-view .sched-title { font-size: 14px; }
.timeline-wrapper.day-view .sched-time { font-size: 12px; }
@media (max-width: 800px) {
  .schedule-page {
    height: calc(100vh - 64px);
    height: calc(100dvh - 64px);
    padding: 16px 12px 24px;
  }
  .schedule-toolbar { align-items: flex-start; flex-direction: column; gap: 12px; }
  .toolbar-left { width: 100%; flex-wrap: wrap; gap: 10px; }
  .toolbar-actions { width: 100%; }
  .toolbar-actions .el-button { flex: 1; }
}
</style>