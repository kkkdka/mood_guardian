<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { savePreferences } from '../api/preferences'

const router = useRouter()


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


const form = reactive({
  movie_genre: [],
  book_genre: [],
  exercise_type: [], 
})

const submitting = ref(false)


async function handleSave() {
  submitting.value = true
  try {
    await savePreferences({
      movie_genre: form.movie_genre.join(','),
      book_genre: form.book_genre.join(','),
      exercise_type: JSON.stringify(form.exercise_type),
    })
    ElMessage.success('偏好设置已保存')
    
    router.push('/')
  } catch (err) {
    const msg = err.response?.data?.detail || err.message || '保存失败'
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}


function handleSkip() {
  router.push('/')
}
</script>

<template>
  <div class="guide-page">
    <h2>完善你的偏好设置</h2>
    <p class="tip">
      这些偏好会帮助「治愈助手」为你推荐更合适的内容，你可以稍后在「个人设置」中随时修改。
    </p>

    <el-form label-width="140px" @submit.prevent>
      <el-form-item label="喜欢的电影类型">
        <el-select
          v-model="form.movie_genre"
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
          v-model="form.book_genre"
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
          v-model="form.exercise_type"
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
        <el-button type="primary" :loading="submitting" @click="handleSave">
          保存并进入
        </el-button>
        <el-button @click="handleSkip">跳过</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<style scoped>
.guide-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 40px 16px;
}
.guide-page h2 {
  margin: 0 0 12px;
}
.tip {
  color: #909399;
  margin: 0 0 24px;
}
</style>