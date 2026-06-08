import React, { useEffect, useState } from 'react';
import {
  Button, Card, Col, Input, Row, Select, Space, Typography, message,
} from 'antd';
import { PlayCircleOutlined, SendOutlined } from '@ant-design/icons';
import {
  chatAgent, getDefaultAgent, invokeAgent, runAgentTestCase,
} from '../../services/adminApi';
import { adminList } from '../../services/adminApi';

const { TextArea } = Input;
const { Paragraph, Text } = Typography;

const AgentStudio: React.FC = () => {
  const [agent, setAgent] = useState<any>(null);
  const [testCases, setTestCases] = useState<any[]>([]);
  const [selectedCase, setSelectedCase] = useState<string>();
  const [inputsJson, setInputsJson] = useState('{}');
  const [runResult, setRunResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [chatLog, setChatLog] = useState<{ role: string; content: string }[]>([]);
  const [sessionId, setSessionId] = useState<string>();

  useEffect(() => {
    getDefaultAgent().then((a) => {
      setAgent(a);
      adminList('/api/admin/test-cases').then((items) => {
        const mine = items.filter((t: any) => t.agent_id === a.id);
        setTestCases(mine);
        if (mine[0]) {
          setSelectedCase(mine[0].id);
          const inp = mine[0].inputs_json || mine[0].inputs;
          setInputsJson(JSON.stringify(typeof inp === 'string' ? JSON.parse(inp) : inp, null, 2));
        }
      });
    }).catch(() => message.error('加载 Agent 失败'));
  }, []);

  const loadCase = (id: string) => {
    const c = testCases.find((t) => t.id === id);
    if (!c) return;
    const inp = c.inputs_json || c.inputs;
    setInputsJson(JSON.stringify(typeof inp === 'string' ? JSON.parse(inp) : inp, null, 2));
  };

  const runDebug = async () => {
    if (!agent) return;
    setLoading(true);
    try {
      let result;
      if (selectedCase) {
        result = await runAgentTestCase(agent.id, selectedCase);
      } else {
        result = await invokeAgent(agent.id, JSON.parse(inputsJson));
      }
      setRunResult(result.result || result);
      message.success('运行完成');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '运行失败');
    } finally {
      setLoading(false);
    }
  };

  const sendChat = async () => {
    if (!agent || !chatInput.trim()) return;
    setChatLog((l) => [...l, { role: 'user', content: chatInput }]);
    try {
      const res = await chatAgent(agent.id, chatInput, sessionId);
      setSessionId(res.session_id);
      setChatLog((l) => [...l, { role: 'assistant', content: res.reply }]);
      if (res.invoke_result) {
        setRunResult(res.invoke_result);
      }
      setChatInput('');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '对话失败');
    }
  };

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Agent 工作室</h2>
      {agent && (
        <Text type="secondary">{agent.name} ({agent.slug}) · {agent.status}</Text>
      )}
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="TestCase 调试" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Select
                style={{ width: '100%' }}
                placeholder="选择 TestCase"
                value={selectedCase}
                onChange={(v) => { setSelectedCase(v); loadCase(v); }}
                options={testCases.map((t) => ({ value: t.id, label: t.name }))}
                allowClear
              />
              <TextArea rows={14} value={inputsJson} onChange={(e) => setInputsJson(e.target.value)} />
              <Button type="primary" icon={<PlayCircleOutlined />} loading={loading} onClick={runDebug}>
                运行 Agent
              </Button>
            </Space>
          </Card>
          <Card title="与 Agent 对话" size="small" style={{ marginTop: 16 }}>
            <div style={{ maxHeight: 200, overflow: 'auto', marginBottom: 8, background: '#fafafa', padding: 8, borderRadius: 8 }}>
              {chatLog.map((m, i) => (
                <Paragraph key={i} style={{ marginBottom: 8 }}><Text strong>{m.role === 'user' ? '你' : 'Agent'}：</Text>{m.content}</Paragraph>
              ))}
            </div>
            <Space.Compact style={{ width: '100%' }}>
              <Input value={chatInput} onChange={(e) => setChatInput(e.target.value)} onPressEnter={sendChat} placeholder="补充商家需求、素材 ID…" />
              <Button type="primary" icon={<SendOutlined />} onClick={sendChat}>发送</Button>
            </Space.Compact>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="运行结果" size="small">
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, maxHeight: 560, overflow: 'auto' }}>
              {runResult ? JSON.stringify(runResult, null, 2) : '（等待运行）'}
            </pre>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AgentStudio;
