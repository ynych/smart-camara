import React from 'react';
import { Button, Layout, Menu, Space, Typography } from 'antd';
import { CameraOutlined, FolderOutlined, PictureOutlined, SettingOutlined } from '@ant-design/icons';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { logout } from '../utils/auth';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

const menuItems = [
  { key: '/materials', icon: <FolderOutlined />, label: '素材管理' },
  { key: '/studio', icon: <CameraOutlined />, label: '生图工作台' },
  { key: '/history', icon: <PictureOutlined />, label: '历史任务' },
  { key: '/settings', icon: <SettingOutlined />, label: '设置' },
];

const MainLayout: React.FC = () => {
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
        <Header style={{ padding: '0 24px', background: '#fff', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 56 }}>
          <Title level={4} style={{ margin: 0 }}>私人摄影团队 MVP</Title>
          <Space>
            <Link to="/admin/conversations"><Button type="primary" ghost>管理后台</Button></Link>
            <Button onClick={() => { logout(); navigate('/login'); }}>退出</Button>
          </Space>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8, minHeight: 'calc(100vh - 56px - 48px)' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
