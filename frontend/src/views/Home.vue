<template>
  <div class="home-layout">
    <!-- 左侧：订阅来源目录 -->
    <aside class="feed-sidebar" v-if="store.feedStats.length">
      <div class="sidebar-header">
        <h4>📡 订阅来源</h4>
        <button class="sidebar-toggle" @click="sidebarCollapsed = !sidebarCollapsed">
          {{ sidebarCollapsed ? '▶' : '◀' }}
        </button>
      </div>
      <div class="sidebar-content" :class="{ collapsed: sidebarCollapsed }">
        <!-- 全部来源 -->
        <div 
          class="feed-source-item all" 
          :class="{ active: !store.currentFeed }"
          @click="store.setFeedFilter(null)"
        >
          <span class="source-name">📁 全部来源</span>
          <span class="source-counts">
            <span class="count-total">{{ store.stats.total }}</span>
            <span v-if="store.stats.unread" class="count-unread">{{ store.stats.unread }}</span>
          </span>
        </div>
        <!-- 各来源列表 -->
        <div 
          v-for="stat in store.feedStats" 
          :key="stat.id"
          class="feed-source-item"
          :class="{ active: store.currentFeed === stat.id }"
          @click="store.setFeedFilter(stat.id)"
        >
          <div class="source-info">
            <span class="source-icon">{{ typeIcon(stat.type) }}</span>
            <span class="source-name">{{ stat.name }}</span>
            <!-- 标签 -->
            <span v-if="stat.tags" class="source-tags">
              <span v-for="tag in statTags(stat.tags)" :key="tag" class="mini-tag">{{ tag }}</span>
            </span>
          </div>
          <span class="source-counts">
            <span class="count-total">{{ stat.article_count || 0 }}</span>
            <span v-if="stat.unread_count" class="count-unread">{{ stat.unread_count }}</span>
          </span>
        </div>
      </div>
    </aside>

    <!-- 右侧：内容区域 -->
    <main class="home-main">
    <!-- 统计卡片 -->
    <div class="stats-bar" v-if="store.stats">
      <div class="stat-card">
        <div class="stat-num">{{ store.stats.unread }}</div>
        <div class="stat-label">未读</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{{ store.stats.starred }}</div>
        <div class="stat-label">收藏</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{{ store.stats.today }}</div>
        <div class="stat-label">今日新增</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{{ store.stats.total }}</div>
        <div class="stat-label">总计</div>
      </div>
    </div>

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
        <select v-model="dateFilter" @change="store.setDateRange(dateFilter)">
          <option value="">全部时间</option>
          <option value="today">📅 今天</option>
          <option value="week">📅 最近7天</option>
          <option value="month">📅 最近30天</option>
        </select>
        <button @click="store.filterStarred = store.filterStarred === null ? true : null; store.loadContents()" 
                :class="{ active: store.filterStarred }">⭐</button>
        <button @click="store.filterRead = store.filterRead === null ? false : null; store.loadContents()" 
                :class="{ active: store.filterRead === false }">📖 未读</button>
        <button @click="clearFilters" title="清除所有过滤">🧹</button>
        <button @click="refresh" :disabled="refreshing" class="refresh-btn">
          {{ refreshing ? '🔄 抓取中...' : '🔄 全部抓取' }}
        </button>
      </div>
    </div>

    <!-- 内容列表 -->
    <div v-if="store.loading" class="loading">加载中...</div>
    <div v-else-if="store.contents.length === 0" class="empty">
      {{ store.searchQuery ? '没有匹配的结果' : '暂无内容，先去添加订阅吧！' }}
    </div>
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
          <!-- 阅读进度条 -->
          <span v-if="item.read_progress > 0 && item.read_progress < 100" class="progress-badge">
            {{ Math.round(item.read_progress) }}%
          </span>
        </div>
        <p class="summary">{{ item.summary?.slice(0, 200) || '无摘要' }}...</p>
        
        <!-- 标签管理 -->
        <div class="tags-row" v-if="item.tags || editingTags === item.id">
          <div v-if="editingTags !== item.id" class="tags-display">
            <span v-for="tag in parseTags(item.tags)" :key="tag" class="tag-chip" @click="filterByTag(tag)">
              {{ tag }}
            </span>
            <button class="tag-edit-btn" @click="startEditTags(item)">✏️</button>
          </div>
          <div v-else class="tags-edit">
            <input 
              v-model="tagInput" 
              @keyup.enter="saveTags(item)"
              @blur="saveTags(item)"
              placeholder="输入标签，用逗号分隔"
              class="tag-input"
              ref="tagInputRef"
              autofocus
            />
          </div>
        </div>
        <div v-else class="tags-row">
          <button class="tag-add-btn" @click="startEditTags(item)">+ 添加标签</button>
        </div>

        <div class="card-footer">
          <button @click="doSummary(item, 'short')" :disabled="summarizing === item.id" :class="{ active: item.ai_summary_short }">📋 短</button>
          <button @click="doSummary(item, 'medium')" :disabled="summarizing === item.id" :class="{ active: item.ai_summary }">📝 中</button>
          <button @click="doSummary(item, 'long')" :disabled="summarizing === item.id" :class="{ active: item.ai_summary_long }">📖 长</button>
          <button @click="doTranslate(item)" :disabled="translating === item.id">
            🌐 {{ item.translated_summary ? '重新翻译' : '翻译' }}
          </button>
          <button @click="doTTS(item)" :disabled="ttsLoading === item.id" :class="{ playing: playingAudio === item.id }">
            🔊 {{ playingAudio === item.id ? '播放中' : (item.tts_url ? '朗读' : '生成语音') }}
          </button>
          <a :href="item.link" target="_blank">🔗 阅读原文</a>
        </div>
        
        <!-- TTS音频播放器 -->
        <div v-if="item.tts_url" class="tts-player">
          <audio :src="item.tts_url" controls @play="playingAudio = item.id" @pause="playingAudio = null" @ended="playingAudio = null"></audio>
        </div>
        
        <!-- AI结果展示 -->
        <div v-if="item.ai_summary || item.ai_summary_short || item.ai_summary_long || item.translated_summary" class="ai-results">
          <div v-if="item.ai_summary_short" class="ai-box short">
            <strong>📋 短摘要：</strong>{{ item.ai_summary_short }}
          </div>
          <div v-if="item.ai_summary" class="ai-box medium">
            <strong>📝 中摘要：</strong>{{ item.ai_summary }}
          </div>
          <div v-if="item.ai_summary_long" class="ai-box long">
            <strong>📖 长摘要：</strong>{{ item.ai_summary_long }}
          </div>
          <div v-if="item.translated_summary" class="ai-box translate">
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
            <button @click="doTTS(selectedItem)" :disabled="ttsLoading === selectedItem.id" class="modal-tts-btn">
              🔊 {{ selectedItem.tts_url ? '朗读' : '生成语音' }}
            </button>
            <a :href="selectedItem.link" target="_blank">阅读原文 →</a>
          </div>
          <div v-if="selectedItem.tts_url" class="tts-player-modal">
            <audio :src="selectedItem.tts_url" controls style="width:100%"></audio>
          </div>
          <!-- 原文对照翻译 -->
          <div v-if="selectedItem.translated_summary" class="bilingual-box">
            <div class="original">
              <h4>📝 原文</h4>
              <p>{{ selectedItem.summary || selectedItem.content || '无原文' }}</p>
            </div>
            <div class="translated">
              <h4>🌐 译文</h4>
              <p>{{ selectedItem.translated_summary }}</p>
            </div>
          </div>
          <div v-else class="content-body" v-html="selectedItem.content || selectedItem.summary"></div>
        </div>
      </div>
    </div>
  </main>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useAppStore } from '../stores'
