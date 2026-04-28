import { defineStore } from 'pinia'
import { getContents, getFeeds, fetchAllFeeds } from '../api'

export const useAppStore = defineStore('app', {
  state: () => ({
    feeds: [],
    contents: [],
    loading: false,
    currentFeed: null,
    searchQuery: '',
    filterRead: null,
    filterStarred: null
  }),
  
  actions: {
    async loadFeeds() {
      const res = await getFeeds()
      this.feeds = res.data
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
      
      const res = await getContents(params)
      this.contents = res.data
      this.loading = false
    },
    
    async refreshAll() {
      await fetchAllFeeds()
      await this.loadContents()
    },
    
    setFeedFilter(feedId) {
      this.currentFeed = feedId
      this.loadContents()
    }
  }
})