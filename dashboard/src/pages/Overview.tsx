import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Table } from 'antd'
import ReactECharts from 'echarts-for-react'

export const OverviewPage: React.FC = () => {
  const [overview, setOverview] = useState<any>({
    total_sessions: 50,
    total_messages: 325,
    ai_handled: 34,
    human_handled: 16,
    transfer_to_human_rate: 32.0,
    resolution_rate: 75.0,
    total_users: 20,
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // In production: fetch from API
    // fetch('/api/analytics/overview').then(r => r.json()).then(setOverview)
  }, [])

  const intentOption = {
    title: { text: '意图分布', left: 'center' },
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: 12, name: '产品咨询' },
        { value: 10, name: '订单查询' },
        { value: 8, name: '售后服务' },
        { value: 5, name: '投诉' },
        { value: 15, name: '闲聊' },
      ],
    }],
  }

  const growthOption = {
    title: { text: '用户增长趋势 (30天)', left: 'center' },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: Array.from({ length: 30 }, (_, i) => `D${i + 1}`),
    },
    yAxis: { type: 'value', name: '用户数' },
    series: [{
      name: '总用户数',
      type: 'line',
      smooth: true,
      data: Array.from({ length: 30 }, (_, i) => 20 + i * 2 + (i % 3)),
      areaStyle: { opacity: 0.3 },
    }],
  }

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic title="今日会话" value={overview.total_sessions} suffix="次" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="AI回复" value={overview.ai_handled} suffix="次" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="人工回复" value={overview.human_handled} suffix="次" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="解决率" value={overview.resolution_rate} suffix="%" />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col span={12}>
          <Card title="意图分布">
            <ReactECharts option={intentOption} style={{ height: 350 }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="用户增长">
            <ReactECharts option={growthOption} style={{ height: 350 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col span={24}>
          <Card title="实时指标">
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="活跃会话" value={12} suffix="个" />
              </Col>
              <Col span={6}>
                <Statistic title="排队中" value={3} suffix="个" />
              </Col>
              <Col span={6}>
                <Statistic title="平均响应时间" value={2340} suffix="ms" />
              </Col>
              <Col span={6}>
                <Statistic title="AI准确率" value={87.5} suffix="%" />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
