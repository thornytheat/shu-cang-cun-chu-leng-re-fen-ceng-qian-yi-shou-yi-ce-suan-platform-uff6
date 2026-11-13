import { defineStore } from 'pinia'
import {
  addPlanItems,
  createPlan,
  downloadTickets,
  fetchPlan,
  fetchPlans,
  fetchReconciliation,
  postBills,
  postReceipts,
  recheckPlan,
  removePlanItem,
  startBatch,
  submitPlan,
} from '../api/plans'
import type { Plan, PlanReconciliation, ReceiptResult } from '../types/domain'
import { ACK_REASON_LABELS } from '../constants/enums'

const reasonLabel = (reason: string | undefined): string =>
  (reason && ACK_REASON_LABELS[reason]) || reason || '未知原因'

interface PlanState {
  list: Plan[]
  current: Plan | null
  recon: PlanReconciliation | null
  attempts: Record<string, number>
  loading: boolean
  busy: boolean
  error: string
  notice: string
}

export const usePlanStore = defineStore('plan', {
  state: (): PlanState => ({
    list: [],
    current: null,
    recon: null,
    attempts: {},
    loading: false,
    busy: false,
    error: '',
    notice: '',
  }),
  actions: {
    syncList() {
      if (!this.current) return
      this.list = this.list.map((plan) => (plan.id === this.current?.id ? { ...this.current } : plan))
    },
    async loadList() {
      this.loading = true
      this.error = ''
      try {
        const result = await fetchPlans()
        this.list = result.items
        if (!this.current && this.list.length) {
          await this.open(this.list[0].id)
        }
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '加载计划失败'
      } finally {
        this.loading = false
      }
    },
    async open(id: string) {
      this.busy = true
      this.error = ''
      try {
        this.current = await fetchPlan(id)
        this.recon = null
        this.attempts = {}
        if (this.current.status !== 'draft') {
          await this.loadRecon()
        }
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '加载计划失败'
      } finally {
        this.busy = false
      }
    },
    async loadRecon() {
      if (!this.current) return
      try {
        this.recon = await fetchReconciliation(this.current.id)
        // 从既有回执号恢复尝试计数：新回执号不与历史冲突（重发仍是同一号码，幂等）
        for (const row of this.recon.rows) {
          const match = /-(\d+)$/.exec(row.receipt_no)
          if (match) {
            this.attempts[row.item_id] = Math.max(this.attempts[row.item_id] ?? 0, Number(match[1]))
          }
        }
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '加载对账失败'
      }
    },
    /** 回执号：同一表同一尝试次数恒定 —— 重发即幂等重试，服务端不重复计费。 */
    receiptNo(itemIndex: number, attempt: number): string {
      const code = this.current?.code ?? 'MP'
      return `RC-${code}-${String(itemIndex + 1).padStart(2, '0')}-${attempt}`
    },
    billNo(itemIndex: number): string {
      const code = this.current?.code ?? 'MP'
      return `BILL-${code}-${String(itemIndex + 1).padStart(2, '0')}`
    },
    async runBatch(batchNo: string) {
      if (!this.current) return
      this.busy = true
      this.error = ''
      try {
        const ack = await startBatch(this.current.id, batchNo)
        this.recon = ack.reconciliation
        await this.refreshCurrent()
        this.notice = ack.created
          ? `批次 ${ack.batch.batch_no} 已启动：${ack.touched} 张表进入执行`
          : `批次 ${ack.batch.batch_no} 已存在，整批重跑未重复计费`
        this.syncList()
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '启动批次失败'
      } finally {
        this.busy = false
      }
    },
    async sendReceipt(itemId: string, itemIndex: number, result: ReceiptResult, resend = false) {
      if (!this.current) return
      this.busy = true
      this.error = ''
      try {
        const attempt = resend ? (this.attempts[itemId] ?? 1) : (this.attempts[itemId] ?? 0) + 1
        this.attempts[itemId] = attempt
        const receiptNo = this.receiptNo(itemIndex, attempt)
        const ack = await postReceipts(this.current.id, [
          {
            receipt_no: receiptNo,
            item_id: itemId,
            result,
            message: result === 'failed' ? '平台组回执：迁移失败，待重试' : '平台组回执：迁移完成',
          },
        ])
        this.recon = ack.reconciliation
        await this.refreshCurrent()
        const first = ack.results[0]
        this.notice = first?.applied
          ? `回执 ${receiptNo} 已生效：${first.table_name} → ${first.status_label}`
          : `回执 ${receiptNo} 未生效：${reasonLabel(first?.reason)}，未重复计费`
        this.syncList()
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '登记回执失败'
      } finally {
        this.busy = false
      }
    },
    async sendBill(itemId: string, itemIndex: number, amount: number, billMonth: string) {
      if (!this.current) return
      this.busy = true
      this.error = ''
      try {
        const billNo = this.billNo(itemIndex)
        const ack = await postBills(this.current.id, [
          { bill_no: billNo, item_id: itemId, bill_month: billMonth, actual_save_month: amount },
        ])
        this.recon = ack.reconciliation
        await this.refreshCurrent()
        const first = ack.results[0]
        this.notice = first?.applied
          ? `账单 ${billNo} 已生效：${first.table_name} → ${first.status_label}`
          : `账单 ${billNo} 未生效：${reasonLabel(first?.reason)}，未重复计费`
        this.syncList()
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '登记账单失败'
      } finally {
        this.busy = false
      }
    },
    async refreshCurrent() {
      if (!this.current) return
      this.current = await fetchPlan(this.current.id)
    },
    async create(title: string, threshold: number, tableIds: string[]) {
      this.busy = true
      this.error = ''
      this.notice = ''
      try {
        const plan = await createPlan({ title, threshold, table_ids: tableIds })
        this.current = plan
        this.list = [plan, ...this.list]
        this.notice = `已创建 ${plan.code}，共 ${plan.item_count} 项，等待风险复检`
        return plan
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '建计划失败'
        return null
      } finally {
        this.busy = false
      }
    },
    async addItems(tableIds: string[]) {
      if (!this.current) return
      this.busy = true
      try {
        this.current = await addPlanItems(this.current.id, tableIds)
        this.notice = `已追加 ${tableIds.length} 张表`
        this.syncList()
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '追加失败'
      } finally {
        this.busy = false
      }
    },
    async remove(itemId: string) {
      if (!this.current) return
      this.busy = true
      try {
        this.current = await removePlanItem(this.current.id, itemId)
        this.notice = '已从计划中移除该表'
        this.syncList()
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '移除失败'
      } finally {
        this.busy = false
      }
    },
    async recheck() {
      if (!this.current) return
      this.busy = true
      this.error = ''
      try {
        this.current = await recheckPlan(this.current.id)
        const plan = this.current
        this.notice = `风险复检完成：${plan.risk_block_count} 张阻断 / ${plan.risk_warn_count} 张需确认`
        this.syncList()
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '复检失败'
      } finally {
        this.busy = false
      }
    },
    async submit() {
      if (!this.current) return
      this.busy = true
      this.error = ''
      try {
        this.current = await submitPlan(this.current.id)
        const plan = this.current
        this.notice = `已提交 ${plan.item_count} 张，净年省 ¥${plan.net_save_year.toLocaleString('zh-CN')}，可启动执行批次`
        await this.loadRecon()
        this.syncList()
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '提交失败'
      } finally {
        this.busy = false
      }
    },
    async exportCsv() {
      if (!this.current) return null
      this.busy = true
      this.error = ''
      try {
        const result = await downloadTickets(this.current.id)
        this.notice = `已导出工单 CSV：${result.rows} 行`
        return result
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '导出失败'
        return null
      } finally {
        this.busy = false
      }
    },
  },
})
