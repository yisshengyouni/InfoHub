<template>
  <div class="rag-page">
    <div class="rag-header">
      <h2>🤖 AI 知识库问答</h2>
      <p class="rag-desc">基于你的 {{ store.stats.total }} 篇订阅文章，智能回答问题</p>
    </div>

    <!-- 问答输入区 -->
    <div class="chat-box">
      <div v-for="(msg, idx) in messages" :key="idx" class="message" :class="msg.role">
        <div class="msg-avatar">{{ msg.role === 'user' ? '🧑‍💻' : '🤖' }}</div>
        <div class="msg-content">
          <div v-if="msg.role === 'user'" class="user-text">{{ msg.content }}</div>
          <div v-else>
            <div class="ai-answer" v-html="formatAnswer(msg.content)"></div>
            <!-- 引用来源 -->
            <div v-if="msg.sources?.length" class="sources">
              <div class="sources-title">📚 参考文章</div>
              <div v-for="s in msg.sources" :key="s.id" class="source-item">
                <a :href="s.link" target="_blank" class="source-link">
                  <span class="source-num">[{{ s.id }}]</span>
                  <span class="source-title">{{ s.title }}</span>
                  <span class="source-feed">{{ s.feed_name }}</span>
                </a>
                <p class="source-summary">{{ s.summary }}</p>
              </div>
            </div>
            <div v-if="msg.tokens" class="meta">上下文约 {{ msg.tokens }} tokens</div>
          </div>
        </div>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" class="message assistant">
        <div class="msg-avatar">🤖</div>
        <div class="msg-content">
          <div class="typing">正在检索文章并生成回答<span class="dots">...</span></div>
        </div>
      </div>
    </div>

    <!-- 输入框 -->
    <div class="input-bar">
      <input
        v-model="question"
        @keyup.enter="ask"
        placeholder="问点啥？比如：最近AI领域有什么新动态？"
        :disabled="loading"
        class="question-input"
      />
      <button @click="ask" :disabled="loading || !question.trim()" class="send-btn">
        {{ loading ? '思考中...' : '提问' }}
      </button>
    </div>

    <!-- 快捷问题 -->
    <div v-if="messages.length === 0" class="quick-questions">
      <div class="quick-title">💡 试试这些问题</div>
      <div class="quick-tags">
        <button v-for="q in quickQuestions" :key="q" @click="quickAsk(q)" class="quick-tag">
          {{ q }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from '../stores'
import { ragAsk } from '../api'

const store = useAppStore()
const question = ref('')
const loading = ref(false)
const messages = ref([])

const quickQuestions = [
  '最近AI有什么重大突破？',
  '推荐几篇关于产品的文章',
  '科技行业最新趋势是什么？',
  '有哪些创业相关的深度文章？'
]

onMounted(() => {
  if (!store.stats.total) {
    store.loadInitData()
  }
})

function quickAsk(q) {
  question.value = q
  ask()
}

async function ask() {
  const q = question.value.trim()
  if (!q || loading.value) return

  messages.value.push({ role: 'user', content: q })
  loading.value = true
  question.value = ''

  try {
    const res = await ragAsk({ question: q, top_k: 5 })
    const data = res.data
    messages.value.push({
      role: 'assistant',
      content: data.answer,
      sources: data.sources,
      tokens: data.context_tokens
    })
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: '❌ 请求失败：' + (e.response?.data?.detail || e.message)
    })
  }
  loading.value = false
}

function formatAnswer(text) {
  // 简单markdown处理
  return text
    .replace(/\[\d+\]/g, '<span class="cite">$&</span>')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
.rag-page { max-width: 800px; margin: 0 auto; }
.rag-header { text-align: center; margin-bottom: 20px; }
.rag-header h2 { margin: 0; font-size: 22px; }
.rag-desc { color: #888; font-size: 14px; margin-top: 4px; }

.chat-box { background: white; border-radius: 12px; padding: 16px; min-height: 300px; max-height: 60vh; overflow-y: auto; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.message { display: flex; gap: 12px; margin-bottom: 16px; }
.message.user { flex-direction: row-reverse; }
.msg-avatar { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
.msg-content { flex: 1; min-width: 0; }
.user-text { background: #1a1a2e; color: white; padding: 10px 14px; border-radius: 12px; display: inline-block; max-width: 80%; }
.ai-answer { line-height: 1.7; font-size: 14px; color: #333; }
.cite { color: #e94560; font-weight: bold; }

.sources { margin-top: 12px; padding-top: 12px; border-top: 1px dashed #eee; }
.sources-title { font-size: 12px; color: #888; margin-bottom: 8px; }
.source-item { margin-bottom: 8px; padding: 8px 12px; background: #f8f9fa; border-radius: 8px; }
.source-link { display: flex; gap: 8px; align-items: center; text-decoration: none; color: #1a1a2e; font-size: 13px; }
.source-link:hover .source-title { color: #e94560; }
.source-num { color: #e94560; font-weight: bold; min-width: 30px; }
.source-title { flex: 1; }
.source-feed { color: #888; font-size: 11px; background: #eee; padding: 2px 8px; border-radius: 10px; white-space: nowrap; }
.source-summary { margin: 4px 0 0 38px; font-size: 12px; color: #666; line-height: 1.4; }

.meta { font-size: 11px; color: #aaa; margin-top: 8px; }
.typing { color: #888; font-size: 14px; }
.dots { animation: blink 1.5s infinite; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

.input-bar { display: flex; gap: 10px; margin-top: 16px; }
.question-input { flex: 1; padding: 12px 16px; border: 1px solid #ddd; border-radius: 10px; font-size: 14px; }
.question-input:focus { outline: none; border-color: #e94560; }
.send-btn { padding: 12px 24px; background: #e94560; color: white; border: none; border-radius: 10px; font-size: 14px; cursor: pointer; white-space: nowrap; }
.send-btn:hover { background: #d13a52; }
.send-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.quick-questions { margin-top: 20px; text-align: center; }
.quick-title { font-size: 13px; color: #888; margin-bottom: 10px; }
.quick-tags { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
.quick-tag { padding: 8px 14px; border: 1px solid #ddd; border-radius: 20px; background: white; font-size: 13px; cursor: pointer; color: #555; }
.quick-tag:hover { border-color: #e94560; color: #e94560; }
</style>
