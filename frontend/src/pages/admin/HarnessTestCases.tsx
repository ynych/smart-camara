import React, { useCallback, useEffect, useState } from 'react';
import { Button, Card, Col, Form, Input, InputNumber, Row, Select, Space, Table, Tag, Typography, message } from 'antd';
import {
  adminCreate, adminList, getDefaultAgent, runHarnessTestcaseEvaluation, runHarnessTestcasePrompts,
} from '../../services/adminApi';

const { TextArea } = Input;
const { Text } = Typography;

const HarnessTestCases: React.FC = () => {
  const [items, setItems] = useState<any[]>([]);
  const [agent, setAgent] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [list, a] = await Promise.all([
        adminList('/api/admin/harness-testcases'),
        getDefaultAgent(),
      ]);
      setItems(list);
      setAgent(a);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const wrapRun = async (id: string, fn: () => Promise<any>, okMsg: string) => {
    setRunningId(id);
    try {
      await fn();
      message.success(okMsg);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '运行失败');
    } finally {
      setRunningId(null);
    }
  };

  const saveNew = async (vals: any) => {
    await adminCreate('/api/admin/harness-testcases', {
      ...vals,
      agent_id: agent?.id,
      clothing_ids_json: JSON.parse(vals.clothing_ids_json || '[]'),
      business_context_json: JSON.parse(vals.business_context_json || '{}'),
      status: 'draft',
    });
    message.success('已创建');
    form.resetFields();
    load();
  };

  const columns = [
    { title: '名称', dataIndex: 'name', ellipsis: true },
    { title: '模特', dataIndex: 'model_id', width: 100, ellipsis: true },
    {
      title: '人评',
      width: 80,
      render: (_: unknown, row: any) => (
        row.source_image_id ? <Tag color="purple">已关联</Tag> : '—'
      ),
    },
    { title: '尺寸', dataIndex: 'size', width: 70 },
    { title: '数量', dataIndex: 'quantity', width: 60 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (s: string) => (
        <Tag color={s === 'passed' ? 'green' : s === 'failed' ? 'red' : 'default'}>{s}</Tag>
      ),
    },
    {
      title: 'Pass',
      dataIndex: 'pass_label',
      width: 60,
      render: (v: number) => (v === 1 ? <Tag color="green">✓</Tag> : v === 0 ? <Tag color="red">✗</Tag> : '—'),
    },
    {
      title: '操作',
      key: 'act',
      width: 180,
      render: (_: unknown, row: any) => (
        <Space size={0} wrap>
          <Button
            type="link"
            size="small"
            loading={runningId === row.id}
            onClick={() => wrapRun(row.id, () => runHarnessTestcasePrompts(row.id), '提示词已生成')}
          >
            Agent
          </Button>
          <Button
            type="link"
            size="small"
            disabled={!!runningId}
            onClick={() => wrapRun(row.id, () => runHarnessTestcaseEvaluation(row.id), '评价已写入')}
          >
            评价
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Harness · TestCases</h2>
      <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
        样本：需求+素材 → Agent 提示词 → 文本 Judge + SQLite 专家人评（双轨）。生图请在用户平台 /studio；评价可从 Gallery 导入。
      </Text>
      <Row gutter={16}>
        <Col span={14}>
          <Card title="TestCase 列表" size="small">
            <Table rowKey="id" loading={loading} dataSource={items} columns={columns} pagination={{ pageSize: 10 }} />
          </Card>
        </Col>
        <Col span={10}>
          <Card title="新建 TestCase" size="small">
            <Form form={form} layout="vertical" onFinish={saveNew} initialValues={{ size: '3:4', quantity: 4, clothing_ids_json: '[]', business_context_json: '{"merchant_need":"","target_audience":""}' }}>
              <Form.Item name="name" label="名称" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="model_id" label="模特 ID"><Input /></Form.Item>
              <Form.Item name="clothing_ids_json" label="服装 IDs (JSON)"><TextArea rows={2} /></Form.Item>
              <Form.Item name="reference_id" label="参考图 ID"><Input /></Form.Item>
              <Form.Item name="business_context_json" label="商家需求/画像 (JSON)"><TextArea rows={3} /></Form.Item>
              <Form.Item name="size" label="尺寸"><Select options={[{ value: '1:1' }, { value: '3:4' }, { value: '9:16' }]} /></Form.Item>
              <Form.Item name="quantity" label="数量"><InputNumber min={1} max={8} style={{ width: '100%' }} /></Form.Item>
              <Form.Item name="acceptance_criteria" label="验收标准"><TextArea rows={2} /></Form.Item>
              <Button type="primary" htmlType="submit">创建</Button>
            </Form>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default HarnessTestCases;
