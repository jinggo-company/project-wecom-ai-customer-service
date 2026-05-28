import React from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { ConfigProvider, Layout, Menu } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { OverviewPage } from './pages/Overview'
import { SessionPage } from './pages/Session'
import { TagsPage } from './pages/Tags'
import { SOPPage } from './pages/SOP'

const { Header, Content, Sider } = Layout

const App: React.FC = () => {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Layout style={{ minHeight: '100vh' }}>
          <Sider theme="dark">
            <div style={{ padding: '16px', color: '#fff', fontSize: '18px', fontWeight: 'bold' }}>
              WeCom AI客服
            </div>
            <Menu theme="dark" mode="inline" defaultSelectedKeys={['overview']}>
              <Menu.Item key="overview">
                <Link to="/">📊 总览</Link>
              </Menu.Item>
              <Menu.Item key="sessions">
                <Link to="/sessions">💬 会话分析</Link>
              </Menu.Item>
              <Menu.Item key="tags">
                <Link to="/tags">🏷️ 标签分析</Link>
              </Menu.Item>
              <Menu.Item key="sop">
                <Link to="/sop">⚙️ SOP执行</Link>
              </Menu.Item>
            </Menu>
          </Sider>
          <Layout>
            <Header style={{ background: '#fff', padding: '0 24px' }}>
              <h2 style={{ margin: 0 }}>企业微信 AI 客服数据看板</h2>
            </Header>
            <Content style={{ margin: '24px 16px', padding: 24, background: '#fff' }}>
              <Routes>
                <Route path="/" element={<OverviewPage />} />
                <Route path="/sessions" element={<SessionPage />} />
                <Route path="/tags" element={<TagsPage />} />
                <Route path="/sop" element={<SOPPage />} />
              </Routes>
            </Content>
          </Layout>
        </Layout>
      </BrowserRouter>
    </ConfigProvider>
  )
}

export default App
