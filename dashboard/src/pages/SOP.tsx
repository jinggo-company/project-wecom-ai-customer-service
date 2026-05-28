import React from 'react'
import { Card, Row, Col, Statistic, Table, Progress } from 'antd'
import ReactECharts from 'echarts-for-react'

export const SOPPage: React.FC = () => {
  const sopExecOption = {
    title: { text: 'SOP执行分布', left: 'center' },
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: '60%',
      data: [
        { value: 50, name: '新客户欢迎流程' },
        { value: 45, name: '客户定期跟进' },
        { value: 25, name: '自动标签打标' },
        { value: 8, name: '营销活动精准触达' },
      ],
    }],
  }

  const sopColumns = [
    { title: 'SOP名称', dataIndex: 'name', key: 'name' },
    { title: '触发类型', dataIndex: 'trigger', key: 'trigger' },
    { title: '执行次数', dataIndex: 'count', key: 'count', sorter: (a: any, b: any) => a.count - b.count },
    {
      title: '成功率',
      dataIndex: 'success_rate',
      key: 'success_rate',
      render: (rate: number) => <Progress percent={rate} size="small" status={rate >= 90 ? 'success' : 'exception'} />,
    },
    { title: '状态', dataIndex: 'enabled', key: 'enabled', render: (v: boolean) => v ? '✅ 启用' : '❌ 禁用' },
  ]

  const sopData = [
    { key: '1', name: '新客户欢迎流程', trigger: '事件触发', count: 50, success_rate: 100, enabled: true },
    { key: '2', name: '客户定期跟进', trigger: '事件触发', count: 45, success_rate: 91, enabled: true },
    { key: '3', name: '自动标签打标', trigger: '事件触发', count: 25, success_rate: 96, enabled: true },
    { key: '4', name: '营销活动精准触达', trigger: '条件触发', count: 8, success_rate: 88, enabled: true },
  ]

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic title="SOP规则数" value={4} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="启用中" value={4} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="总执行次数" value={128} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="整体成功率" value={93.8} suffix="%" />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col span={12}>
          <Card title="执行分布">
            <ReactECharts option={sopExecOption} style={{ height: 300 }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="执行成功率趋势">
            <ReactECharts
              option={{
                title: { text: '每日成功率', left: 'center' },
                tooltip: { trigger: 'axis' },
                xAxis: { type: 'category', data: Array.from({ length: 7 }, (_, i) => `D${i + 1}`) },
                yAxis: { type: 'value', min: 80, max: 100, axisLabel: { formatter: '{value}%' } },
                series: [{
                  type: 'line',
                  smooth: true,
                  data: [88, 92, 95, 90, 94, 96, 94],
                  areaStyle: { opacity: 0.3 },
                }],
              }}
              style={{ height: 300 }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="SOP规则列表" style={{ marginTop: 16 }}>
        <Table columns={sopColumns} dataSource={sopData} pagination={false} />
      </Card>
    </div>
  )
}