import { markRead as apiMarkRead, toggleStar as apiToggleStar, updateContent, summarize as apiSummarize, translate as apiTranslate, fetchAllFeeds, generateTTS as apiGenerateTTS } from '../api'

const store = useAppStore()
const searchQuery = ref('')
const currentFeed = ref('')
const dateFilter = ref('')
const refreshing = ref(false)
const summarizing = ref(null)
const translating = ref(null)
const ttsLoading = ref(null)
const playingAudio = ref(null)
const selectedItem = ref(null)
const editingTags = ref(null)
const tagInput = ref('')
const tagInputRef = ref(null)
const sidebarCollapsed = ref(false)
let searchTimer = null

onMounted(() => {
  store.loadInitData()
})

function debounceSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    store.searchQuery = searchQuery.value
    store.loadContents()
  }, 300)
}

function clearFilters() {
  searchQuery.value = ''
  currentFeed.value = ''
  dateFilter.value = ''
  store.clearFilters()
}

async function refresh() {
  refreshing.value = true
  await store.refreshAll()
  refreshing.value = false
}

function getFeedName(feedId) {
  return store.feedNameMap[feedId] || '未知'
}

function formatDate(date) {
}

function typeIcon(type) {
  const icons = {
    rss: '📰',
    podcast: '🎙️',
    wechat_search: '📱',
    weibo_search: '📝'
  }
  return icons[type] || '📄'
}

