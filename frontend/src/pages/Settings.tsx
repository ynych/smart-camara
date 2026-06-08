import React, { useState, useEffect } from 'react';
import { Card, Form, Input, Button, message, Space, Divider, Alert } from 'antd';
import { getConfig, updateConfig, testConfig, testChatConfig } from '../services/api';

const VOLCANO_ENDPOINT_CONSOLE =
  'https://console.volcengine.com/ark/region:ark+cn-beijing/endpoint?projectName=default';

function endpointIssue(endpoint?: string): string | null {
  const ep = (endpoint || '').trim();
  if (!ep) {
    return '尚未配置豆包对话接入点（ep-）。提示词 Agent 会回退 Harness 模板；请在下方填写或在 .env 设置 VOLCANO_CHAT_ENDPOINT 后重启后端。';
  }
  if (ep.startsWith('ark-')) {
    return '当前填的是 ark- 应用 ID，不能用于对话 API。请在火山方舟「在线推理」创建豆包对话接入点，使用 ep- 开头的 ID。';
  }
  return null;
}

const Settings: React.FC = () => {
  const [volcanoForm] = Form.useForm();
  const [chatForm] = Form.useForm();
  const [configs, setConfigs] = useState<any[]>([]);
  const [testResult, setTestResult] = useState<any>(null);
  const [chatTestResult, setChatTestResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);

  const volcanoConfig = configs.find((c) => c.provider === 'volcano');
  const chatConfig = configs.find((c) => c.provider === 'volcano_chat');
  const chatEndpointIssue = endpointIssue(chatConfig?.endpoint);

  const loadConfig = async () => {
    try {
      const res = await getConfig();
      const list = res.data.configs || [];
      setConfigs(list);
      const vol = list.find((c: any) => c.provider === 'volcano');
      const chat = list.find((c: any) => c.provider === 'volcano_chat');
      volcanoForm.setFieldsValue({
        provider: 'volcano',
        endpoint: vol?.endpoint || '',
        model: vol?.model || 'seedream',
      });
      chatForm.setFieldsValue({
        provider: 'volcano_chat',
        endpoint: chat?.endpoint || '',
        model: chat?.model || 'doubao',
      });
    } catch {
      message.error('加载配置失败');
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  const handleSave = async (values: any) => {
    try {
      await updateConfig(values);
      message.success('配置已保存，请重启后端或重新测试');
      loadConfig();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败');
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

  return (
    <div style={{ maxWidth: 640 }}>
      <h2>设置</h2>

      {chatEndpointIssue && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message="对话模型配置错误（导致提示词回退 Harness 模板）"
          description={
            <>
              <p style={{ marginBottom: 8 }}>{chatEndpointIssue}</p>
              <p style={{ marginBottom: 0 }}>
                {chatConfig?.endpoint ? (
                  <>当前值：<code>{chatConfig.endpoint.slice(0, 36)}{chatConfig.endpoint.length > 36 ? '…' : ''}</code></>
                ) : (
                  <>当前值：<code>（空）</code></>
                )}
                {' · '}
                <a href={VOLCANO_ENDPOINT_CONSOLE} target="_blank" rel="noreferrer">
                  打开火山方舟 · 在线推理
                </a>
              </p>
            </>
          }
        />
      )}

      <Card title="火山引擎 · 生图（Seedream）">
        <Form form={volcanoForm} layout="vertical" onFinish={handleSave}>
          <Form.Item name="provider" hidden><Input /></Form.Item>
          <Form.Item name="api_key" label="API Key">
            <Input.Password placeholder={volcanoConfig?.api_key_masked ? '留空则保持原 Key' : '输入 API Key'} />
          </Form.Item>
          <Form.Item name="endpoint" label="生图推理端点 (ep-)" rules={[{ required: true }]}>
            <Input placeholder="Seedream ep-xxx" />
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
          message="须填写 ep- 豆包对话接入点；Doubao-2.0 使用 /api/v3/responses，API Key 可与生图 Key 不同（VOLCANO_CHAT_API_KEY）。"
        />
        <Form form={chatForm} layout="vertical" onFinish={handleSave}>
          <Form.Item name="provider" hidden><Input /></Form.Item>
          <Form.Item name="api_key" label="API Key">
            <Input.Password placeholder={chatConfig?.api_key_masked ? '留空则保持原 Key' : '默认可复用 VOLCANO_API_KEY'} />
          </Form.Item>
          <Form.Item
            name="endpoint"
            label="对话接入点 ID"
            rules={[{ required: true }]}
            extra={
              <a href={VOLCANO_ENDPOINT_CONSOLE} target="_blank" rel="noreferrer">
                控制台创建接入点 →
              </a>
            }
          >
            <Input placeholder="ep-xxx（豆包 Pro/Lite 对话）" />
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
            description={chatTestResult.error || `接入点: ${chatTestResult.endpoint || ''}`}
            showIcon
            style={{ marginTop: 16 }}
          />
        )}
      </Card>

      <Divider />

      <Card title="使用说明" size="small">
        <p>生图：<code>ep-</code> Seedream；提示词：<code>ep-</code> 豆包对话。配置错误时会回退 Harness 模板组装。</p>
        <p>修改 .env 后需重启后端；也可在本页保存（写入 SQLite），立即生效。</p>
      </Card>
    </div>
  );
};

export default Settings;
