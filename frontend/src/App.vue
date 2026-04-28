<template>
  <div class="app">
    <nav class="nav">
      <div class="nav-brand">📡 内容聚合器</div>
      <div class="nav-links">
        <router-link to="/" :class="{ active: $route.name === 'home' }">📰 内容</router-link>
        <router-link to="/feeds" :class="{ active: $route.name === 'feeds' }">📡 订阅</router-link>
        <router-link to="/settings" :class="{ active: $route.name === 'settings' }">⚙️ 设置</router-link>
      </div>
    </nav>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app { min-height: 100vh; display: flex; flex-direction: column; }
.nav { 
  background: #1a1a2e; 
  color: white; 
  padding: 12px 16px; 
  display: flex; 
  align-items: center; 
  justify-content: space-between;
  position: sticky; 
  top: 0; 
  z-index: 100;
}
.nav-brand { font-size: 18px; font-weight: bold; }
.nav-links { display: flex; gap: 8px; }
.nav-links a { 
  color: rgba(255,255,255,0.7); 
  text-decoration: none; 
  padding: 6px 12px; 
  border-radius: 6px; 
  font-size: 14px;
}
.nav-links a.active, .nav-links a:hover { 
  color: white; 
  background: rgba(255,255,255,0.15); 
}
.main { flex: 1; padding: 16px; max-width: 900px; margin: 0 auto; width: 100%; }
</style>