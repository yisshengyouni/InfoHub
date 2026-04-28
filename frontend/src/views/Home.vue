<template>
  <div class="home">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <input 
        v-model="searchQuery" 
        @input="debounceSearch"
        placeholder="🔍 搜索内容..." 
        class="search-input"
      />
      <div class="filters">
        <select v-model="currentFeed" @change="store.setFeedFilter(currentFeed || null)">
          <option value="">全部订阅</option>
          <option v-for="feed in store.feeds" :key="feed.id" :value="feed.id">
            {{ feed.name }}
          </option>
        </select>
        <button @click="store.filterStarred = store.filterStarred === null ? true : null; store.loadContents()" 
                :class="{ active: store.filterStarred }">⭐</button>
        <button @click="store.filterRead = store.filterRead === null ? false : null; store.loadContents()" 
                :class="{ active: store.filterRead === false }">📖 未读</button>
        <button @click="refresh" :disabled="refreshing" class="refresh-btn">
          {{ refreshing ? '🔄 抓取中...' : '🔄 全部抓取' }}
        </button>
      </div>
    </div>

    <!-- 内容列表 -->
    <div v-if="store.loading" class="loading">加载中...</div>
    <div v-else-if="store.contents.length === 0" class="empty">暂无内容，先去添加订阅吧！</div>
    <div v-else class="content-list">
      <div v-for="item in store.contents" :key="item.id" 
           class="content-card" :class="{ unread: !item.is_read }">
        <div class="card-header">
          <h3 @click="openDetail(item)">{{ item.title }}</h3>
          <div class="card-actions">
            <button @click="toggleStar(item)" :class="{ starred: item.is_starred }">
              {{ item.is_starred ? '⭐' : '☆' }}
            </button>
            <button @click="markRead(item)">{{ item.is_read ? '✓' : '○' }}</button>
          </div>
        </div>
        <div class="card-meta">
          <span class="author">{{ item.author || '匿名' }}</span>
          <span class="date">{{ formatDate(item.published) }}</span>
          <span class="feed">{{ getFeedName(item.feed_id) }}</span>
        </div>
        <p class="summary">{{ item.summary?.slice(0, 200) || '无摘要' }}...</p>
        <div class="card-footer">
          <button @click="doSummary(item)" :disabled="summarizing === item.id">
            🤖 {{ item.ai_summary ? '重新总结' : 'AI总结' }}
          </button>
          <button @click="doTranslate(item)" :disabled="translating === item.id">
            🌐 {{ item.translated_summary ? '重新翻译' : '翻译' }}
          </button>
          <a :href="item.link" target="_blank">🔗 阅读原文</a>
        </div>
        
        <!-- AI结果展示 -->
        <div v-if="item.ai_summary || item.translated_summary" class="ai-results">
          <div v-if="item.ai_summary" class="ai-box">
            <strong>🤖 AI总结：</strong>{{ item.ai_summary }}
          </div>
          <div v-if="item.translated_summary" class="ai-box">
            <strong>🌐 翻译：</strong>{{ item.translated_summary }}
          </div>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="selectedItem" class="modal" @click.self="selectedItem = null">
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ selectedItem.title }}</h2>
          <button @click="selectedItem = null">✕</button>
        </div>
        <div class="modal-body">
          <div class="modal-meta">
            <span>{{ selectedItem.author }}</span>
            <span>{{ formatDate(selectedItem.published) }}</span>
            <a :href="selectedItem.link" target="_blank">阅读原文 →</a>
          </div>
          <div class="content-body" v-html="selectedItem.content || selectedItem.summary"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from '../stores'
import { markRead as apiMarkRead, toggleStar as apiToggleStar, summarize as apiSummarize, translate as apiTranslate, fetchAllFeeds } from '../api'

const store = useAppStore()
const searchQuery = ref('')
const currentFeed = ref('')
const refreshing = ref(false)
const summarizing = ref(null)
const translating = ref(null)
const selectedItem = ref(null)
let searchTimer = null

onMounted(() => {
  store.loadFeeds()
  store.loadContents()
})

function debounceSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    store.searchQuery = searchQuery.value
    store.loadContents()
  }, 300)
}

async function refresh() {
  refreshing.value = true
  await store.refreshAll()
  refreshing.value = false
}

