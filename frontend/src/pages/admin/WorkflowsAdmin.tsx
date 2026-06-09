import React, { useEffect, useState } from 'react';
import { Card, Collapse, message, Table, Tag } from 'antd';
import { adminList } from '../../services/adminApi';

type Workflow = {
  workflow_id: string;
  name: string;
  description?: string;
  status: string;
  version: number;
  graph_ref?: string;
  steps_json: { id: string; label: string; type: string }[];
};

const WorkflowsAdmin: React.FC = () => {
  const [items, setItems] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    adminList('/api/admin/workflows')
      .then((res) => setItems(Array.isArray(res) ? res : res?.items || []))
      .catch(() => message.error('加载工作流失败'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Card title="生产 Workflow（只读 · P0）">
      <Table
        rowKey="workflow_id"
        loading={loading}
        dataSource={items}
        expandable={{
          expandedRowRender: (row) => (
            <Collapse
              items={[{
                key: 'steps',
                label: '步骤列表',
                children: (
                  <ol>
                    {(row.steps_json || []).map((s) => (
                      <li key={s.id}><Tag>{s.type}</Tag> {s.label} ({s.id})</li>
                    ))}
                  </ol>
                ),
              }]}
            />
          ),
        }}
        columns={[
          { title: 'ID', dataIndex: 'workflow_id' },
          { title: '名称', dataIndex: 'name' },
          { title: 'Graph', dataIndex: 'graph_ref' },
          { title: '状态', dataIndex: 'status', render: (s) => <Tag color="green">{s}</Tag> },
          { title: '版本', dataIndex: 'version', width: 80 },
        ]}
      />
    </Card>
  );
};

export default WorkflowsAdmin;
