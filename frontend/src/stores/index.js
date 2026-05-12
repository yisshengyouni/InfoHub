import { defineStore } from 'pinia'
import { getContents, getFeeds, getFeedStats, fetchAllFeeds, getStats, updateContent } from '../api'

export const useAppStore = defineStore('app', {
  state: () => ({
    feeds: [],
    feedStats: [],
    contents: [],
    loading: false,
    currentFeed: null,
    searchQuery: '',
    filterRead: null,
    filterStarred: null,
    dateRange: '',  // 'today' | 'week' | 'month' | ''
    stats: { total: 0, unread: 0, starred: 0, today: 0 }
  }),
  
  actions: {
    async loadFeeds() {
      const res = await getFeeds()
      this.feeds = res.data
    },
    
    async loadFeedStats() {
      try {
        const res = await getFeedStats()
        this.feedStats = res.data
      } catch (e) {
        console.error('loadFeedStats', e)
      }
    },
    
    async loadContents() {
      this.loading = true
      const params = {
        page: 1,
        page_size: 50
      }
      if (this.currentFeed) params.feed_id = this.currentFeed
      if (this.filterRead !== null) params.is_read = this.filterRead
      if (this.filterStarred !== null) params.is_starred = this.filterStarred
      if (this.searchQuery) params.search = this.searchQuery
      if (this.dateRange) params.date_range = this.dateRange
      
      const res = await getContents(params)
      this.contents = res.data
      this.loading = false
    },
    
    async refreshAll() {
      await fetchAllFeeds()
      await this.loadContents()
      await this.loadStats()
      await this.loadFeedStats()
    },
    
    async loadStats() {
      try {
        const res = await getStats()
        this.stats = res.data
      } catch (e) {
        // stats API 可能不存在，静默失败
      }
    },
    
    async setContentTag(contentId, tags) {
      await updateContent(contentId, { tags })
      const item = this.contents.find(c => c.id === contentId)
      if (item) item.tags = tags
    },
    
    async setReadProgress(contentId, progress) {
      await updateContent(contentId, { read_progress: progress, is_read: progress >= 90 })
      const item = this.contents.find(c => c.id === contentId)
      if (item) {
        item.read_progress = progress
        item.is_read = progress >= 90
      }
    },
    
    setFeedFilter(feedId) {
      this.currentFeed = feedId
      this.loadContents()
    },
    
    setDateRange(range) {
      this.dateRange = range
      this.loadContents()
    },
    
    clearFilters() {
      this.currentFeed = null
      this.searchQuery = ''
      this.filterRead = null
      this.filterStarred = null
      this.dateRange = ''
      this.loadContents()
    }
  }
})