<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { DEMO_ACCOUNTS, ROLE_LABELS, ROLE_SCOPE } from '../constants/roles'
import { TIER_HINT, TIER_LABELS } from '../constants/enums'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const form = reactive({ email: 'admin@coldtier.io', password: 'Demo@2026' })
const zoneTiers: Array<'hot' | 'warm' | 'cold'> = ['hot', 'warm', 'cold']
const chain = [
  { code: '01', name: '配置', note: '档位单价 / 冷区前置条件' },
  { code: '02', name: '试算', note: '阈值粗筛 + 净收益' },
  { code: '03', name: '复检', note: '风险闸门 block / warn' },
  { code: '04', name: '工单', note: '提交计划并导出 CSV' },
]
const localError = ref('')

const busy = computed(() => auth.loading)
const errorText = computed(() => localError.value || auth.error)

function fill(email: string) {
  form.email = email
  form.password = 'Demo@2026'
  localError.value = ''
}

async function submit() {
  localError.value = ''
  if (!form.email || !form.password) {
    localError.value = '请填写邮箱与密码'
    return
  }
  try {
    await auth.login(form.email, form.password)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/overview'
    await router.push(redirect)
  } catch (error) {
    localError.value = (error as { message?: string }).message ?? '登录失败'
  }
}
</script>

