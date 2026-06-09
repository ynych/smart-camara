import React from 'react';
import { Button, Layout, Menu, Typography } from 'antd';
import {
  HistoryOutlined,
  ApartmentOutlined,
  ExperimentOutlined,
  MessageOutlined,
  PlusCircleOutlined,
  RobotOutlined,
  SwapOutlined,
  ToolOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

const AdminLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = React.useState(false);
  const [openKeys, setOpenKeys] = React.useState<string[]>(['harness']);

  const path = location.pathname;

  const menuItems = [
    { key: '/admin/new-task', icon: <PlusCircleOutlined />, label: 'New Task' },
    { key: '/admin/conversations', icon: <MessageOutlined />, label: 'Conversations' },
    { key: '/admin/runs', icon: <HistoryOutlined />, label: 'Runs' },
    { key: '/admin/agents', icon: <RobotOutlined />, label: 'Agents' },
    { key: '/admin/skills', icon: <ToolOutlined />, label: 'Skills' },
    {
      key: 'harness',
      icon: <ExperimentOutlined />,
      label: 'Harness',
      children: [
        { key: '/admin/harness/generation-packs', label: 'Generation Packs' },
        { key: '/admin/harness/workflows', label: 'Workflows' },
        { key: '/admin/harness/testcases', label: 'TestCases' },
        { key: '/admin/harness/versions', icon: <SwapOutlined />, label: 'Versions' },
        { key: '/admin/harness/pipeline', icon: <ApartmentOutlined />, label: 'Pipeline' },
        { key: '/admin/harness/tools', label: 'Tools' },
        { key: '/admin/harness/regression', icon: <TrophyOutlined />, label: 'Regression' },
      ],
    },
  ];

  const selectedKey = path.startsWith('/admin/harness') ? path
    : path.startsWith('/admin/agents/studio') ? '/admin/agents'
    : menuItems.some((m) => m.key === path) ? path
    : path;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={240}
        className="admin-sider"
        style={{ height: '100vh', position: 'fixed', left: 0, top: 0, bottom: 0, overflow: 'hidden' }}
      >
        <div className="admin-sider-inner">
          <div className="logo admin-sider-logo">
            <RobotOutlined style={{ fontSize: 22, color: '#722ed1' }} />
            {!collapsed && <span className="logo-text">管理后台</span>}
          </div>
          <div className="admin-sider-menu">
            <Menu
              theme="dark"
              mode="inline"
              selectedKeys={[selectedKey]}
              openKeys={collapsed ? [] : openKeys}
              onOpenChange={setOpenKeys}
              items={menuItems}
              onClick={({ key }) => key.startsWith('/') && navigate(key)}
            />
          </div>
        </div>
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 240, transition: 'margin-left 0.2s' }}>
        <Header style={{ padding: '0 24px', background: '#fff', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 56 }}>
          <Title level={4} style={{ margin: 0 }}>Agent 平台 · 纯本地</Title>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <Text type="secondary">MVP 开放权限</Text>
            <Link to="/studio"><Button>返回工作台</Button></Link>
          </div>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8, minHeight: 'calc(100vh - 56px - 48px)' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AdminLayout;
