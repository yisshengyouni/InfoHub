import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// Feeds
export const getFeeds = () => api.get('/feeds/')
export const getFeedStats = () => api.get('/feeds/stats')
export const updateFeedTags = (id, tags) => api.patch(`/feeds/${id}/tags`, tags, { headers: { 'Content-Type': 'text/plain' } })
export const autoTagFeed = (id) => api.post(`/feeds/${id}/auto-tag`)
export const autoTagAll = () => api.post('/feeds/auto-tag-all')
export const createFeed = (data) => api.post('/feeds/', data)
export const deleteFeed = (id) => api.delete(`/feeds/${id}`)
export const fetchFeed = (id) => api.post(`/feeds/${id}/fetch`)
export const fetchAllFeeds = () => api.post('/feeds/fetch-all')
export const importOPML = (data) => api.post('/feeds/import-opml', data)
export const importOPMLFile = (xml) => api.post('/feeds/import-opml-file', xml)
export const exportOPML = () => api.get('/feeds/export-opml')

// Contents
export const getContents = (params) => api.get('/contents/', { params })
export const getInitData = (params) => api.get('/contents/init-data', { params })
export const getContent = (id) => api.get(`/contents/${id}`)
export const markRead = (id, progress) => api.patch(`/contents/${id}/read`, { progress })
export const toggleStar = (id) => api.patch(`/contents/${id}/star`)
export const updateContent = (id, data) => api.patch(`/contents/${id}`, data)
export const deleteContent = (id) => api.delete(`/contents/${id}`)
export const getStats = () => api.get('/contents/stats/overview')

// AI Summary (支持多长度)
export const summarize = (data) => api.post('/summary/', data)

// Translate
export const translate = (data) => api.post('/translate/', data)

// Daily Picks
export const getDailyPicks = (params) => api.get('/daily-picks/', { params })
export const getTodayPick = () => api.get('/daily-picks/today')
export const getPickByDate = (date) => api.get(`/daily-picks/${date}`)
export const getPickArticles = (date) => api.get(`/daily-picks/${date}/articles`)
export const generateDailyPick = () => api.post('/daily-picks/generate')

// Settings
export const getSettings = () => api.get('/settings/')
export const saveSettings = (data) => api.post('/settings/', data)

// TTS
export const generateTTS = (data) => api.post('/tts/', data)

// Discover
export const searchPodcast = (query) => api.get('/discover/podcast', { params: { query } })
export const searchWechat = (query) => api.get('/discover/wechat', { params: { query } })
export const getWechat2Rss = (query) => api.get('/discover/wechat2rss', { params: { query } })
