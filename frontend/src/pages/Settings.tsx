import React, { useState, useEffect } from 'react';
import { Card, Form, Input, Button, message, Space, Divider, Alert } from 'antd';
import { getConfig, updateConfig, testConfig, testChatConfig } from '../services/api';

const Settings: React.FC = () => {
  const [configs, setConfigs] = useState<any[]>([]);
  const [testResult, setTestResult] = useState<any>(null);
  const [chatTestResult, setChatTestResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const res = await getConfig();
      setConfigs(res.data.configs || []);
    } catch {
      message.error('加载配置失败');
    }
  };

  const handleSave = async (values: any) => {
    try {
      await updateConfig(values);
      message.success('配置已保存');
      loadConfig();
    } catch {
      message.error('保存失败');
    }
  };

  const handleTestChat = async () => {
    setChatLoading(true);
    setChatTestResult(null);
    try {
      const res = await testChatConfig();
      setChatTestResult(res.data);
    } catch {
      setChatTestResult({ success: false, error: '连接失败' });
    } finally {
      setChatLoading(false);
    }
  };

  const handleTest = async () => {
    setLoading(true);
    setTestResult(null);
    try {
      const res = await testConfig();
      setTestResult(res.data);
    } catch {
      setTestResult({ success: false, error: '连接失败' });
    } finally {
      setLoading(false);
    }
  };

  const volcanoConfig = configs.find((c) => c.provider === 'volcano');
  const chatConfig = configs.find((c) => c.provider === 'volcano_chat');

  return (
    <div style={{ maxWidth: 640 }}>
      <h2>设置</h2>
      <Card title="火山引擎 · 生图（Seedream）">
        <Form
          layout="vertical"
          initialValues={{
            provider: 'volcano',
            endpoint: volcanoConfig?.endpoint || '',
            model: volcanoConfig?.model || 'seedream',
          }}
          onFinish={handleSave}
        >
          <Form.Item name="provider" hidden><Input /></Form.Item>
          <Form.Item name="api_key" label="API Key" rules={[{ required: !volcanoConfig?.api_key_masked }]}>
            <Input.Password placeholder={volcanoConfig?.api_key_masked ? '留空则保持原 Key' : '输入 API Key'} />
          </Form.Item>
          <Form.Item name="endpoint" label="生图推理端点" rules={[{ required: true }]}>
            <Input placeholder="Seedream endpoint ID" />
          </Form.Item>
          <Form.Item name="model" label="模型标识">
            <Input placeholder="seedream" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">保存</Button>
              <Button onClick={handleTest} loading={loading}>测试生图连接</Button>
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

      <Card title="火山引擎 · 对话模型（提示词生成）">
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="VOLCANO_CHAT_ENDPOINT 须为 ep- 对话接入点，且与 VOLCANO_API_KEY 同属一个火山项目。ark- 应用 ID 若与 API Key 不匹配会调用失败。"
        />
        <Form
          layout="vertical"
          initialValues={{
            provider: 'volcano_chat',
            endpoint: chatConfig?.endpoint || '',
            model: chatConfig?.model || 'doubao',
          }}
          onFinish={handleSave}
        >
          <Form.Item name="provider" hidden><Input /></Form.Item>
          <Form.Item name="api_key" label="API Key">
            <Input.Password placeholder={chatConfig?.api_key_masked ? '留空则保持原 Key' : '默认可复用 VOLCANO_API_KEY'} />
          </Form.Item>
          <Form.Item name="endpoint" label="对话接入点 ID" rules={[{ required: true }]}>
            <Input placeholder="ep-xxx（豆包对话接入点，非 Seedream 生图 ep）" />
          </Form.Item>
          <Form.Item name="model" label="备注名称">
            <Input placeholder="doubao" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">保存对话模型</Button>
              <Button onClick={handleTestChat} loading={chatLoading}>测试对话模型</Button>
            </Space>
          </Form.Item>
        </Form>
        {chatTestResult && (
          <Alert
            type={chatTestResult.success ? 'success' : 'error'}
            message={chatTestResult.success ? '对话模型可用' : '对话模型不可用'}
            description={chatTestResult.error || `接入点: ${chatTestResult.endpoint || ''} (${chatTestResult.api_mode || ''})`}
            showIcon
            style={{ marginTop: 16 }}
          />
        )}
      </Card>

      <Divider />

      <Card title="使用说明" size="small">
        <p>生图使用 Seedream；提示词由 Ark 对话模型生成，未配置或调用失败时回退模板。</p>
        <p>历史任务在侧栏「历史任务」查看，支持按模特/服装/参考图/任务 ID 筛选。</p>
      </Card>
    </div>
  );
};

export default Settings;