function statTags(tagsStr) {
  if (!tagsStr) return []
  return tagsStr.split(',').map(t => t.trim()).filter(t => t)
}

function parseTags(tagsStr) {
  if (!tagsStr) return []
  return tagsStr.split(',').map(t => t.trim()).filter(t => t)
}

// 标签管理
function startEditTags(item) {
  editingTags.value = item.id
  tagInput.value = item.tags || ''
  nextTick(() => {
    if (tagInputRef.value) tagInputRef.value.focus()
  })
}

async function saveTags(item) {
  const tags = tagInput.value.trim()
  await updateContent(item.id, { tags })
  item.tags = tags
  editingTags.value = null
  tagInput.value = ''
}

function filterByTag(tag) {
  // 可以扩展为点击标签过滤
  searchQuery.value = tag
  store.searchQuery = tag
  store.loadContents()
}

async function toggleStar(item) {
  await apiToggleStar(item.id)
  item.is_starred = !item.is_starred
  store.loadStats()
}

async function markRead(item) {
  if (!item.is_read) {
    await apiMarkRead(item.id)
    item.is_read = true
    item.read_progress = 100
    store.loadStats()
  }
}

function openDetail(item) {
  markRead(item)
  selectedItem.value = item
}

async function doSummary(item, length = 'medium') {
  summarizing.value = item.id
  const text = item.content || item.summary || item.title
  try {
    const res = await apiSummarize({ content_id: item.id, text, length })
    if (length === 'short') item.ai_summary_short = res.data.summary
    else if (length === 'long') item.ai_summary_long = res.data.summary
    else item.ai_summary = res.data.summary
  } catch (e) {
    alert('总结失败: ' + e.message)
  }
  summarizing.value = null
}

