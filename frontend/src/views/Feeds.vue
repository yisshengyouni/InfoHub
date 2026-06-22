<template>
  <div class="feeds-page">
    <div class="feeds-header">
      <h2>📡 订阅源管理</h2>
      <div class="header-actions">
        <button class="btn" @click="handleExportOPML" title="导出 OPML">📤 导出</button>
        <button class="btn" @click="showImportModal = true" title="导入 OPML">📥 导入</button>
        <button class="btn btn-primary" @click="showModal = true">+ 添加订阅</button>
      </div>
    </div>

    <div class="feed-list">
      <div v-for="feed in feeds" :key="feed.id" class="feed-card">
        <div class="feed-info">
          <div class="feed-name">{{ feed.name }}</div>
          <div class="feed-meta">
            <span class="feed-type" :class="feed.type">{{ typeLabel(feed.type) }}</span>
            <span class="feed-category">{{ feed.category }}</span>
            <span v-if="feed.last_fetched" class="feed-time">
              更新: {{ formatDate(feed.last_fetched) }}
            </span>
          </div>
          <div class="feed-url">{{ feed.url }}</div>
          <!-- 标签显示/编辑 -->
          <div class="feed-tags-row" v-if="feed.tags || editingFeedId === feed.id">
            <div v-if="editingFeedId !== feed.id" class="tags-display">
              <span v-for="tag in parseTags(feed.tags)" :key="tag" class="mini-tag">{{ tag }}</span>
              <button class="tag-edit-btn" @click="startEditTags(feed)">✏️</button>
              <button class="tag-auto-btn" @click="doAutoTag(feed.id)" title="自动标签">🔄</button>
            </div>
            <div v-else class="tags-edit">
              <input 
                v-model="tagInput" 
                @keyup.enter="saveTags(feed.id)"
                @blur="saveTags(feed.id)"
                placeholder="标签用逗号分隔"
                class="tag-input"
                ref="tagInputRef"
                autofocus
              />
            </div>
          </div>
          <div v-else class="feed-tags-row">
            <button class="tag-add-btn" @click="startEditTags(feed)">+ 添加标签</button>
          </div>
        </div>
        <div class="feed-actions">
          <button class="btn btn-small" @click="doFetch(feed.id)">🔄 抓取</button>
          <button class="btn btn-small btn-danger" @click="doDelete(feed.id)">🗑️</button>
        </div>
      </div>
    </div>

    <!-- Add Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <h3>添加订阅源</h3>
        
        <div class="form-group">
          <label>平台类型</label>
          <select v-model="newFeed.type" class="form-control">
            <option value="rss">📰 RSS / Atom（博客/新闻）</option>
            <option value="podcast">🎙️ 播客 RSS（小宇宙/苹果播客/Spotify）</option>
            <option value="wechat_search">📱 微信公众号（搜狗搜索）</option>
            <option value="weibo_search">📝 微博搜索</option>
            <option value="douyin">🎵 抖音 (RSSHub)</option>
            <option value="xiaohongshu">📕 小红书 (RSSHub)</option>
          </select>
          <div class="type-hint">{{ typeHint }}</div>
        </div>

        <div class="form-group">
          <label>名称</label>
          <input v-model="newFeed.name" class="form-control" placeholder="给这个订阅起个名字" />
        </div>

        <div class="form-group">
          <label>{{ urlLabel }}</label>
          <input v-model="newFeed.url" class="form-control" :placeholder="urlPlaceholder" />
        </div>

        <!-- Podcast Search -->
        <div v-if="newFeed.type === 'podcast' && newFeed.url.length >= 2" class="search-box">
          <button class="btn btn-small" @click="searchPodcast" :disabled="searching">
            {{ searching ? '搜索中...' : '🔍 iTunes搜索播客' }}
          </button>
          <div v-if="podcastResults.length" class="search-results">
            <div v-for="pod in podcastResults" :key="pod.podcast_id" class="search-item" @click="selectPodcast(pod)">
              <img v-if="pod.cover" :src="pod.cover" class="podcast-cover" />
              <div class="podcast-info">
                <div class="podcast-name">{{ pod.name }}</div>
                <div class="podcast-artist">{{ pod.artist }} · {{ pod.track_count }}期 · {{ pod.genre }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- WeChat Search -->
        <div v-if="newFeed.type === 'wechat_search' && newFeed.url.length >= 2" class="search-box">
          <button class="btn btn-small" @click="searchWechat" :disabled="searching">
            {{ searching ? '搜索中...' : '🔍 搜索公众号' }}
          </button>
          <div v-if="wechatResults.length" class="search-results">
            <div v-for="acc in wechatResults" :key="acc.name + acc.source" 
                 class="search-item" 
                 :class="{ 'is-rss': acc.source === 'wechat2rss' }"
                 @click="selectWechat(acc)">
              <div class="wechat-info">
                <div class="wechat-name">{{ acc.name }}
                  <span class="source-tag" :class="acc.source">{{ acc.source === 'wechat2rss' ? '🔥 全文RSS' : '📝 搜狗摘要' }}</span>
                </div>
                <div class="wechat-desc">{{ acc.description }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- RSSHub Guide -->
        <div v-if="['weibo_search', 'douyin', 'xiaohongshu'].includes(newFeed.type)" class="rsshub-guide">
          <h4>💡 RSSHub 辅助工具</h4>
          <p class="guide-desc">对于微博、抖音、小红书等平台，建议使用 <a href="https://docs.rsshub.app" target="_blank">RSSHub</a> 生成标准 RSS 链接。</p>
          <div class="guide-inputs">
            <input v-model="rsshubId" class="form-control guide-input" placeholder="输入用户ID (如微博UID)" />
            <button class="btn btn-small guide-btn" @click="generateRssHubLink">生成订阅链接</button>
          </div>
          <p class="guide-note" v-if="newFeed.type === 'weibo_search'">示例链接：https://rsshub.app/weibo/user/123456</p>
        </div>

        <div class="form-group">
          <label>分类</label>
          <input v-model="newFeed.category" class="form-control" placeholder="如：科技新闻" />
        </div>

        <div class="modal-actions">
          <button class="btn" @click="showModal = false">取消</button>
          <button class="btn btn-primary" @click="doCreate" :disabled="saving">
            {{ saving ? '保存中...' : '添加' }}
          </button>
        </div>
      </div>
    </div>

    <!-- OPML Import Modal -->
    <div v-if="showImportModal" class="modal-overlay" @click.self="showImportModal = false">
      <div class="modal">
        <h3>📥 导入 OPML</h3>
        <div class="form-group">
          <label>粘贴 OPML XML 内容</label>
          <textarea v-model="opmlContent" class="form-control" rows="8" placeholder="&lt;?xml version=&quot;1.0&quot;?&gt;
&lt;opml version=&quot;2.0&quot;&gt;
  &lt;head&gt;&lt;title&gt;我的订阅&lt;/title&gt;&lt;/head&gt;
  &lt;body&gt;
    &lt;outline type=&quot;rss&quot; text=&quot;示例博客&quot; xmlUrl=&quot;https://example.com/feed.xml&quot; /&gt;
  &lt;/body&gt;
&lt;/opml&gt;

或者粘贴 Inoreader / Feedly / 其他 RSS 阅读器的 OPML 导出内容"></textarea>
        </div>
        <div v-if="importResult" class="import-result" :class="{ success: importResult.added > 0, error: importResult.errors?.length }">
          <div v-if="importResult.added > 0">✅ 成功导入 {{ importResult.added }} 个订阅</div>
          <div v-if="importResult.skipped > 0">⚠️ {{ importResult.skipped }} 个已存在，跳过</div>
          <div v-if="importResult.errors?.length" class="import-errors">
            <div v-for="err in importResult.errors" :key="err.name">❌ {{ err.name }}: {{ err.error }}</div>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn" @click="showImportModal = false">取消</button>
          <button class="btn btn-primary" @click="doImportOPML" :disabled="importing || !opmlContent.trim()">
            {{ importing ? '导入中...' : '导入' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { getFeeds, createFeed as apiCreateFeed, deleteFeed as apiDeleteFeed, fetchFeed as apiFetchFeed, searchPodcast as apiSearchPodcast, searchWechat as apiSearchWechat, importOPMLFile, exportOPML, updateFeedTags, autoTagFeed } from '../api'

const feeds = ref([])
const showModal = ref(false)
const showImportModal = ref(false)
const saving = ref(false)
const searching = ref(false)
const podcastResults = ref([])
const wechatResults = ref([])

// 标签编辑
const editingFeedId = ref(null)
const tagInput = ref('')

// OPML
const opmlContent = ref('')
const importing = ref(false)
const importResult = ref(null)

const rsshubId = ref('')

const newFeed = ref({
  name: '',
  url: '',
  type: 'rss',
  category: '默认'
})

const typeHints = {
  rss: '支持任意 RSS/Atom 订阅源：博客、新闻网站、知乎专栏、第三方RSS桥接等',
  podcast: '输入播客名称搜索，或粘贴 RSS 链接直接订阅',
  wechat_search: '输入公众号名称。优先使用 Wechat2RSS 全文订阅（收录300+公众号），未收录则回退搜狗搜索',
  weibo_search: '输入微博用户昵称或搜索关键词',
  douyin: '需要使用 RSSHub 提供订阅链接，例如 https://rsshub.app/douyin/user/:uid',
  xiaohongshu: '需要使用 RSSHub 提供订阅链接，例如 https://rsshub.app/xiaohongshu/user/:user_id'
}

const urlLabels = {
  rss: 'RSS 链接',
  podcast: 'RSS 链接 或 播客名称',
  wechat_search: '公众号名称',
  weibo_search: '微博昵称/关键词',
  douyin: 'RSSHub 抖音链接',
  xiaohongshu: 'RSSHub 小红书链接'
}

const urlPlaceholders = {
  rss: 'https://example.com/feed.xml',
  podcast: '搜索播客名称或粘贴 RSS 链接',
  wechat_search: '如：36氪、阮一峰的网络日志',
  weibo_search: '如：央视新闻。提示：微博反爬严格，建议通过 RSSHub 获取 RSS 链接后直接作为 RSS 订阅',
  douyin: '如：https://rsshub.app/douyin/user/MS4wLjABAAAA...',
  xiaohongshu: '如：https://rsshub.app/xiaohongshu/user/5c1a16620000000007011d8c'
}

const typeHint = computed(() => typeHints[newFeed.value.type] || '')
const urlLabel = computed(() => urlLabels[newFeed.value.type] || '链接')
const urlPlaceholder = computed(() => urlPlaceholders[newFeed.value.type] || '')

function typeLabel(type) {
  const map = {
    rss: 'RSS',
    podcast: '播客',
    wechat_search: '公众号',
    weibo_search: '微博',
    douyin: '抖音',
    xiaohongshu: '小红书'
  }
  return map[type] || type
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

async function loadFeeds() {
  const res = await getFeeds()
  feeds.value = res.data
}

async function doCreate() {
  saving.value = true
  try {
    let url = newFeed.value.url.trim()
    let type = newFeed.value.type
    
    // 处理协议前缀
    if (type === 'wechat_search' && !url.startsWith('http') && !url.startsWith('wechat://')) {
      url = 'wechat://' + url
    }
    if (type === 'weibo_search' && !url.startsWith('http') && !url.startsWith('weibo://')) {
      url = 'weibo://' + url
    }
    
    await apiCreateFeed({
      name: newFeed.value.name,
      url: url,
      type: type,
      category: newFeed.value.category
    })
    showModal.value = false
    newFeed.value = { name: '', url: '', type: 'rss', category: '默认' }
    podcastResults.value = []
    wechatResults.value = []
    await loadFeeds()
  } catch (e) {
    alert(e.response?.data?.detail || '添加失败')
  }
  saving.value = false
}

async function doDelete(id) {
  if (!confirm('确定删除此订阅源？')) return
  await apiDeleteFeed(id)
  await loadFeeds()
}

async function doFetch(id) {
  const res = await apiFetchFeed(id)
  alert(`抓取完成！新条目: ${res.data.new_items || 0}`)
  if (res.data.error) {
    alert('错误: ' + res.data.error)
  }
}

// === 标签管理 ===
function parseTags(tagsStr) {
  if (!tagsStr) return []
  return tagsStr.split(',').map(t => t.trim()).filter(t => t)
}

function startEditTags(feed) {
  editingFeedId.value = feed.id
  tagInput.value = feed.tags || ''
}

async function saveTags(feedId) {
  const tags = tagInput.value.trim()
  await updateFeedTags(feedId, tags)
  editingFeedId.value = null
  tagInput.value = ''
  await loadFeeds()
}

async function doAutoTag(feedId) {
  await autoTagFeed(feedId)
  await loadFeeds()
}

async function searchPodcast() {
  searching.value = true
  try {
    const res = await apiSearchPodcast(newFeed.value.url)
    podcastResults.value = res.data.results || []
  } catch (e) {
    alert('搜索失败')
  }
  searching.value = false
}

function selectPodcast(pod) {
  newFeed.value.name = pod.name
  newFeed.value.url = pod.feed_url
  podcastResults.value = []
}

async function searchWechat() {
  searching.value = true
  try {
    const res = await apiSearchWechat(newFeed.value.url)
    wechatResults.value = res.data.results || []
  } catch (e) {
    alert('搜索失败')
  }
  searching.value = false
}

function generateRssHubLink() {
  if (!rsshubId.value) return
  const id = rsshubId.value.trim()
  let url = ''
  if (newFeed.value.type === 'weibo_search') {
    url = `https://rsshub.app/weibo/user/${id}`
  } else if (newFeed.value.type === 'douyin') {
    url = `https://rsshub.app/douyin/user/${id}`
  } else if (newFeed.value.type === 'xiaohongshu') {
    url = `https://rsshub.app/xiaohongshu/user/${id}`
  }
  newFeed.value.url = url
  newFeed.value.type = 'rss' // RSSHub 生成的是标准 RSS
  alert(`已生成 RSS 链接: ${url}\n注意：由于 RSSHub 返回的是标准 RSS 格式，已自动将类型切换为 "RSS / Atom"。`)
}

function selectWechat(acc) {
  if (acc.source === 'wechat2rss' && acc.rss_url) {
    // Wechat2RSS 收录 → 直接用 RSS 类型订阅（获取全文）
    newFeed.value.type = 'rss'
    newFeed.value.name = acc.name
    newFeed.value.url = acc.rss_url
  } else {
    // 搜狗搜索 → 用 wechat_search 类型（只抓列表摘要）
    newFeed.value.name = acc.name
    newFeed.value.url = 'wechat://' + acc.name
  }
  wechatResults.value = []
}

// === OPML ===
async function doImportOPML() {
  importing.value = true
  importResult.value = null
  try {
    const res = await importOPMLFile(opmlContent.value)
    importResult.value = res.data
    if (res.data.added > 0) {
      await loadFeeds()
    }
  } catch (e) {
    alert(e.response?.data?.detail || '导入失败，请检查 OPML 格式')
  }
  importing.value = false
}

async function handleExportOPML() {
  try {
    const res = await exportOPML()
    const opml = res.data.opml
    // 创建下载
    const blob = new Blob([opml], { type: 'text/xml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `feeds_export_${new Date().toISOString().slice(0,10)}.opml`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert('导出失败')
  }
}

onMounted(loadFeeds)
</script>

<style scoped>
.feeds-page { padding: 16px; }
.feeds-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.feeds-header h2 { font-size: 20px; }

.feed-list { display: flex; flex-direction: column; gap: 12px; }
.feed-card {
  background: var(--card-bg);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.feed-info { flex: 1; }
.feed-name { font-weight: 600; font-size: 16px; margin-bottom: 6px; }
.feed-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 6px;
  font-size: 12px;
}
.feed-type {
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}
.feed-type.rss { background: #e3f2fd; color: #1976d2; }
.feed-type.podcast { background: #fce4ec; color: #c2185b; }
.feed-type.wechat_search { background: #e8f5e9; color: #388e3c; }
.feed-type.weibo_search { background: #fff3e0; color: #f57c00; }
.feed-type.douyin { background: #1c1c1e; color: #ff0050; }
.feed-type.xiaohongshu { background: #ffebee; color: #ff2442; }
.feed-category { color: #666; }
.feed-time { color: #999; }
.feed-url { font-size: 12px; color: #999; word-break: break-all; }

.feed-actions {
  display: flex;
  gap: 8px;
  margin-left: 12px;
}

.header-actions { display: flex; gap: 8px; }

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  background: var(--btn-bg);
  color: var(--text-color);
  cursor: pointer;
  font-size: 14px;
}
.btn:hover { filter: brightness(0.9); }
.btn-primary { background: #1976d2; color: white; }
.btn-danger { background: #ffebee; color: #c62828; }
.btn-small { padding: 6px 12px; font-size: 12px; }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }

/* 标签 */
.feed-tags-row { margin-top: 8px; }
.tags-display { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.mini-tag { background: #f0f0f5; color: #555; padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.tag-edit-btn, .tag-auto-btn, .tag-add-btn { background: none; border: none; font-size: 13px; cursor: pointer; padding: 2px 6px; color: #999; }
.tag-edit-btn:hover, .tag-auto-btn:hover, .tag-add-btn:hover { color: #e94560; }
.tags-edit { display: flex; }
.tag-input { flex: 1; padding: 5px 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 12px; }

/* OPML 导入结果 */
.import-result { margin: 12px 0; padding: 12px; border-radius: 8px; font-size: 13px; }
.import-result.success { background: #e8f5e9; color: #2e7d32; }
.import-result.error { background: #ffebee; color: #c62828; }
.import-errors { margin-top: 6px; font-size: 12px; }
.import-errors div { margin: 2px 0; }

.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 16px;
}
.modal {
  background: var(--card-bg);
  border-radius: 16px;
  padding: 24px;
  width: 100%;
  max-width: 480px;
  max-height: 85vh;
  overflow-y: auto;
}
.modal h3 { margin-bottom: 16px; font-size: 18px; }

.form-group { margin-bottom: 16px; }
.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 6px;
  color: #444;
}
.form-control {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  box-sizing: border-box;
}
.type-hint {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
}

/* RSSHub Guide */
.rsshub-guide { background: var(--btn-bg); padding: 12px; border-radius: 8px; margin-bottom: 15px; border-left: 3px solid var(--primary-color); }
.rsshub-guide h4 { margin: 0 0 6px 0; font-size: 14px; color: var(--primary-color); }
.guide-desc { font-size: 13px; color: var(--text-color); opacity: 0.8; margin-bottom: 8px; }
.guide-inputs { display: flex; gap: 8px; }
.guide-input { flex: 1; }
.guide-btn { white-space: nowrap; }
.guide-note { font-size: 12px; color: #888; margin-top: 6px; }

.search-box { margin: 8px 0; }
.search-results {
  margin-top: 8px;
  border: 1px solid #eee;
  border-radius: 8px;
  max-height: 240px;
  overflow-y: auto;
}
.search-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
}
.search-item:hover { background: #f5f5f5; }
.search-item:last-child { border-bottom: none; }

.podcast-cover {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  object-fit: cover;
}
.podcast-name { font-weight: 500; font-size: 14px; }
.podcast-artist { font-size: 12px; color: #888; }

.search-item.is-rss { background: #fff8e1; border-left: 3px solid #ff9800; }
.search-item.is-rss:hover { background: #ffecb3; }
.source-tag { font-size: 11px; padding: 2px 6px; border-radius: 4px; margin-left: 6px; }
.source-tag.wechat2rss { background: #ff9800; color: white; }
.source-tag.sogou { background: #e0e0e0; color: #666; }

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}
</style>
