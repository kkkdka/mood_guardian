<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  addLibraryItem,
  addLibraryReview,
  deleteLibraryItem,
  finishLibraryBook,
  getBookReviews,
  getLibraryBooks,
  getLibraryMovies,
  getMovieReviews,
} from '../api/library'

const activeTab = ref('movies')
const activeMovieStatus = ref('want_to_watch')
const activeBookStatus = ref('want_to_read')
const loading = ref(false)
const movies = ref([])
const books = ref([])
const finishingBookId = ref(null)
const deletingId = ref(null)
const addDialogVisible = ref(false)
const adding = ref(false)
const addForm = ref({ item_type: 'movie', title: '', status: 'want_to_watch' })
const reviewDialogVisible = ref(false)
const reviewLoading = ref(false)
const reviewType = ref('book')
const reviewData = ref({
  title: '',
  average_rating: null,
  review_count: 0,
  reviews: [],
})
const reviewForm = ref({ rating: 8, feedback_text: '' })
const submittingReview = ref(false)

const filteredMovies = computed(() =>
  movies.value.filter((movie) => movie.status === activeMovieStatus.value),
)
const filteredBooks = computed(() =>
  books.value.filter((book) => book.status === activeBookStatus.value),
)
const hasMovies = computed(() => filteredMovies.value.length > 0)
const hasBooks = computed(() => filteredBooks.value.length > 0)

function formatMonthDay(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${month}-${day}`
}

function statusLabel(status) {
  return {
    want_to_watch: '想看',
    watched: '已看',
    want_to_read: '想读',
    reading: '在读',
    finished: '已读',
  }[status] || '未分类'
}

async function loadMovies() {
  loading.value = true
  try {
    const data = await getLibraryMovies()
    movies.value = Array.isArray(data) ? data : []
  } catch (_error) {
    ElMessage.error('加载电影片单失败')
  } finally {
    loading.value = false
  }
}

async function loadBooks() {
  loading.value = true
  try {
    const data = await getLibraryBooks()
    books.value = Array.isArray(data) ? data : []
  } catch (_error) {
    ElMessage.error('加载书单失败')
  } finally {
    loading.value = false
  }
}

async function loadLibrary() {
  await Promise.all([loadMovies(), loadBooks()])
}

async function viewReviews(item, type) {
  reviewType.value = type
  reviewForm.value = { rating: 8, feedback_text: '' }
  reviewDialogVisible.value = true
  reviewLoading.value = true
  reviewData.value = {
    title: item.title,
    average_rating: null,
    review_count: 0,
    reviews: [],
  }

  try {
    const getReviews = type === 'movie' ? getMovieReviews : getBookReviews
    const data = await getReviews(item.title)
    reviewData.value = {
      title: data.title || item.title,
      average_rating: data.average_rating ?? null,
      review_count: data.review_count || 0,
      reviews: Array.isArray(data.reviews) ? data.reviews : [],
    }
  } catch (_error) {
    ElMessage.error(`加载${type === 'movie' ? '电影' : '书籍'}评价失败`)
  } finally {
    reviewLoading.value = false
  }
}

async function submitReview() {
  submittingReview.value = true
  try {
    await addLibraryReview(reviewType.value, reviewData.value.title, {
      rating: reviewForm.value.rating,
      feedback_text: reviewForm.value.feedback_text.trim() || null,
    })
    ElMessage.success('评价已保存')
    reviewForm.value = { rating: 8, feedback_text: '' }
    const getReviews = reviewType.value === 'movie' ? getMovieReviews : getBookReviews
    const data = await getReviews(reviewData.value.title)
    reviewData.value = {
      title: data.title,
      average_rating: data.average_rating ?? null,
      review_count: data.review_count || 0,
      reviews: Array.isArray(data.reviews) ? data.reviews : [],
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '评价保存失败')
  } finally {
    submittingReview.value = false
  }
}

function formatReviewDate(value) {
  if (!value) return '暂无时间'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hours}:${minutes}`
}

