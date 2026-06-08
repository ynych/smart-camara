import React, { useEffect, useState } from 'react';
import { Button, Card, Col, Input, Row, Select, Space, Typography, message } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import { getHarnessTools, runHarnessTool } from '../services/api';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

const DEFAULT_CONTEXT = `{
  "model_id": "",
  "clothing_ids": [],
  "reference_id": "",
  "model_desc": "优雅的亚洲女性模特",
  "clothing_desc": "时尚服装",
  "scene_desc": "电商Lookbook拍摄场景",
  "style_hint": "",
  "seedream_image_slots": []
}`;

const HarnessTools: React.FC = () => {
  const [tools, setTools] = useState<any[]>([]);
  const [selectedTool, setSelectedTool] = useState<string>();
  const [contextJson, setContextJson] = useState(DEFAULT_CONTEXT);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getHarnessTools()
      .then((res) => {
        const list = res.data.tools || [];
        setTools(list);
        if (list.length) setSelectedTool(list[0].id);
      })
      .catch(() => message.error('加载 Tool 列表失败'));
  }, []);

  const handleRun = async () => {
    if (!selectedTool) return;
    let context: Record<string, unknown>;
    try {
      context = JSON.parse(contextJson);
    } catch {
      message.error('Context JSON 格式错误');
      return;
    }
    setLoading(true);
    try {
      const res = await runHarnessTool(selectedTool, context);
      setResult(res.data);
      message.success('Tool 执行完成');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '执行失败');
    } finally {
      setLoading(false);
    }
  };

  const current = tools.find((t) => t.id === selectedTool);

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Harness Tool 调试台</h2>
      <Text type="secondary">选择 Skill Tool，输入 JSON 上下文，查看输出（MVP 内置 5 个 Tool）。</Text>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={10}>
          <Card title="输入" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Select
                style={{ width: '100%' }}
                placeholder="选择 Tool"
                value={selectedTool}
                onChange={setSelectedTool}
                options={tools.map((t) => ({ value: t.id, label: `${t.name} (${t.id})` }))}
              />
              {current && (
                <Paragraph type="secondary" style={{ fontSize: 12, margin: 0 }}>
                  关联模块：{(current.module_ids || []).join(', ') || '无'}
                </Paragraph>
              )}
              <TextArea rows={16} value={contextJson} onChange={(e) => setContextJson(e.target.value)} />
              <Button type="primary" icon={<PlayCircleOutlined />} loading={loading} onClick={handleRun}>
                运行 Tool
              </Button>
            </Space>
          </Card>
        </Col>
        <Col span={14}>
          <Card title="输出" size="small">
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, maxHeight: 480, overflow: 'auto' }}>
              {result ? JSON.stringify(result, null, 2) : '（等待运行）'}
            </pre>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default HarnessTools;
