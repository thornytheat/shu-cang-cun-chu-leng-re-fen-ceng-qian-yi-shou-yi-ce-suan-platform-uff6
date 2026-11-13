import { ref, type Ref } from 'vue'

/** 统一的「加载 / 失败可重试 / 完成」封装：空态与错误态都可以从 UI 直接重跑。 */
export function useAsync<T>(loader: () => Promise<T>, options: { immediate?: boolean } = {}) {
  const data = ref<T | null>(null) as Ref<T | null>
  const loading = ref(false)
  const error = ref('')
  let lastError: unknown = null

  async function run(): Promise<T | null> {
    loading.value = true
    error.value = ''
    try {
      const result = await loader()
      data.value = result
      return result
    } catch (err) {
      lastError = err
      error.value = (err as { message?: string })?.message ?? '加载失败'
      return null
    } finally {
      loading.value = false
    }
  }

  if (options.immediate) void run()

  return { data, loading, error, run, lastError: () => lastError }
}
