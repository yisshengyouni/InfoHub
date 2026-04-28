import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// Feeds
export const getFeeds = () => api.get('/feeds/')
export const createFeed = (data) => api.post('/feeds/', data)
export const deleteFeed = (id) => api.delete(`/feeds/${id}`)
export const fetchFeed = (id) => api.post(`/feeds/${id}/fetch`)
export const fetchAllFeeds = () => api.post('/feeds/fetch-all')

// Contents
export const getContents = (params) => api.get('/contents/', { params })
export const getContent = (id) => api.get(`/contents/${id}`)
export const markRead = (id) => api.patch(`/contents/${id}/read`)
export const toggleStar = (id) => api.patch(`/contents/${id}/star`)
export const deleteContent = (id) => api.delete(`/contents/${id}`)

// AI Summary
export const summarize = (data) => api.post('/summary/', data)

// Translate
export const translate = (data) => api.post('/translate/', data)

// Settings
export const getSettings = () => api.get('/settings/')
export const saveSettings = (data) => api.post('/settings/', data)

// TTS
export const generateTTS = (data) => api.post('/tts/', data)

// Discover
export const searchPodcast = (query) => api.get('/discover/podcast', { params: { query } })
export const searchWechat = (query) => api.get('/discover/wechat', { params: { query } })
export const getWechat2Rss = (query) => api.get('/discover/wechat2rss', { params: { query } })