<template>
  <div class="login">
    <section class="zone-panel settle">
      <div class="brand">
        <div class="mark mono" aria-hidden="true"><span></span><span></span><span></span></div>
        <div>
          <p class="name">coldtier</p>
          <p class="sub mono">WAREHOUSE TIERING CONSOLE</p>
        </div>
      </div>

      <h1 class="claim">
        数仓存储<br />
        冷热分层与<br />
        <em>迁移收益测算台</em>
      </h1>
      <p class="lede">
        青禾零售 · 数据平台组维护 42 张表、42 TB 明细。这里按 90 天访问热度给每张表定温区，
        再用净收益与风险闸门决定谁能迁、迁了能省多少。
      </p>

      <div class="zones">
        <div v-for="tier in zoneTiers" :key="tier" class="zone" :class="`z-${tier}`">
          <span class="z-code mono">{{ tier === 'hot' ? 'H' : tier === 'warm' ? 'W' : 'C' }}</span>
          <div>
            <p class="z-name">{{ TIER_LABELS[tier] }}</p>
            <p class="z-hint mono">{{ TIER_HINT[tier] }}</p>
          </div>
          <span class="z-scale mono" aria-hidden="true">
            <i v-for="n in 6" :key="n" :style="{ opacity: tier === 'hot' ? 1 : tier === 'warm' ? 0.72 : 0.5 }"></i>
          </span>
        </div>
      </div>

      <ol class="chain">
        <li v-for="(step, index) in chain" :key="step.code">
          <span class="chain-code mono">{{ step.code }}</span>
          <span class="chain-name">{{ step.name }}</span>
          <span class="chain-note mono">{{ step.note }}</span>
          <span v-if="index < chain.length - 1" class="chain-arrow mono" aria-hidden="true">→</span>
        </li>
      </ol>

      <p class="foot mono">3 个角色 · 5 个页面 · 2 个真算算法（Python 计算，前端只展示）</p>
    </section>

    <section class="form-panel settle">
      <div class="rail-wood" aria-hidden="true"></div>
      <div class="form-head">
        <span class="tag">登录闸口 / ACCESS</span>
        <h2>进入货架</h2>
        <p class="hint">演示密码统一为 <code class="mono">Demo@2026</code></p>
      </div>

      <form @submit.prevent="submit">
        <label class="field">
          <span>邮箱</span>
          <input v-model="form.email" class="input" type="email" autocomplete="username" placeholder="admin@coldtier.io" />
        </label>
        <label class="field">
          <span>密码</span>
          <input v-model="form.password" class="input" type="password" autocomplete="current-password" />
        </label>
        <button class="btn btn-primary submit" type="submit" :disabled="busy">
          {{ busy ? '校验中…' : '登录' }}
        </button>
      </form>

      <div v-if="errorText" class="error" role="alert">
        <span class="mono">✕</span>
        <span>{{ errorText }}</span>
      </div>

      <div class="accounts">
        <p class="label">演示账号（点一下自动填充）</p>
        <button
          v-for="account in DEMO_ACCOUNTS"
          :key="account.email"
          class="account"
          type="button"
          @click="fill(account.email)"
        >
          <span class="acc-mail mono">{{ account.email }}</span>
          <span class="acc-role">{{ ROLE_LABELS[account.role] }}</span>
          <span class="acc-scope mono">{{ ROLE_SCOPE[account.role] }}</span>
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.85fr);
}
.zone-panel {
  padding: 34px 44px 30px;
  background: var(--frost-2);
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 18px;
  background-image: repeating-linear-gradient(
    90deg,
    transparent 0 64px,
    oklch(80% 0.012 244 / 0.4) 64px 65px
  );
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.mark {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.mark span {
  display: block;
  width: 24px;
  height: 3px;
  background: var(--wood);
}
.mark span:nth-child(2) {
  width: 17px;
  background: var(--wood-pale);
}
.mark span:nth-child(3) {
  width: 21px;
}
.name {
  font-family: var(--font-mono);
  font-size: 19px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.05;
}
.sub {
  font-size: 9px;
  letter-spacing: 0.18em;
  color: var(--slate-faint);
}
.claim {
  font-size: clamp(28px, 3.2vw, 46px);
  line-height: 1.18;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-top: 6px;
}
.claim em {
  font-style: normal;
  color: var(--wood-deep);
  box-shadow: inset 0 -0.28em 0 var(--wood-wash);
}
.lede {
  max-width: 46ch;
}
.zones {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 6px;
}
.zone {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr) 84px;
  align-items: center;
  gap: 12px;
  padding: 9px 12px 9px 9px;
  background: var(--frost-1);
  border-left: 3px solid var(--line-strong);
}
.z-hot {
  border-left-color: var(--hot);
}
.z-warm {
  border-left-color: var(--warm);
}
.z-cold {
  border-left-color: var(--cold);
}
.z-code {
  font-size: 11px;
  font-weight: 700;
  color: var(--frost-0);
  text-align: center;
  padding: 1px 0;
}
.z-hot .z-code {
  background: var(--hot);
}
.z-warm .z-code {
  background: var(--warm);
}
.z-cold .z-code {
  background: var(--cold);
}
.z-name {
  font-weight: 500;
  font-size: 13px;
}
.z-hint {
  font-size: 10px;
  color: var(--slate-faint);
}
.z-scale {
  display: flex;
  gap: 2px;
  justify-content: flex-end;
}
.z-scale i {
  width: 3px;
  height: 14px;
  background: var(--slate-faint);
}
.chain {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
  margin-top: 4px;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  background: var(--frost-1);
}
.chain li {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 10px 12px;
  border-right: var(--hair);
}
.chain li:last-child {
  border-right: 0;
}
.chain-code {
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--wood-deep);
}
.chain-name {
  font-size: 13px;
  font-weight: 500;
}
.chain-note {
  font-size: 9.8px;
  line-height: 1.45;
  color: var(--slate-faint);
}
.chain-arrow {
  position: absolute;
  right: -7px;
  top: 12px;
  font-size: 11px;
  color: var(--wood-pale);
  background: var(--frost-1);
  padding: 0 2px;
}
.foot {
  margin-top: auto;
  font-size: 10px;
  letter-spacing: 0.1em;
  color: var(--slate-faint);
}
.form-panel {
  padding: 30px 40px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: var(--frost-0);
  justify-content: center;
}
.form-head h2 {
  font-size: var(--step-3);
  font-weight: 700;
  margin-top: 8px;
}
.hint {
  font-size: 12px;
  color: var(--slate-soft);
  margin-top: 3px;
}
.hint code {
  background: var(--frost-2);
  padding: 1px 5px;
}
form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.submit {
  justify-content: center;
  padding: 9px;
  margin-top: 4px;
}
.error {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 9px 11px;
  border: 1px solid var(--block);
  background: var(--hot-wash);
  color: var(--block);
  font-size: 12px;
}
.accounts {
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-top: var(--hair);
  padding-top: 12px;
  margin-top: 4px;
}
.account {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  grid-template-rows: auto auto;
  gap: 0 10px;
  text-align: left;
  padding: 7px 9px;
  border: 1px solid var(--line);
  background: var(--frost-1);
  cursor: pointer;
  transition: border-color 180ms var(--ease), transform 160ms var(--ease);
}
.account:hover {
  border-color: var(--wood);
  transform: translateX(2px);
}
.acc-mail {
  font-size: 11px;
  color: var(--slate);
}
.acc-role {
  font-size: 11px;
  color: var(--wood-deep);
  text-align: right;
}
.acc-scope {
  grid-column: 1 / -1;
  font-size: 9.5px;
  color: var(--slate-faint);
  letter-spacing: 0.02em;
}
@media (max-width: 1023px) {
  .login {
    grid-template-columns: minmax(0, 1fr);
  }
  .zone-panel {
    border-right: 0;
    border-bottom: 1px solid var(--line);
    padding: 24px 20px;
    gap: 12px;
  }
  .claim {
    font-size: clamp(24px, 6vw, 32px);
  }
  .form-panel {
    padding: 22px 20px 34px;
  }
  .chain {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .chain li:nth-child(2n) {
    border-right: 0;
  }
}
</style>
