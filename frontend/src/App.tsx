import React from 'react';
import { Layout, Menu, Typography } from 'antd';
import { CameraOutlined, PictureOutlined, SettingOutlined, FolderOutlined } from '@ant-design/icons';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import LookbookStudio from './pages/LookbookStudio';
import Materials from './pages/Materials';
import Gallery from './pages/Gallery';
import Settings from './pages/Settings';
import './App.css';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

const menuItems = [
  { key: '/studio', icon: <CameraOutlined />, label: '拍摄工作台' },
  { key: '/materials', icon: <FolderOutlined />, label: '素材管理' },
  { key: '/gallery', icon: <PictureOutlined />, label: '我的相册' },
  { key: '/settings', icon: <SettingOutlined />, label: '设置' },
];

const AppContent: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = React.useState(false);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} width={200}
        style={{ overflow: 'auto', height: '100vh', position: 'fixed', left: 0, top: 0, bottom: 0 }}>
        <div className="logo">
          <CameraOutlined style={{ fontSize: 24, color: '#1890ff' }} />
          {!collapsed && <span className="logo-text">私人摄影团队</span>}
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[location.pathname]}
          items={menuItems} onClick={({ key }) => navigate(key)} />
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.2s' }}>
        <Header style={{ padding: '0 24px', background: '#fff', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', height: 56 }}>
          <Title level={4} style={{ margin: 0 }}>私人摄影团队 MVP</Title>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8, minHeight: 'calc(100vh - 56px - 48px)' }}>
          <Routes>
            <Route path="/studio" element={<LookbookStudio />} />
            <Route path="/materials" element={<Materials />} />
            <Route path="/gallery" element={<Gallery />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<LookbookStudio />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
};

const App: React.FC = () => (
  <BrowserRouter>
    <AppContent />
  </BrowserRouter>
);

export default App;
