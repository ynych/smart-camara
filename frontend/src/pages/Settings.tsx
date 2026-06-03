import React, { useState, useEffect } from 'react';
import { Card, Form, Input, Button, message, Space, Divider, Alert } from 'antd';
import { getConfig, updateConfig, testConfig } from '../services/api';

const Settings: React.FC = () => {
  const [configs, setConfigs] = useState<any[]>([]);
  const [testResult, setTestResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const res = await getConfig();
      setConfigs(res.data.configs || []);
    } catch (e) {
      message.error('加载配置失败');
    }
  };

  const handleSave = async (values: any) => {
    try {
      await updateConfig(values);
      message.success('配置已保存');
      loadConfig();
    } catch (e) {
      message.error('保存失败');
    }
  };

  const handleTest = async () => {
    setLoading(true);
    setTestResult(null);
    try {
      const res = await testConfig();
      setTestResult(res.data);
    } catch (e) {
      setTestResult({ success: false, error: '连接失败' });
    } finally {
      setLoading(false);
    }
  };

  const volcanoConfig = configs.find(c => c.provider === 'volcano');

  return (
    <div style={{ maxWidth: 600 }}>
      <h2>设置</h2>
      <Card title="火山引擎 API 配置">
        <Form layout="vertical" initialValues={{
          provider: 'volcano',
          api_key: volcanoConfig?.api_key_masked ? '' : '',
          endpoint: volcanoConfig?.endpoint || '',
          model: volcanoConfig?.model || 'seedream',
        }} onFinish={handleSave}>
          <Form.Item name="provider" label="服务商"><Input disabled /></Form.Item>
          <Form.Item name="api_key" label="API Key" rules={[{ required: true }]}>
            <Input.Password placeholder="输入API Key" />
          </Form.Item>
          <Form.Item name="endpoint" label="推理端点" rules={[{ required: true }]}>
            <Input placeholder="输入推理端点ID" />
          </Form.Item>
          <Form.Item name="model" label="模型"><Input placeholder="模型名称" /></Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">保存配置</Button>
              <Button onClick={handleTest} loading={loading}>测试连接</Button>
            </Space>
          </Form.Item>
        </Form>
        {testResult && (
          <Alert
            type={testResult.success ? 'success' : 'error'}
            message={testResult.success ? '连接成功' : '连接失败'}
            description={testResult.error || `状态码: ${testResult.status_code}`}
            showIcon
            style={{ marginTop: 16 }}
          />
        )}
      </Card>
      <Divider />
      <Card title="使用说明" size="small">
        <p>当前使用火山引擎 Seedream 模型生成图片。</p>
        <p>免费额度：50张（请合理使用）</p>
        <p>图片尺寸：2048x2048</p>
      </Card>
    </div>
  );
};

export default Settings;
