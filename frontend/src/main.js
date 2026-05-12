import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import Home from './views/Home.vue'
import Feeds from './views/Feeds.vue'
import Settings from './views/Settings.vue'
import DailyPick from './views/DailyPick.vue'

const routes = [
  { path: '/', component: Home, name: 'home' },
  { path: '/feeds', component: Feeds, name: 'feeds' },
  { path: '/settings', component: Settings, name: 'settings' },
  { path: '/daily', component: DailyPick, name: 'daily' }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')