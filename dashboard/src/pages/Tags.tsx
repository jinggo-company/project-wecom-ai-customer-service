import React from 'react'
import { Card, Row, Col, Statistic, Tag as AntdTag, Table } from 'antd'
import ReactECharts from 'echarts-for-react'

export const TagsPage: React.FC = () => {
  const tagBarOption = {
    title: { text: '标签分布', left: 'center' },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: ['高价值', '已推送优惠', '已跟进', '活跃用户', '新客户', '普通'] },
    series: [{
      type: 'bar',
      data: [8, 12, 25, 30, 45, 100],
      itemStyle: { color: '#1890ff' },
    }],
  }

  const coverageOption = {
    title: { text: '标签覆盖率', left: 'center' },
    tooltip: { formatter: '{b}: {c}%' },
    series: [{
      type: 'gauge',
      progress: { show: true },
      detail: { formatter: '{value}%' },
      data: [{ value: 85, name: '覆盖率' }],
    }],
  }

  const tagColumns = [
    { title: '标签', dataIndex: 'name', key: 'name', render: (text: string) => <AntdTag color="blue">{text}</AntdTag> },
    { title: '用户数', dataIndex: 'count', key: 'count', sorter: (a: any, b: any) => a.count - b.count },
    { title: '占比', dataIndex: 'percent', key: 'percent' },
    { title: '类型', dataIndex: 'type', key: 'type' },
  ]

  const tagData = [
    { key: '1', name: '新客户', count: 45, percent: '22.5%', type: '自动' },
    { key: '2', name: '活跃用户', count: 30, percent: '15.0%', type: '自动' },
    { key: '3', name: '已跟进', count: 25, percent: '12.5%', type: '自动' },
    { key: '4', name: '已推送优惠', count: 12, percent: '6.0%', type: '手动' },
    { key: '5', name: '高价值', count: 8, percent: '4.0%', type: '手动' },
    { key: '6', name: '普通', count: 100, percent: '50.0%', type: '自动' },
  ]

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col span={8}>
          <Card>
            <Statistic title="总标签数" value={6} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="已打标签用户" value={170} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="标签覆盖率" value={85} suffix="%" />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col span={12}>
          <Card title="标签分布">
            <ReactECharts option={tagBarOption} style={{ height: 300 }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="覆盖率">
            <ReactECharts option={coverageOption} style={{ height: 300 }} />
          </Card>
        </Col>
      </Row>

      <Card title="标签详情" style={{ marginTop: 16 }}>
        <Table columns={tagColumns} dataSource={tagData} pagination={false} />
      </Card>
    </div>
  )
}
