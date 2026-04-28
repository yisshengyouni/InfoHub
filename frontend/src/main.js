import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import Home from './views/Home.vue'
import Feeds from './views/Feeds.vue'
import Settings from './views/Settings.vue'

const routes = [
  { path: '/', component: Home, name: 'home' },
  { path: '/feeds', component: Feeds, name: 'feeds' },
  { path: '/settings', component: Settings, name: 'settings' }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')