async function doTTS(item) {
  if (item.tts_url) {
    // 已有音频，直接播放
    const audio = document.querySelector(`audio[src="${item.tts_url}"]`)
    if (audio) {
      audio.play()
    }
    return
  }
  
  ttsLoading.value = item.id
  const text = item.content || item.summary || item.title
  try {
    const res = await apiGenerateTTS({ text })
    item.tts_url = res.data.audio_url
  } catch (e) {
    alert('语音生成失败: ' + e.message)
  }
  ttsLoading.value = null
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
/* 统计卡片 */
.stats-bar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.stat-card { background: white; border-radius: 10px; padding: 12px 20px; text-align: center; min-width: 80px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
.stat-num { font-size: 22px; font-weight: bold; color: #e94560; }
.stat-label { font-size: 11px; color: #888; margin-top: 2px; }

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

.card-meta { display: flex; gap: 12px; margin: 8px 0; font-size: 12px; color: #888; align-items: center; }
.card-meta .feed { color: #e94560; }
.progress-badge { background: #f0f7ff; color: #0066cc; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }

.summary { color: #666; font-size: 13px; line-height: 1.6; margin: 8px 0; }

/* 标签 */
.tags-row { margin: 8px 0; }
.tags-display { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.tag-chip { background: #f0f0f5; color: #555; padding: 3px 10px; border-radius: 12px; font-size: 12px; cursor: pointer; transition: background 0.2s; }
.tag-chip:hover { background: #e94560; color: white; }
.tag-edit-btn, .tag-add-btn { background: none; border: none; font-size: 13px; cursor: pointer; padding: 3px 6px; color: #999; }
.tag-edit-btn:hover, .tag-add-btn:hover { color: #e94560; }
.tags-edit { display: flex; }
.tag-input { flex: 1; padding: 6px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; }

.card-footer { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.card-footer button, .card-footer a { 
  padding: 6px 12px; border-radius: 6px; border: 1px solid #ddd; 
  background: #f8f8f8; font-size: 12px; cursor: pointer; text-decoration: none; color: #333;
}
.card-footer button:hover { background: #1a1a2e; color: white; border-color: #1a1a2e; }
.card-footer a { background: #e94560; color: white; border-color: #e94560; font-weight: 500; }
.card-footer a:hover { background: #d13a52; }

.ai-results { margin-top: 12px; display: flex; flex-direction: column; gap: 8px; }
.ai-box { border-radius: 8px; padding: 10px 14px; font-size: 13px; line-height: 1.6; }
.ai-box strong { font-weight: 600; }
.ai-box.short { background: #e8f5e9; }
.ai-box.short strong { color: #2e7d32; }
.ai-box.medium { background: #e3f2fd; }
.ai-box.medium strong { color: #1565c0; }
.ai-box.long { background: #fff3e0; }
.ai-box.long strong { color: #e65100; }
.ai-box.translate { background: #fce4ec; }
.ai-box.translate strong { color: #c2185b; }

/* 原文对照 */
.bilingual-box { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 12px; }
.bilingual-box .original, .bilingual-box .translated { padding: 16px; border-radius: 8px; }
.bilingual-box .original { background: #f5f5f5; }
.bilingual-box .translated { background: #e8f5e9; }
.bilingual-box h4 { margin: 0 0 8px 0; font-size: 14px; color: #666; }
.bilingual-box p { margin: 0; line-height: 1.6; font-size: 14px; }
@media (max-width: 600px) {
  .bilingual-box { grid-template-columns: 1fr; }
}

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

/* TTS播放器 */
.tts-player { margin-top: 10px; padding: 8px 12px; background: #f8f9fa; border-radius: 8px; }
.tts-player audio { width: 100%; height: 36px; }
.tts-player-modal { margin: 12px 0; padding: 10px; background: #f0f7ff; border-radius: 8px; }
.modal-tts-btn { background: #1a1a2e; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; }
.modal-tts-btn:hover { background: #e94560; }
.modal-tts-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.card-footer button.playing { background: #1a1a2e; color: white; border-color: #1a1a2e; animation: pulse 1.5s infinite; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* === 侧边栏：订阅来源目录 === */
.home-layout { display: flex; gap: 16px; min-height: 100vh; }
.feed-sidebar { width: 240px; min-width: 240px; background: white; border-radius: 12px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); align-self: flex-start; position: sticky; top: 70px; max-height: calc(100vh - 90px); overflow-y: auto; }
.feed-sidebar::-webkit-scrollbar { width: 4px; }
.feed-sidebar::-webkit-scrollbar-thumb { background: #ddd; border-radius: 4px; }
.sidebar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
.sidebar-header h4 { margin: 0; font-size: 14px; color: #1a1a2e; }
.sidebar-toggle { background: none; border: none; font-size: 12px; cursor: pointer; color: #999; padding: 2px 6px; }
.sidebar-toggle:hover { color: #e94560; }
.sidebar-content.collapsed { display: none; }
.feed-source-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s; margin-bottom: 4px; }
.feed-source-item:hover { background: #f5f5f5; }
.feed-source-item.active { background: #e94560; color: white; }
.feed-source-item.active .source-name { color: white; }
.feed-source-item.active .count-total { color: rgba(255,255,255,0.8); }
.feed-source-item.active .count-unread { background: white; color: #e94560; }
.feed-source-item.active .mini-tag { background: rgba(255,255,255,0.2); color: white; }
.feed-source-item.all { font-weight: 600; background: #f8f9fa; border: 1px solid #eee; }
.feed-source-item.all:hover { background: #eee; }
.source-info { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0; }
.source-icon { font-size: 14px; flex-shrink: 0; }
.source-name { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #333; }
.source-tags { display: flex; gap: 4px; flex-shrink: 0; }
.mini-tag { font-size: 10px; padding: 1px 6px; border-radius: 8px; background: #f0f0f5; color: #666; }
.source-counts { display: flex; gap: 6px; align-items: center; flex-shrink: 0; }
.count-total { font-size: 12px; color: #888; }
.count-unread { font-size: 11px; padding: 1px 6px; border-radius: 10px; background: #e94560; color: white; font-weight: 600; }
.home-main { flex: 1; min-width: 0; }

@media (max-width: 768px) {
  .home-layout { flex-direction: column; }
  .feed-sidebar { width: 100%; min-width: auto; position: static; max-height: none; }
  .sidebar-content { display: flex; flex-wrap: wrap; gap: 4px; }
  .feed-source-item { flex: 1; min-width: 140px; }
  .toolbar { flex-direction: column; }
  .filters { width: 100%; }
  .stats-bar { justify-content: space-between; }
  .stat-card { min-width: 70px; padding: 8px 12px; }
  .stat-num { font-size: 18px; }
  .card-header h3 { font-size: 15px; }
}
</style>
