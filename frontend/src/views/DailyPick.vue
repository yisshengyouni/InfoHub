<template>
  <div class="daily-pick-page">
    <div class="header">
      <h2>🏆 每日精选</h2>
      <button class="btn btn-primary" @click="doGenerate" :disabled="generating">
        {{ generating ? '🔄 生成中...' : '✨ 生成今日精选' }}
      </button>
    </div>

    <!-- 今日精选 -->
    <div v-if="todayPick" class="today-section">
      <div class="today-header">
        <span class="today-badge">今日</span>
        <span class="today-title">{{ todayPick.title }}</span>
        <span class="today-meta">{{ todayPick.article_count }} 篇文章</span>
      </div>
      <div v-if="todayArticles.length" class="article-list">
        <div v-for="article in todayArticles" :key="article.id" class="article-card" :class="{ unread: !article.is_read }">
          <div class="article-header">
            <h3 @click="openDetail(article)">{{ article.title }}</h3>
            <div class="article-actions">
              <button @click="toggleStar(article)" :class="{ starred: article.is_starred }">
                {{ article.is_starred ? '⭐' : '☆' }}
              </button>
            </div>
          </div>
          <div class="article-meta">
            <span class="author">{{ article.author || '匿名' }}</span>
            <span class="feed">{{ getFeedName(article.feed_id) }}</span>
            <span class="date">{{ formatDate(article.published) }}</span>
          </div>
          <p class="summary">{{ article.summary?.slice(0, 150) || '无摘要' }}...</p>
          <div class="article-footer">
            <button @click="doSummary(article, 'short')">🤖 短摘要</button>
            <button @click="doSummary(article, 'medium')">🤖 中摘要</button>
            <button @click="doSummary(article, 'long')">🤖 长摘要</button>
            <button @click="doTranslate(article)">🌐 翻译</button>
            <a :href="article.link" target="_blank">🔗 阅读原文</a>
          </div>
          <!-- AI结果 -->
          <div v-if="article.ai_summary || article.ai_summary_short || article.ai_summary_long || article.translated_summary" class="ai-results">
            <div v-if="article.ai_summary_short" class="ai-box short">
              <strong>📋 短摘要：</strong>{{ article.ai_summary_short }}
            </div>
            <div v-if="article.ai_summary" class="ai-box medium">
              <strong>📝 中摘要：</strong>{{ article.ai_summary }}
            </div>
            <div v-if="article.ai_summary_long" class="ai-box long">
              <strong>📖 长摘要：</strong>{{ article.ai_summary_long }}
            </div>
            <div v-if="article.translated_summary" class="ai-box translate">
              <strong>🌐 翻译：</strong>{{ article.translated_summary }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 历史精选 -->
    <div class="history-section">
      <h3>📅 历史精选</h3>
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="history.length === 0" class="empty">暂无历史精选</div>
      <div v-else class="history-list">
        <div v-for="pick in history" :key="pick.id" class="history-item" @click="loadPickArticles(pick.date)">
          <div class="history-date">{{ pick.date }}</div>
          <div class="history-title">{{ pick.title }}</div>
          <div class="history-count">{{ pick.article_count }} 篇</div>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from '../stores'
import {
  getTodayPick, getPickArticles, getDailyPicks, generateDailyPick,
  toggleStar as apiToggleStar, markRead as apiMarkRead,
  summarize as apiSummarize, translate as apiTranslate
} from '../api'

const store = useAppStore()
const todayPick = ref(null)
const todayArticles = ref([])
const history = ref([])
const loading = ref(false)
const generating = ref(false)
const selectedItem = ref(null)

onMounted(() => {
  loadToday()
  loadHistory()
})

async function loadToday() {
  try {
    const res = await getTodayPick()
    todayPick.value = res.data
    if (todayPick.value) {
      const articlesRes = await getPickArticles(todayPick.value.date)
      todayArticles.value = articlesRes.data.articles || []
    }
  } catch (e) {
    // 今天没生成，静默
  }
}

async function loadHistory() {
  loading.value = true
  try {
    const res = await getDailyPicks({ limit: 14 })
    history.value = (res.data || []).filter(p => p.date !== todayPick.value?.date)
  } catch (e) {
    console.error('loadHistory', e)
  }
  loading.value = false
}

async function doGenerate() {
  generating.value = true
  try {
    await generateDailyPick()
    await loadToday()
    await loadHistory()
  } catch (e) {
    alert('生成失败: ' + e.message)
  }
  generating.value = false
}

async function loadPickArticles(date) {
  try {
    const res = await getPickArticles(date)
    todayPick.value = { date, title: res.data.date + ' 精选', article_count: res.data.count }
    todayArticles.value = res.data.articles || []
  } catch (e) {
    alert('加载失败')
  }
}

function getFeedName(feedId) {
  return store.feedNameMap[feedId] || '未知'
}

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN')
}