function getFeedName(feedId) {
  const feed = store.feeds.find(f => f.id === feedId)
  return feed?.name || '未知'
}

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN')
}

async function toggleStar(item) {
  await apiToggleStar(item.id)
  item.is_starred = !item.is_starred
}

async function markRead(item) {
  if (!item.is_read) {
    await apiMarkRead(item.id)
    item.is_read = true
  }
}

function openDetail(item) {
  markRead(item)
  selectedItem.value = item
}

async function doSummary(item) {
  summarizing.value = item.id
  const text = item.content || item.summary || item.title
  try {
    const res = await apiSummarize({ content_id: item.id, text, max_length: 200 })
    item.ai_summary = res.data.summary
  } catch (e) {
    alert('总结失败: ' + e.message)
  }
  summarizing.value = null
}

async function doTranslate(item) {
  translating.value = item.id
  const text = item.ai_summary || item.summary || item.title
  try {
    const res = await apiTranslate({ content_id: item.id, text, target_language: 'zh' })
    item.translated_summary = res.data.translated_text
  } catch (e) {
    alert('翻译失败: ' + e.message)
  }
  translating.value = null
}
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.search-input { flex: 1; min-width: 200px; padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
.filters { display: flex; gap: 8px; flex-wrap: wrap; }
.filters select, .filters button { padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; background: white; cursor: pointer; font-size: 13px; }
.filters button.active { background: #1a1a2e; color: white; }
.refresh-btn { background: #e94560 !important; color: white !important; border: none !important; }

.loading, .empty { text-align: center; padding: 40px; color: #999; }
.content-list { display: flex; flex-direction: column; gap: 12px; }

.content-card { background: white; border-radius: 12px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.content-card.unread { border-left: 3px solid #e94560; }

.card-header { display: flex; justify-content: space-between; align-items: start; gap: 12px; }
.card-header h3 { flex: 1; font-size: 16px; color: #1a1a2e; cursor: pointer; margin: 0; line-height: 1.4; }
.card-header h3:hover { color: #e94560; }

.card-actions { display: flex; gap: 6px; }
.card-actions button { background: none; border: none; font-size: 16px; cursor: pointer; padding: 4px; }
.card-actions button.starred { color: #f39c12; }

.card-meta { display: flex; gap: 12px; margin: 8px 0; font-size: 12px; color: #888; }
.card-meta .feed { color: #e94560; }

.summary { color: #666; font-size: 13px; line-height: 1.6; margin: 8px 0; }

.card-footer { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.card-footer button, .card-footer a { 
  padding: 6px 12px; border-radius: 6px; border: 1px solid #ddd; 
  background: #f8f8f8; font-size: 12px; cursor: pointer; text-decoration: none; color: #333;
}
.card-footer button:hover { background: #1a1a2e; color: white; border-color: #1a1a2e; }
.card-footer a { background: #e94560; color: white; border-color: #e94560; font-weight: 500; }
.card-footer a:hover { background: #d13a52; }

.ai-results { margin-top: 12px; display: flex; flex-direction: column; gap: 8px; }
.ai-box { background: #f0f7ff; border-radius: 8px; padding: 10px 14px; font-size: 13px; line-height: 1.6; }
.ai-box strong { color: #0066cc; }

.modal { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 200; padding: 20px; }
.modal-content { background: white; border-radius: 16px; max-width: 700px; width: 100%; max-height: 90vh; overflow: hidden; display: flex; flex-direction: column; }
.modal-header { padding: 16px 20px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
.modal-header h2 { font-size: 18px; margin: 0; }
.modal-header button { background: none; border: none; font-size: 20px; cursor: pointer; }
.modal-body { padding: 20px; overflow-y: auto; flex: 1; }
.modal-meta { display: flex; gap: 16px; margin-bottom: 16px; font-size: 13px; color: #888; }
.modal-meta a { color: #e94560; font-weight: 600; padding: 4px 10px; background: #fff0f2; border-radius: 4px; text-decoration: none; }
.modal-meta a:hover { background: #e94560; color: white; }
.content-body { line-height: 1.8; font-size: 14px; }
.content-body img { max-width: 100%; height: auto; }

@media (max-width: 640px) {
  .toolbar { flex-direction: column; }
  .filters { width: 100%; }
  .card-header h3 { font-size: 15px; }
}
</style>
