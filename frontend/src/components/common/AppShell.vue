<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/authStore'
import { ROLE_LABELS } from '../../constants/roles'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const menuOpen = ref(false)

const lastTable = computed(() => localStorage.getItem('coldtier_last_table') ?? '')

const nav = computed(() => [
  { code: 'A-01', label: '存储概览', to: '/overview', active: route.path === '/overview' },
  {
    code: 'A-02',
    label: '表热度详情',
    to: lastTable.value ? `/tables/${lastTable.value}` : '/overview',
    active: route.path.startsWith('/tables'),
  },
  { code: 'B-01', label: '策略与试算', to: '/policies', active: route.path === '/policies' },
  { code: 'C-01', label: '迁移计划', to: '/plans', active: route.path === '/plans' },
])

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="shell">
    <aside class="rail" :class="{ open: menuOpen }">
      <div class="brand">
        <div class="brand-mark mono" aria-hidden="true">
          <span></span><span></span><span></span>
        </div>
        <div>
          <p class="brand-name">coldtier</p>
          <p class="brand-sub mono">WAREHOUSE TIERING</p>
        </div>
      </div>
      <p class="org">{{ auth.user?.team || '青禾零售 · 数据平台组' }}</p>

      <nav class="nav" aria-label="主导航">
        <router-link
          v-for="item in nav"
          :key="item.code"
          :to="item.to"
          class="nav-item"
          :class="{ active: item.active }"
          @click="menuOpen = false"
        >
          <span class="nav-code mono">{{ item.code }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="rail-foot">
        <div class="user">
          <p class="user-name">{{ auth.displayName || '未登录' }}</p>
          <p class="user-role mono">
            {{ auth.user ? ROLE_LABELS[auth.role] : '—' }}
          </p>
          <p class="user-mail mono">{{ auth.email }}</p>
        </div>
        <button class="btn btn-ghost btn-sm" type="button" @click="logout">退出</button>
      </div>
    </aside>

    <div class="main">
      <button class="menu-btn mono" type="button" @click="menuOpen = !menuOpen">
        {{ menuOpen ? '收起货架' : '展开货架' }}
      </button>
      <div class="content">
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: var(--rail) minmax(0, 1fr);
  min-height: 100vh;
}
.rail {
  position: sticky;
  top: 0;
  align-self: start;
  height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px 16px 14px;
  background: var(--frost-1);
  border-right: 1px solid var(--line);
  background-image: repeating-linear-gradient(
    90deg,
    transparent 0 46px,
    oklch(80% 0.012 244 / 0.35) 46px 47px
  );
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-mark {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.brand-mark span {
  display: block;
  width: 22px;
  height: 3px;
  background: var(--wood);
}
.brand-mark span:nth-child(2) {
  width: 16px;
  background: var(--wood-pale);
}
.brand-mark span:nth-child(3) {
  width: 19px;
}
.brand-name {
  font-family: var(--font-mono);
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.brand-sub {
  font-size: 9px;
  letter-spacing: 0.16em;
  color: var(--slate-faint);
}
.org {
  font-size: 11.5px;
  color: var(--slate-soft);
  padding-bottom: 12px;
  border-bottom: var(--hair);
}
.nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-item {
  display: grid;
  grid-template-columns: 44px 1fr;
  align-items: center;
  gap: 8px;
  padding: 8px 8px;
  border-left: 2px solid transparent;
  color: var(--slate-soft);
  transition: background 180ms var(--ease), border-color 180ms var(--ease);
}
.nav-item:hover {
  background: var(--frost-2);
  text-decoration: none;
  color: var(--slate);
}
.nav-item.active {
  border-left-color: var(--wood);
  background: var(--frost-0);
  color: var(--slate);
}
.nav-code {
  font-size: 10.5px;
  letter-spacing: 0.08em;
  color: var(--slate-faint);
}
.nav-item.active .nav-code {
  color: var(--wood-deep);
  font-weight: 700;
}
.nav-label {
  font-size: 13px;
}
.rail-foot {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 12px;
  border-top: var(--hair);
}
.user-name {
  font-size: 13px;
  font-weight: 500;
}
.user-role {
  font-size: 10.5px;
  color: var(--wood-deep);
  letter-spacing: 0.06em;
}
.user-mail {
  font-size: 10px;
  color: var(--slate-faint);
  overflow: hidden;
  text-overflow: ellipsis;
}
.main {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.content {
  padding: 20px 30px 44px;
  max-width: 1500px;
  width: 100%;
}
.menu-btn {
  display: none;
  margin: 10px 16px 0;
  padding: 6px 10px;
  border: 1px solid var(--line-strong);
  background: var(--frost-1);
  font-size: 11px;
  letter-spacing: 0.1em;
  cursor: pointer;
}
@media (max-width: 1023px) {
  .shell {
    grid-template-columns: minmax(0, 1fr);
  }
  .rail {
    position: static;
    height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--line);
    display: none;
  }
  .rail.open {
    display: flex;
  }
  .menu-btn {
    display: inline-block;
  }
  .content {
    padding: 16px 18px 36px;
  }
}
@media (max-width: 767px) {
  .content {
    padding: 12px 12px 32px;
  }
}
</style>
