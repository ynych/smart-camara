import React, { useState } from 'react';
import { Button, Card, Form, Input, Typography, message } from 'antd';
import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { isAuthenticated, login } from '../utils/auth';

const { Title, Text } = Typography;

const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(false);
  const from = (location.state as { from?: string })?.from || '/studio';

  if (isAuthenticated()) {
    return <Navigate to={from} replace />;
  }

  const onFinish = (values: { username: string; password: string }) => {
    setLoading(true);
    if (login(values.username, values.password)) {
      message.success('登录成功');
      navigate(from, { replace: true });
    } else {
      message.error('账号或密码错误');
    }
    setLoading(false);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f5f5' }}>
      <Card style={{ width: 380, boxShadow: '0 4px 24px rgba(0,0,0,.08)' }}>
        <Title level={3} style={{ textAlign: 'center', marginBottom: 8 }}>私人摄影团队</Title>
        <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginBottom: 24 }}>登录后状态保存在本浏览器，无需重复登录</Text>
        <Form layout="vertical" onFinish={onFinish} initialValues={{ username: 'admin' }}>
          <Form.Item name="username" label="账号" rules={[{ required: true, message: '请输入账号' }]}>
            <Input prefix={<UserOutlined />} placeholder="admin" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>登录</Button>
        </Form>
      </Card>
    </div>
  );
};

export default Login;
