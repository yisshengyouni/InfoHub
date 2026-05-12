import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Feeds from '../views/Feeds.vue'
import Settings from '../views/Settings.vue'
import DailyPick from '../views/DailyPick.vue'
import RagChat from '../views/RagChat.vue'

const routes = [
  { path: '/', name: 'home', component: Home },
  { path: '/feeds', name: 'feeds', component: Feeds },
  { path: '/daily', name: 'daily', component: DailyPick },
  { path: '/rag', name: 'rag', component: RagChat },
  { path: '/settings', name: 'settings', component: Settings }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
