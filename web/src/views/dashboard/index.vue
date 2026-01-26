<template>
  <div class="dashboard" v-loading="loading">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="mb-16">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #409eff;">
            <el-icon><Goods /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ formatNumber(stats.item_count) }}</div>
            <div class="stat-label">商品总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #67c23a;">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ formatNumber(stats.today_order_count) }}</div>
            <div class="stat-label">今日订单</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #e6a23c;">
            <el-icon><UserFilled /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ formatNumber(stats.member_count) }}</div>
            <div class="stat-label">会员总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #f56c6c;">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">￥{{ formatMoney(stats.today_sales) }}</div>
            <div class="stat-label">今日销售额</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <span>销售趋势</span>
          </template>
          <div ref="chartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <span>快捷操作</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/order')">
              <el-icon><Document /></el-icon> 新建订单
            </el-button>
            <el-button type="success" @click="$router.push('/item')">
              <el-icon><Goods /></el-icon> 添加商品
            </el-button>
            <el-button type="warning" @click="$router.push('/stock')">
              <el-icon><Box /></el-icon> 库存管理
            </el-button>
            <el-button type="info" @click="$router.push('/member')">
              <el-icon><UserFilled /></el-icon> 会员管理
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import * as echarts from 'echarts'
import { getDashboardStats, type DashboardStats } from '@/api/dashboard'

const chartRef = ref<HTMLElement>()
const loading = ref(false)
const stats = reactive<DashboardStats>({
  item_count: 0,
  today_order_count: 0,
  member_count: 0,
  today_sales: 0,
  week_sales_trend: []
})

const dayLabels: Record<string, string> = {
  'Mon': '周一', 'Tue': '周二', 'Wed': '周三', 
  'Thu': '周四', 'Fri': '周五', 'Sat': '周六', 'Sun': '周日'
}

function formatNumber(num: number): string {
  return num.toLocaleString()
}

function formatMoney(num: number): string {
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

let chart: echarts.ECharts | null = null

function updateChart() {
  if (!chart) return
  
  const xData = stats.week_sales_trend.map(t => dayLabels[t.date] || t.date)
  const yData = stats.week_sales_trend.map(t => t.amount)
  
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: xData,
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: '销售额',
        type: 'line',
        smooth: true,
        data: yData,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.5)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.1)' },
          ]),
        },
      },
    ],
  })
}

async function fetchStats() {
  loading.value = true
  try {
    const res = await getDashboardStats()
    if (res.success && res.data) {
      Object.assign(stats, res.data)
      updateChart()
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (chartRef.value) {
    chart = echarts.init(chartRef.value)
    window.addEventListener('resize', () => chart?.resize())
  }
  fetchStats()
})
</script>

<style lang="scss" scoped>
.dashboard {
  .stat-card {
    display: flex;
    align-items: center;
    padding: 20px;

    .stat-icon {
      width: 60px;
      height: 60px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 16px;

      .el-icon {
        font-size: 28px;
        color: #fff;
      }
    }

    .stat-info {
      .stat-value {
        font-size: 24px;
        font-weight: 600;
        color: #303133;
      }

      .stat-label {
        font-size: 14px;
        color: #909399;
        margin-top: 4px;
      }
    }
  }

  .quick-actions {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .el-button {
      width: 100%;
      justify-content: flex-start;
    }
  }
}
</style>
