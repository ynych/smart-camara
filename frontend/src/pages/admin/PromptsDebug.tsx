import React, { useEffect, useState } from 'react';
import { Button, Card, Col, Input, Row, Select, Space, Typography, message } from 'antd';
import { adminList } from '../../services/adminApi';
import { runHarnessPipeline } from '../../services/api';

const { TextArea } = Input;
const { Text } = Typography;

const PromptsDebug: React.FC = () => {
  const [packs, setPacks] = useState<any[]>([]);
  const [selected, setSelected] = useState<string>();
  const [contextJson, setContextJson] = useState('{"angle_name":"正面全身","angle_desc":"正面展示"}');
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    adminList('/api/admin/prompt-packs').then(setPacks).catch(() => message.error('加载提示词包失败'));
  }, []);

  const run = async () => {
    const pack = packs.find((p) => p.id === selected);
    if (!pack) {
      message.warning('请选择提示词包');
      return;
    }
    let context: Record<string, unknown>;
    try {
      context = JSON.parse(contextJson);
    } catch {
      message.error('Context JSON 无效');
      return;
    }
    try {
      const res = await runHarnessPipeline({
        context: { ...context, goal_text: pack.template },
        enabled_modules: [pack.module_id || 'goal'],
        include_regen: false,
      });
      setResult({ pack, pipeline: res.data });
      message.success('已运行');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '运行失败');
    }
  };

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Prompts 调试</h2>
      <Text type="secondary">选择原子提示词包，结合上下文试跑（数据来自「提示词包」CRUD）。</Text>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={10}>
          <Card size="small" title="配置">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Select
                style={{ width: '100%' }}
                placeholder="选择提示词包"
                value={selected}
                onChange={setSelected}
                options={packs.map((p) => ({ value: p.id, label: `${p.domain}/${p.module_id}: ${p.name}` }))}
              />
              <TextArea rows={12} value={contextJson} onChange={(e) => setContextJson(e.target.value)} />
              <Button type="primary" onClick={run}>试跑模块</Button>
            </Space>
          </Card>
        </Col>
        <Col span={14}>
          <Card size="small" title="输出">
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{result ? JSON.stringify(result, null, 2) : '（等待运行）'}</pre>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default PromptsDebug;
