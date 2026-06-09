import React from 'react';
import { Button, Card, Empty, Table, Tag } from 'antd';
import { PlusOutlined, RocketOutlined } from '@ant-design/icons';

export type StudioTaskItem = {
  id: string;
  title: string;
  status: string;
  model_name?: string;
  quantity?: number;
  prompts?: { prompt?: string }[];
  updated_at?: string;
  error_message?: string;
};

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  draft: { color: 'default', label: '编辑中' },
  prompts_ready: { color: 'processing', label: '待生图' },
  generating: { color: 'warning', label: '生图中' },
  completed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
};

type Props = {
  tasks: StudioTaskItem[];
  loading: boolean;
  onNew: () => void;
  onOpen: (task: StudioTaskItem) => void;
};

const StudioTaskList: React.FC<Props> = ({ tasks, loading, onNew, onOpen }) => (
  <div>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
      <div>
        <h2 style={{ margin: 0 }}>生图任务</h2>
        <span style={{ color: '#888' }}>每次生成提示词即一条任务，未完成可继续编辑并生图</span>
      </div>
      <Button type="primary" icon={<PlusOutlined />} onClick={onNew}>新建任务</Button>
    </div>
    {tasks.length === 0 && !loading ? (
      <Card><Empty description="暂无任务，点击新建开始"><Button type="primary" onClick={onNew}>新建任务</Button></Empty></Card>
    ) : (
      <Table
        rowKey="id"
        loading={loading}
        dataSource={tasks}
        pagination={{ pageSize: 10 }}
        onRow={(record) => ({ onClick: () => onOpen(record), style: { cursor: 'pointer' } })}
        columns={[
          { title: '任务', dataIndex: 'title', ellipsis: true },
          {
            title: '状态',
            dataIndex: 'status',
            width: 100,
            render: (s: string) => {
              const m = STATUS_MAP[s] || { color: 'default', label: s };
              return <Tag color={m.color}>{m.label}</Tag>;
            },
          },
          {
            title: '提示词',
            width: 90,
            render: (_, r) => `${(r.prompts || []).length} 条`,
          },
          {
            title: '更新',
            dataIndex: 'updated_at',
            width: 160,
            render: (t: string) => (t ? new Date(t).toLocaleString() : '—'),
          },
          {
            title: '',
            width: 100,
            render: (_, r) => (
              <Button
                type={r.status === 'prompts_ready' ? 'primary' : 'link'}
                size="small"
                icon={r.status === 'prompts_ready' ? <RocketOutlined /> : undefined}
                onClick={(e) => { e.stopPropagation(); onOpen(r); }}
              >
                {r.status === 'completed' ? '查看' : '继续'}
              </Button>
            ),
          },
        ]}
      />
    )}
  </div>
);

export default StudioTaskList;