async function toggleStar(item) {
  await apiToggleStar(item.id)
  item.is_starred = !item.is_starred
}

async function openDetail(item) {
  if (!item.is_read) {
    await apiMarkRead(item.id)
    item.is_read = true
  }
  selectedItem.value = item
}

async function doSummary(item, length) {
  const text = item.content || item.summary || item.title
  try {
    const res = await apiSummarize({ content_id: item.id, text, length })
    if (length === 'short') item.ai_summary_short = res.data.summary
    else if (length === 'long') item.ai_summary_long = res.data.summary
    else item.ai_summary = res.data.summary
  } catch (e) {
    alert('总结失败: ' + e.message)
  }
}

async function doTranslate(item) {
  const text = item.ai_summary || item.summary || item.title
  try {
    const res = await apiTranslate({ content_id: item.id, text, target_language: 'zh' })
    item.translated_summary = res.data.translated_text
  } catch (e) {
    alert('翻译失败: ' + e.message)
  }
}
</script>

<style scoped>
.daily-pick-page { padding-bottom: 40px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header h2 { margin: 0; font-size: 22px; }
.btn { padding: 8px 16px; border-radius: 6px; border: 1px solid #ddd; background: white; cursor: pointer; font-size: 13px; }
.btn-primary { background: #e94560; color: white; border: none; }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }

.today-section { margin-bottom: 30px; }
.today-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding: 12px 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; }
.today-badge { background: rgba(255,255,255,0.2); padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; }
.today-title { font-size: 16px; font-weight: bold; flex: 1; }
.today-meta { font-size: 13px; opacity: 0.9; }

.article-list { display: flex; flex-direction: column; gap: 12px; }
.article-card { background: white; border-radius: 10px; padding: 16px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
.article-card.unread { border-left: 3px solid #e94560; }
.article-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.article-header h3 { margin: 0; font-size: 16px; cursor: pointer; flex: 1; }
.article-header h3:hover { color: #667eea; }
.article-actions button { background: none; border: none; font-size: 18px; cursor: pointer; padding: 4px; }
.article-actions button.starred { color: #f39c12; }
.article-meta { display: flex; gap: 12px; font-size: 12px; color: #888; margin: 6px 0; }
.summary { color: #666; font-size: 14px; line-height: 1.5; margin: 8px 0; }
.article-footer { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.article-footer button, .article-footer a { padding: 6px 12px; border-radius: 4px; border: 1px solid #ddd; background: #f8f9fa; cursor: pointer; font-size: 12px; text-decoration: none; color: #333; }
.article-footer button:hover { background: #e9ecef; }

.ai-results { margin-top: 12px; padding-top: 12px; border-top: 1px solid #eee; }
.ai-box { padding: 10px; border-radius: 6px; margin-bottom: 8px; font-size: 13px; line-height: 1.5; }
.ai-box.short { background: #e8f5e9; }
.ai-box.medium { background: #e3f2fd; }
.ai-box.long { background: #fff3e0; }
.ai-box.translate { background: #fce4ec; }

.history-section h3 { margin-bottom: 12px; }
.history-list { display: flex; flex-direction: column; gap: 8px; }
.history-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: white; border-radius: 8px; cursor: pointer; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.history-item:hover { background: #f8f9fa; }
.history-date { font-weight: bold; color: #667eea; min-width: 90px; }
.history-title { flex: 1; font-size: 14px; }
.history-count { font-size: 12px; color: #888; background: #f0f0f0; padding: 2px 8px; border-radius: 10px; }

.loading, .empty { text-align: center; padding: 40px; color: #999; }

/* 弹窗 */
.modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 200; padding: 20px; }
.modal-content { background: white; border-radius: 12px; max-width: 700px; width: 100%; max-height: 80vh; overflow: hidden; display: flex; flex-direction: column; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #eee; }
.modal-header h2 { margin: 0; font-size: 18px; }
.modal-header button { background: none; border: none; font-size: 20px; cursor: pointer; }
.modal-body { padding: 20px; overflow-y: auto; flex: 1; }
.modal-meta { display: flex; gap: 16px; font-size: 13px; color: #888; margin-bottom: 16px; }
.modal-meta a { color: #667eea; }
.content-body { line-height: 1.8; font-size: 15px; }

/* 原文对照 */
.bilingual-box { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 12px; }
.bilingual-box .original, .bilingual-box .translated { padding: 16px; border-radius: 8px; }
.bilingual-box .original { background: #f5f5f5; }
.bilingual-box .translated { background: #e8f5e9; }
.bilingual-box h4 { margin: 0 0 8px 0; font-size: 14px; color: #666; }
.bilingual-box p { margin: 0; line-height: 1.6; font-size: 14px; }
@media (max-width: 600px) {
  .bilingual-box { grid-template-columns: 1fr; }
  .header { flex-direction: column; gap: 12px; align-items: flex-start; }
}
</style>
