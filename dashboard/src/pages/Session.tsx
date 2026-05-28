import React, { useState } from 'react'
import { Card, Table, Select, Space } from 'antd'
import ReactECharts from 'echarts-for-react'

const { Option } = Select

export const SessionPage: React.FC = () => {
  const [period, setPeriod] = useState('day')

  const sessionOption = {
    title: { text: '会话量趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['会话数', '消息数'], bottom: 0 },
    xAxis: {
      type: 'category',
      data: Array.from({ length: 24 }, (_, i) => `${i}:00`),
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: '会话数',
        type: 'bar',
        data: Array.from({ length: 24 }, (_, i) => 5 + (i % 8) * 2),
      },
      {
        name: '消息数',
        type: 'line',
        smooth: true,
        data: Array.from({ length: 24 }, (_, i) => 15 + (i % 10) * 5),
      },
    ],
  }

  const aiRatioOption = {
    title: { text: 'AI回复占比趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: Array.from({ length: 24 }, (_, i) => `${i}:00`),
    },
    yAxis: { type: 'value', min: 0.5, max: 1, axisLabel: { formatter: '{value}%' } },
    series: [{
      name: 'AI占比',
      type: 'line',
      smooth: true,
      areaStyle: { opacity: 0.3 },
      data: Array.from({ length: 24 }, (_, i) => +(0.6 + (i % 4) * 0.05) * 100),
    }],
  }

  const columns = [
    { title: '会话ID', dataIndex: 'id', key: 'id' },
    { title: '用户', dataIndex: 'user_id', key: 'user_id' },
    { title: '渠道', dataIndex: 'channel', key: 'channel' },
    { title: '消息数', dataIndex: 'message_count', key: 'message_count' },
    { title: 'AI处理', dataIndex: 'ai_handled', key: 'ai_handled', render: (v: boolean) => v ? '✅' : '❌' },
    { title: '状态', dataIndex: 'resolution_status', key: 'resolution_status' },
    { title: '意图', dataIndex: 'intent', key: 'intent' },
  ]

  const mockSessions = Array.from({ length: 50 }, (_, i) => ({
    key: i,
    id: `session_${i}`,
    user_id: `user_${(i % 20).toString().padStart(3, '0')}`,
    channel: i % 5 !== 0 ? '单聊' : '群聊',
    message_count: 3 + (i % 10),
    ai_handled: i % 3 !== 0,
    resolution_status: i % 4 !== 0 ? 'resolved' : 'pending',
    intent: ['产品咨询', '订单查询', '售后服务', '投诉', '闲聊'][i % 5],
  }))

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <span>时间维度：</span>
        <Select value={period} onChange={setPeriod} style={{ width: 120 }}>
          <Option value="day">今日</Option>
          <Option value="week">本周</Option>
          <Option value="month">本月</Option>
        </Select>
      </Space>

      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card>
            <ReactECharts option={sessionOption} style={{ height: 300 }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card>
            <ReactECharts option={aiRatioOption} style={{ height: 300 }} />
          </Card>
        </Col>
      </Row>

      <Card title="会话列表" style={{ marginTop: 16 }}>
        <Table columns={columns} dataSource={mockSessions.slice(0, 10)} pagination={{ pageSize: 10 }} />
      </Card>
    </div>
  )
}
