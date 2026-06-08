import React, { useEffect, useState } from 'react';
import { Table, Tabs, Tag } from 'antd';
import { getGallery } from '../../services/api';
import { adminList } from '../../services/adminApi';

const TaskList: React.FC = () => {
  const [lookbook, setLookbook] = useState<any[]>([]);
  const [harness, setHarness] = useState<any[]>([]);

  useEffect(() => {
    getGallery().then((r) => setLookbook(r.data.gallery || []));
    adminList('/api/admin/harness-testcases').then(setHarness);
  }, []);

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Your Task List</h2>
      <Tabs
        items={[
          {
            key: 'lookbook',
            label: 'Lookbook 任务',
            children: (
              <Table
                rowKey="task_id"
                dataSource={lookbook}
                columns={[
                  { title: '任务', dataIndex: 'task_id', ellipsis: true, render: (v: string) => v?.slice(0, 12) + '…' },
                  { title: '状态', dataIndex: 'status', render: (s: string) => <Tag>{s}</Tag> },
                  { title: '张数', render: (_: unknown, r: any) => r.images?.length },
                  { title: '时间', dataIndex: 'created_at', width: 180 },
                ]}
                pagination={{ pageSize: 15 }}
              />
            ),
          },
          {
            key: 'harness',
            label: 'Harness TestCases',
            children: (
              <Table
                rowKey="id"
                dataSource={harness}
                columns={[
                  { title: '名称', dataIndex: 'name' },
                  { title: '状态', dataIndex: 'status', render: (s: string) => <Tag>{s}</Tag> },
                  { title: '模特', dataIndex: 'model_id', ellipsis: true },
                  { title: '更新', dataIndex: 'updated_at', width: 180 },
                ]}
              />
            ),
          },
        ]}
      />
    </div>
  );
};

export default TaskList;
