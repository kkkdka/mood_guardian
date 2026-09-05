<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'


import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { getDailyAvg } from '../api/stats'


echarts.use([BarChart, GridComponent, TooltipComponent, DataZoomComponent, CanvasRenderer])

const viewMode = ref('day') 
const loading = ref(false)  

const chartRef = ref(null) 
let chart = null           

const dayDate = ref(new Date())           
const weekStart = ref(getMonday(new Date())) 
const monthDate = ref(new Date())         



function getMonday(d) {
  const date = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const day = date.getDay() 
  const diff = day === 0 ? 6 : day - 1 
  date.setDate(date.getDate() - diff)
  return date
}


function formatDate(d) {
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}


function mmdd(d) {
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${m}-${day}`
}



const weekDays = computed(() => {
  const days = []
  for (let i = 0; i < 7; i++) {
    const d = new Date(weekStart.value)
    d.setDate(weekStart.value.getDate() + i)
    days.push(d)
  }
  return days
})


const weekRange = computed(() => {
  const start = weekStart.value
  const end = new Date(start)
  end.setDate(start.getDate() + 6)
  return `${mmdd(start)} 至 ${mmdd(end)}`
})



function getMonthDays(year, month) {
  const days = []
  const lastDay = new Date(year, month + 1, 0).getDate() 
  for (let d = 1; d <= lastDay; d++) {
    days.push(new Date(year, month, d))
  }
  return days
}



function targetDays() {
  if (viewMode.value === 'day') {
    return [new Date(dayDate.value)]
  }
  if (viewMode.value === 'week') {
    return weekDays.value
  }
  
  const y = monthDate.value.getFullYear()
  const m = monthDate.value.getMonth()
  return getMonthDays(y, m)
}


function initChart() {
  chart = echarts.init(chartRef.value)
}

function handleResize() {
  chart && chart.resize()
}


function colorByScore(v) {
  const styles = getComputedStyle(document.documentElement)
  if (v < 5) return styles.getPropertyValue('--app-danger').trim()
  if (v <= 7) return styles.getPropertyValue('--app-primary-light').trim()
  return styles.getPropertyValue('--app-success').trim()
}


function buildBarOption(labels, scores, hasData, isMonth) {
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        
        if (!hasData[p.dataIndex]) {
          return `${p.axisValue}<br/>无记录`
        }
        return `${p.axisValue}<br/>平均分：${Number(p.value).toFixed(1)}`
      },
    },
    grid: { left: 40, right: 20, top: 40, bottom: isMonth ? 60 : 40 },
    xAxis: {
      type: 'category',
      data: labels, 
      axisLabel: { interval: 0 }, 
    },
    yAxis: {
      type: 'value',
      name: '平均分',
      min: 0,
      max: 10,
      interval: 1, 
    },
    series: [
      {
        name: '每日平均心情',
        type: 'bar',
        data: scores, 
        barMaxWidth: isMonth ? 14 : 36, 
        itemStyle: {
          
          color: (params) => colorByScore(params.value),
        },
        label: {
          show: true,
          position: 'top',
          
          formatter: (p) => (p.value > 0 ? Number(p.value).toFixed(1) : ''),
        },
      },
    ],
  }

  
  if (isMonth) {
    const total = labels.length
    option.dataZoom = [
      {
        type: 'slider',
        xAxisIndex: 0,
        height: 20,
        bottom: 8,
        start: 0,
        
        end: total > 10 ? Math.round((10 / total) * 100) : 100,
      },
      {
        type: 'inside', 
        xAxisIndex: 0,
        start: 0,
        end: total > 10 ? Math.round((10 / total) * 100) : 100,
      },
    ]
  }

  return option
}


async function loadData() {
  const days = targetDays() 
  const start = formatDate(days[0])
  const end = formatDate(days[days.length - 1])

  loading.value = true
  try {
    const data = await getDailyAvg({ start_date: start, end_date: end })

    
    const scoreMap = {}
    data.dates.forEach((date, i) => {
      scoreMap[date] = data.avg_scores[i]
    })

    
    const labels = days.map((d) => mmdd(d))
    const scores = days.map((d) => scoreMap[formatDate(d)] ?? 0)
    const hasData = days.map((d) => scoreMap[formatDate(d)] !== undefined)

    
    chart && chart.setOption(buildBarOption(labels, scores, hasData, viewMode.value === 'month'), true)

    
    if (!hasData.some(Boolean)) {
      ElMessage.info('该时间段暂无记录')
    }
  } catch (err) {
    ElMessage.error('查询失败，请稍后再试')
  } finally {
    loading.value = false
  }
}



function changeWeek(offset) {
  const d = new Date(weekStart.value)
  d.setDate(d.getDate() + offset * 7)
  weekStart.value = d
}


function goThisWeek() {
  weekStart.value = getMonday(new Date())
}



watch(viewMode, loadData)
watch(dayDate, loadData)
watch(weekStart, loadData)
watch(monthDate, loadData)

onMounted(() => {
  initChart()
  loadData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (chart) {
    chart.dispose() 
    chart = null
  }
})
</script>

<template>
  <div class="stats-page">
    <h2>每日平均心情</h2>

    
    <el-radio-group v-model="viewMode" size="small" class="view-tabs">
      <el-radio-button value="day">日视图</el-radio-button>
      <el-radio-button value="week">周视图</el-radio-button>
      <el-radio-button value="month">月视图</el-radio-button>
    </el-radio-group>

    
    <div class="toolbar">
      
      <div v-if="viewMode === 'day'" class="tool-item">
        <el-date-picker
          v-model="dayDate"
          type="date"
          placeholder="选择日期"
          format="YYYY-MM-DD"
        />
      </div>

      
      <div v-else-if="viewMode === 'week'" class="tool-item week-switch">
        <el-button circle @click="changeWeek(-1)">‹</el-button>
        <span class="week-range">{{ weekRange }}</span>
        <el-button circle @click="changeWeek(1)">›</el-button>
        <el-button @click="goThisWeek">本周</el-button>
      </div>

      
      <div v-else class="tool-item">
        <el-date-picker
          v-model="monthDate"
          type="month"
          placeholder="选择月份"
          format="YYYY-MM"
        />
      </div>
    </div>

    
    <div ref="chartRef" class="chart" v-loading="loading"></div>

  </div>
</template>

<style scoped>
.stats-page { max-width: 1080px; margin: 0 auto; padding: 40px 24px 64px; }
.stats-page h2 { margin: 0 0 24px; color: var(--app-text); font-size: 28px; }
.view-tabs { margin-bottom: 22px; }
.toolbar { display: flex; align-items: center; min-height: 58px; margin-bottom: 20px; padding: 12px 16px; background: var(--app-card-bg); border: 1px solid var(--app-border); border-radius: 16px; }
.tool-item { display: flex; align-items: center; }
.week-switch { gap: 12px; width: 100%; justify-content: center; }
.week-range { min-width: 200px; color: var(--app-primary-dark); font-size: 16px; font-weight: 600; text-align: center; }
.chart { width: 100%; height: 430px; padding: 10px; background: var(--app-card-bg); border: 1px solid var(--app-border); border-radius: 16px; box-shadow: var(--app-shadow); }
@media (max-width: 600px) { .stats-page { padding: 28px 16px 48px; } .stats-page h2 { font-size: 24px; } .toolbar :deep(.el-date-editor) { width: 100%; } .week-range { min-width: 0; font-size: 14px; } .chart { height: 360px; } }
</style>