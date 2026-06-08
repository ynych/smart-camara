import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Button, Card, Descriptions, Drawer, Select, Space, Table, Tag, Typography, message,
} from 'antd';
import { adminGet, adminList, syncPromptfooTests } from '../../services/adminApi';

const { Text } = Typography;

const RUN_TYPE_LABELS: Record<string, string> = {
  generate_prompt: '提示词生成',
  chat: 'Agent 对话',
  harness_images: 'Harness 生图',
  harness_eval: 'Harness 评价',
  golden_regression: '黄金集回归',
};

const AgentRuns: React.FC = () => {
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get('id');
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState<string | undefined>();
  const [detail, setDetail] = useState<any>(null);
  const [syncing, setSyncing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await adminList('/api/admin/agent-runs');
      setItems(list.sort((a: any, b: any) => (b.created_at || '').localeCompare(a.created_at || '')));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!highlightId) return;
    adminGet('/api/admin/agent-runs', highlightId)
      .then(setDetail)
      .catch(() => message.warning('运行记录不存在'));
  }, [highlightId]);

  const filtered = useMemo(() => {
    if (!filterType) return items;
    return items.filter((i) => i.run_type === filterType);
  }, [items, filterType]);

  const syncPromptfoo = async () => {
    setSyncing(true);
    try {
      const res = await syncPromptfooTests();
      message.success(`已导出 ${res.count} 条到 ${res.path}`);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '导出失败');
    } finally {
      setSyncing(false);
    }
  };

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 170,
      render: (v: string) => (v ? new Date(v).toLocaleString() : '—'),
    },
    {
      title: '类型',
      dataIndex: 'run_type',
      width: 120,
      render: (t: string) => <Tag>{RUN_TYPE_LABELS[t] || t}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (s: string) => (
        <Tag color={s === 'success' ? 'green' : s === 'failed' ? 'red' : 'blue'}>{s}</Tag>
      ),
    },
    { title: '耗时(ms)', dataIndex: 'duration_ms', width: 90 },
    { title: 'Agent', dataIndex: 'agent_id', width: 100, ellipsis: true },
    { title: '关联', dataIndex: 'ref_id', width: 100, ellipsis: true },
    {
      title: '操作',
      key: 'act',
      width: 80,
      render: (_: unknown, row: any) => (
        <Button type="link" size="small" onClick={() => setDetail(row)}>详情</Button>
      ),
    },
  ];

  const renderJson = (value: unknown) => (
    <pre style={{ maxHeight: 280, overflow: 'auto', fontSize: 12, background: '#fafafa', padding: 12, borderRadius: 8 }}>
      {JSON.stringify(value, null, 2)}
    </pre>
  );

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Runs · 运行账本</h2>
      <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
        本地 SQLite 记录 Agent / Harness 每次运行（替代 Langfuse）。Promptfoo 用例可从 TestCases 自动导出。
      </Text>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            allowClear
            placeholder="按类型筛选"
            style={{ width: 180 }}
            value={filterType}
            onChange={setFilterType}
            options={Object.entries(RUN_TYPE_LABELS).map(([value, label]) => ({ value, label }))}
          />
          <Button onClick={load}>刷新</Button>
          <Button loading={syncing} onClick={syncPromptfoo}>导出 Promptfoo tests</Button>
        </Space>
      </Card>
      <Table rowKey="id" loading={loading} dataSource={filtered} columns={columns} pagination={{ pageSize: 15 }} />

      <Drawer
        title="运行详情"
        width={640}
        open={!!detail}
        onClose={() => setDetail(null)}
      >
        {detail && (
          <>
            <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="ID">{detail.id}</Descriptions.Item>
              <Descriptions.Item label="类型">{RUN_TYPE_LABELS[detail.run_type] || detail.run_type}</Descriptions.Item>
              <Descriptions.Item label="状态">{detail.status}</Descriptions.Item>
              <Descriptions.Item label="耗时">{detail.duration_ms ?? '—'} ms</Descriptions.Item>
              {detail.error_message && (
                <Descriptions.Item label="错误">{detail.error_message}</Descriptions.Item>
              )}
            </Descriptions>
            <Text strong>输入</Text>
            {renderJson(detail.input_json || detail.input)}
            <Text strong style={{ display: 'block', marginTop: 12 }}>输出</Text>
            {renderJson(detail.output_json || detail.output)}
            {(detail.steps_json || detail.steps)?.length > 0 && (
              <>
                <Text strong style={{ display: 'block', marginTop: 12 }}>步骤</Text>
                {renderJson(detail.steps_json || detail.steps)}
              </>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
};

export default AgentRuns;
