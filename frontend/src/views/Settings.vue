<template>
  <div class="settings-page">
    <h2>⚙️ 设置</h2>
    
    <div class="setting-card">
      <h3>🤖 AI 配置</h3>
      <div class="form-group">
        <label>AI提供商</label>
        <select v-model="settings.ai_provider">
          <option value="openai">OpenAI</option>
          <option value="deepseek">DeepSeek</option>
          <option value="kimi">Kimi (Moonshot)</option>
        </select>
      </div>
      <div class="form-group">
        <label>API密钥</label>
        <input v-model="settings.ai_api_key" type="password" placeholder="sk-..." />
      </div>
      <div class="form-group">
        <label>模型</label>
        <input v-model="settings.ai_model" placeholder="gpt-3.5-turbo" />
      </div>
    </div>

    <div class="setting-card">
      <h3>🌐 翻译配置</h3>
      <div class="form-group">
        <label>翻译提供商</label>
        <select v-model="settings.translate_provider">
          <option value="openai">OpenAI</option>
          <option value="deepseek">DeepSeek</option>
          <option value="kimi">Kimi (Moonshot)</option>
        </select>
      </div>
      <div class="form-group">
        <label>目标语言</label>
        <select v-model="settings.target_language">
          <option value="zh">中文</option>
          <option value="en">English</option>
          <option value="ja">日本語</option>
        </select>
      </div>
    </div>

    <button @click="saveSettings" :disabled="saving" class="btn-save">
      {{ saving ? '保存中...' : '💾 保存设置' }}
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getSettings, saveSettings as apiSaveSettings } from '../api'

const settings = ref({
  ai_provider: 'openai',
  ai_api_key: '',
  ai_model: 'gpt-3.5-turbo',
  translate_provider: 'openai',
  target_language: 'zh'
})
const saving = ref(false)

onMounted(async () => {
  try {
    const res = await getSettings()
    settings.value = { ...settings.value, ...res.data }
  } catch (e) {
    // 如果后端未启动或报错，回退到localStorage
    const saved = localStorage.getItem('ca_settings')
    if (saved) settings.value = { ...settings.value, ...JSON.parse(saved) }
  }
})

async function saveSettings() {
  saving.value = true
  try {
    await apiSaveSettings(settings.value)
    localStorage.setItem('ca_settings', JSON.stringify(settings.value))
    alert('设置已保存！')
  } catch (e) {
    alert('保存失败: ' + e.message)
  }
  saving.value = false
}
</script>

<style scoped>
.settings-page { max-width: 600px; }
h2 { font-size: 20px; color: var(--text-color); margin-bottom: 20px; }

.setting-card { background: var(--card-bg); border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.setting-card h3 { font-size: 16px; margin-bottom: 16px; color: var(--text-color); }

.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 13px; color: var(--text-color); opacity: 0.8; margin-bottom: 6px; }
.form-group input, .form-group select { 
  width: 100%; padding: 10px 12px; border: 1px solid var(--border-color);
  background: var(--bg-color); color: var(--text-color);
  border-radius: 8px; font-size: 14px; 
}

.btn-save { 
  width: 100%; padding: 12px; background: #e94560; color: white; 
  border: none; border-radius: 8px; font-size: 15px; cursor: pointer; 
}
.btn-save:hover { background: #d6336c; }
</style>