async function finishBook(book) {
  finishingBookId.value = book.id
  try {
    await finishLibraryBook(book.id)
    ElMessage.success('已标记为读完')
    await loadBooks()
  } catch (_error) {
    ElMessage.error('更新书籍状态失败')
  } finally {
    finishingBookId.value = null
  }
}

async function deleteItem(item) {
  try {
    await ElMessageBox.confirm(`确定要删除「${item.title}」吗？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch (_error) {
    return
  }
  deletingId.value = item.id
  try {
    await deleteLibraryItem(item.id)
    ElMessage.success('已删除')
    await loadLibrary()
  } catch (_error) {
    ElMessage.error('删除失败，请稍后再试')
  } finally {
    deletingId.value = null
  }
}

async function addItem() {
  const title = addForm.value.title.trim()
  if (!title) {
    ElMessage.warning('请输入电影名或书名')
    return
  }
  adding.value = true
  try {
    const response = await addLibraryItem({
      item_type: addForm.value.item_type,
      title,
      status: addForm.value.status,
    })
    ElMessage.success(response.message || '已加入片单/书单')
    addForm.value.title = ''
    addDialogVisible.value = false
    await loadLibrary()
  } catch (_error) {
    ElMessage.error('添加失败，请稍后再试')
  } finally {
    adding.value = false
  }
}

function changeItemType(itemType) {
  addForm.value.status = itemType === 'movie' ? 'want_to_watch' : 'want_to_read'
}

function openAddDialog() {
  addForm.value = { item_type: 'movie', title: '', status: 'want_to_watch' }
  addDialogVisible.value = true
}

onMounted(loadLibrary)
</script>

<template>
  <section class="library-page">
    <div class="library-toolbar">
      <el-tabs v-model="activeTab" class="library-tabs">
        <el-tab-pane label="电影片单" name="movies" />
        <el-tab-pane label="书籍清单" name="books" />
      </el-tabs>
      <div class="toolbar-actions">
        <el-button type="primary" plain @click="openAddDialog">+ 手动添加</el-button>
        <el-button
          class="refresh-button"
          text
          :loading="loading"
          aria-label="刷新媒体库"
          title="刷新媒体库"
          @click="loadLibrary"
        >
          ↻
        </el-button>
      </div>
    </div>

    <div v-if="activeTab === 'movies'" v-loading="loading" class="tab-content">
      <el-radio-group v-model="activeMovieStatus" class="status-tabs" size="large">
        <el-radio-button value="want_to_watch">想看</el-radio-button>
        <el-radio-button value="watched">已看</el-radio-button>
      </el-radio-group>
      <el-empty v-if="!loading && !hasMovies" description="该分类还没有电影" />
      <div v-else class="item-list">
        <el-card v-for="movie in filteredMovies" :key="movie.id" shadow="never" class="library-item">
          <div class="media-cover movie-cover" aria-hidden="true">🎬</div>
          <div class="media-content">
            <h3 class="item-title">{{ movie.title }}</h3>
            <el-tag :class="`status-tag status-${movie.status}`" effect="light">
              {{ statusLabel(movie.status) }}
            </el-tag>
            <div v-if="movie.director || movie.year || movie.category" class="item-meta">
              <span v-if="movie.director">{{ movie.director }}</span>
              <span v-if="movie.year">{{ movie.year }}</span>
              <span v-if="movie.category">{{ movie.category }}</span>
            </div>
            <div class="item-date">加入时间 {{ formatMonthDay(movie.created_at) }}</div>
            <div v-if="movie.rating || movie.feedback_text" class="item-review">
              <el-rate v-if="movie.rating" :model-value="movie.rating" :max="10" disabled />
              <span v-if="movie.feedback_text">{{ movie.feedback_text }}</span>
            </div>
          </div>
          <div class="book-action">
            <el-button text @click="viewReviews(movie, 'movie')">查看评价</el-button>
            <el-button
              text
              type="danger"
              :loading="deletingId === movie.id"
              @click="deleteItem(movie)"
            >
              删除
            </el-button>
          </div>
        </el-card>
      </div>
    </div>

    <div v-else v-loading="loading" class="tab-content">
      <el-radio-group v-model="activeBookStatus" class="status-tabs" size="large">
        <el-radio-button value="want_to_read">想看</el-radio-button>
        <el-radio-button value="reading">在看</el-radio-button>
        <el-radio-button value="finished">已看</el-radio-button>
      </el-radio-group>
      <el-empty v-if="!loading && !hasBooks" description="该分类还没有书籍" />
      <div v-else class="item-list">
        <el-card v-for="book in filteredBooks" :key="book.id" shadow="never" class="library-item book-item">
          <div class="media-cover book-cover" aria-hidden="true">📖</div>
          <div class="media-content">
            <h3 class="item-title">{{ book.title }}</h3>
            <el-tag :class="`status-tag status-${book.status}`" effect="light">
              {{ statusLabel(book.status) }}
            </el-tag>
            <div v-if="book.rating || book.feedback_text" class="item-review book-review">
              <el-rate v-if="book.rating" :model-value="book.rating" :max="10" disabled />
              <span v-if="book.feedback_text">{{ book.feedback_text }}</span>
            </div>
            <div class="item-date">加入时间 {{ formatMonthDay(book.created_at) }}</div>
          </div>
          <div class="book-action">
            <el-button text @click="viewReviews(book, 'book')">查看评价</el-button>
            <el-button
              v-if="book.status === 'reading'"
              type="primary"
              plain
              :loading="finishingBookId === book.id"
              @click="finishBook(book)"
            >
              已读完
            </el-button>
            <el-button
              text
              type="danger"
              :loading="deletingId === book.id"
              @click="deleteItem(book)"
            >
              删除
            </el-button>
          </div>
        </el-card>
      </div>
    </div>

    <el-dialog
      v-model="addDialogVisible"
      title="手动添加"
      width="min(460px, 92vw)"
    >
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="类型">
          <el-segmented
            v-model="addForm.item_type"
            :options="[
              { label: '电影', value: 'movie' },
              { label: '书籍', value: 'book' },
            ]"
            block
            @change="changeItemType"
          />
        </el-form-item>
        <el-form-item :label="addForm.item_type === 'movie' ? '电影名' : '书名'">
          <el-input
            v-model="addForm.title"
            :placeholder="addForm.item_type === 'movie' ? '输入想看的电影' : '输入想读的书'"
            maxlength="100"
            clearable
            @keyup.enter="addItem"
          />
        </el-form-item>
        <el-form-item :label="addForm.item_type === 'movie' ? '观看状态' : '阅读状态'">
          <el-radio-group v-if="addForm.item_type === 'movie'" v-model="addForm.status">
            <el-radio-button value="want_to_watch">想看</el-radio-button>
            <el-radio-button value="watched">已看</el-radio-button>
          </el-radio-group>
          <el-radio-group v-else v-model="addForm.status">
            <el-radio-button value="want_to_read">想读</el-radio-button>
            <el-radio-button value="reading">在读</el-radio-button>
            <el-radio-button value="finished">已读</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="adding" @click="addItem">确认添加</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="reviewDialogVisible"
      :title="`${reviewData.title} 的${reviewType === 'movie' ? '电影' : '书籍'}评价`"
      width="min(680px, 92vw)"
    >
      <div v-loading="reviewLoading" class="review-dialog-content">
        <section class="review-editor">
          <div class="review-editor-head">
            <strong>写评价</strong>
            <span>{{ reviewForm.rating }} 分</span>
          </div>
          <el-rate v-model="reviewForm.rating" :max="10" show-score score-template="{value} 分" />
          <el-input
            v-model="reviewForm.feedback_text"
            type="textarea"
            :rows="3"
            maxlength="300"
            show-word-limit
            placeholder="写下你的感受（可选）"
          />
          <div class="review-editor-actions">
            <el-button type="primary" :loading="submittingReview" @click="submitReview">
              发布评价
            </el-button>
          </div>
        </section>

        <div class="review-summary">
          <div>
            <span class="summary-label">平均分</span>
            <el-rate
              :model-value="reviewData.average_rating || 0"
              :max="10"
              disabled
              show-score
              score-template="{value} 分"
            />
          </div>
          <span class="review-count">{{ reviewData.review_count }} 条评价</span>
        </div>

        <el-empty v-if="!reviewLoading && !reviewData.reviews.length" description="暂无评价" />
        <div v-else class="review-list">
          <div v-for="review in reviewData.reviews" :key="review.id" class="review-item">
            <div class="review-head">
              <el-rate :model-value="review.rating" :max="10" disabled />
              <span>{{ formatReviewDate(review.feedback_at || review.created_at) }}</span>
            </div>
            <p v-if="review.feedback_text" class="review-text">{{ review.feedback_text }}</p>
          </div>
        </div>
      </div>
    </el-dialog>
  </section>
</template>

<style scoped>
.library-page {
  width: min(1080px, calc(100% - 48px));
  margin: 0 auto;
  padding: 28px 0 64px;
}
.library-toolbar {
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--app-border);
}
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 12px;
}
.toolbar-actions :deep(.el-button) {
  margin-left: 0;
}
.library-tabs {
  flex: 1;
  min-width: 0;
}
.library-tabs :deep(.el-tabs__header) {
  height: 48px;
  margin: 0;
}
.library-tabs :deep(.el-tabs__item) {
  box-sizing: border-box;
  height: 48px;
  padding: 0 22px;
  color: var(--app-text-light);
  font-size: 20px;
  font-weight: 400;
  line-height: 28px;
}
.library-tabs :deep(.el-tabs__item.is-active) {
  font-weight: 600;
}
.library-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}
.library-tabs :deep(.el-tabs__item:first-child) {
  padding-left: 0;
}
.library-tabs :deep(.el-tabs__item:hover) {
  color: var(--app-text);
}
.library-tabs :deep(.el-tabs__item.is-active) {
  color: var(--app-text);
}
.library-tabs :deep(.el-tabs__active-bar) {
  height: 2px;
  background-color: var(--app-primary);
}
.refresh-button {
  flex: 0 0 32px;
  width: 32px;
  height: 32px;
  padding: 0;
  color: var(--app-text-light);
  font-size: 19px;
}
.refresh-button:hover {
  color: var(--app-primary-dark);
}
.tab-content {
  min-height: 240px;
  padding-top: 20px;
}
.status-tabs {
  display: flex;
  margin-bottom: 18px;
}
.status-tag {
  width: fit-content;
  margin-top: 7px;
  border-radius: 999px;
}
.status-want_to_watch,
.status-want_to_read {
  --el-tag-bg-color: #e8f4ff;
  --el-tag-border-color: #b9ddf7;
  --el-tag-text-color: #397ba6;
}
.status-reading {
  --el-tag-bg-color: #fff1dc;
  --el-tag-border-color: #f2c98e;
  --el-tag-text-color: #b56a18;
}
.status-watched,
.status-finished {
  --el-tag-bg-color: #e7f6ea;
  --el-tag-border-color: #b8dfbf;
  --el-tag-text-color: #39804a;
}
.item-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.library-item {
  display: flex;
  align-items: center;
  min-height: 112px;
  border: 1px solid var(--app-border);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 4px 14px rgba(74, 82, 72, .04);
  transition: border-color .2s ease, box-shadow .2s ease;
}
.library-item:hover {
  border-color: var(--app-primary-light);
  box-shadow: 0 8px 22px rgba(74, 82, 72, .08);
}
.library-item :deep(.el-card__body) {
  display: flex;
  align-items: center;
  width: 100%;
  min-width: 0;
  padding: 22px 24px;
}
.media-cover {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  color: #a78d70;
  background: #f2e9dc;
  font-size: 23px;
}
.movie-cover {
  width: 48px;
  height: 64px;
}
.book-cover {
  width: 52px;
  height: 72px;
  background: #eee6d8;
}
.media-content {
  min-width: 0;
  margin-left: 20px;
}
.item-title {
  margin: 0;
  color: var(--app-text);
  font-size: 17px;
  font-weight: 600;
  line-height: 25px;
  overflow-wrap: anywhere;
}
.item-meta,
.item-review {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin-top: 7px;
  color: var(--app-text-light);
  font-size: 12px;
  line-height: 18px;
}
.item-meta span + span::before {
  margin-right: 14px;
  content: '·';
  color: var(--app-border);
}
.item-date {
  margin-top: 10px;
  color: var(--app-text-light);
  font-size: 12px;
  line-height: 18px;
}
.item-review :deep(.el-rate) {
  height: 18px;
}
.item-review :deep(.el-rate__icon) {
  margin-right: 1px;
  font-size: 14px;
}
.item-review span {
  max-width: 560px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.book-status {
  display: inline-flex;
  margin-top: 7px;
  color: var(--app-primary-dark);
  font-size: 13px;
}
.book-review {
  margin-top: 8px;
}
.book-action {
  flex: 0 0 auto;
  margin-left: auto;
  padding-left: 24px;
}
.book-action :deep(.el-button) {
  border-radius: 6px;
}
.review-dialog-content {
  min-height: 120px;
}
.review-editor {
  display: grid;
  gap: 12px;
  margin-bottom: 20px;
  padding: 16px;
  border: 1px solid var(--app-border);
  border-radius: 10px;
  background: var(--app-surface-soft, #faf8f4);
}
.review-editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--app-text);
}
.review-editor-head span {
  color: var(--app-primary-dark);
  font-size: 13px;
  font-weight: 600;
}
.review-editor :deep(.el-rate) {
  height: 22px;
}
.review-editor :deep(.el-rate__icon) {
  margin-right: 2px;
  font-size: 18px;
}
.review-editor-actions {
  display: flex;
  justify-content: flex-end;
}
.review-summary,
.review-head {
  display: flex;
  align-items: center;
}
.review-summary {
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--app-border);
}
.summary-label {
  display: block;
  margin-bottom: 6px;
  color: var(--app-text-light);
  font-size: 12px;
}
.review-count,
.review-head span {
  color: var(--app-text-light);
  font-size: 12px;
}
.review-list {
  display: grid;
  gap: 16px;
  margin-top: 16px;
}
.review-item {
  padding-bottom: 14px;
  border-bottom: 1px solid color-mix(in srgb, var(--app-border) 75%, transparent);
}
.review-head {
  justify-content: space-between;
  gap: 12px;
}
.review-text {
  margin: 8px 0 0;
  color: var(--app-text);
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
@media (max-width: 680px) {
  .library-page {
    width: calc(100% - 32px);
    padding-top: 18px;
  }
  .library-toolbar {
    align-items: flex-start;
  }
  .toolbar-actions {
    padding-top: 8px;
  }
  .toolbar-actions :deep(.el-button:first-child) {
    padding-left: 8px;
    padding-right: 8px;
  }
  .library-tabs :deep(.el-tabs__item) {
    padding: 0 14px;
  }
  .library-tabs :deep(.el-tabs__item:first-child) {
    padding-left: 0;
  }
  .library-item :deep(.el-card__body) {
    align-items: flex-start;
    padding: 18px 16px;
  }
  .media-content {
    flex: 1;
    margin-left: 14px;
  }
  .book-action {
    align-self: center;
    padding-left: 12px;
  }
  .item-review span {
    max-width: 100%;
  }
}
</style>
