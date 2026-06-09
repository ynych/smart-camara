import React, { useEffect, useState } from 'react';
import { Button, Card, message, Space, Table, Tag } from 'antd';
import { adminList, default as adminApi } from '../../services/adminApi';

type Pack = {
  id: string;
  slug: string;
  name: string;
  status: string;
  version: number;
  harness_pipeline_slug?: string;
};

const GenerationPacks: React.FC = () => {
  const [items, setItems] = useState<Pack[]>([]);
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    adminList('/api/admin/generation-packs')
      .then((res) => setItems(Array.isArray(res) ? res : res?.items || []))
      .catch(() => message.error('加载生成包失败'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCopy = async (id: string) => {
    try {
      await adminApi.post(`/api/admin/generation-packs/${id}/copy`, {});
      message.success('已复制为 draft');
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '复制失败');
    }
  };

  const handlePublish = async (id: string) => {
    try {
      await adminApi.post(`/api/admin/generation-packs/${id}/publish`, {});
      message.success('已发布并更新 manifest pin');
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '发布失败');
    }
  };

  return (
    <Card title="提示词生成包（PromptGenerationPack）">
      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        columns={[
          { title: '名称', dataIndex: 'name' },
          { title: 'Slug', dataIndex: 'slug' },
          {
            title: '状态',
            dataIndex: 'status',
            render: (s: string) => (
              <Tag color={s === 'published' ? 'green' : s === 'draft' ? 'blue' : 'default'}>{s}</Tag>
            ),
          },
          { title: '版本', dataIndex: 'version', width: 80 },
          { title: 'Pipeline', dataIndex: 'harness_pipeline_slug' },
          {
            title: '操作',
            render: (_, row) => (
              <Space>
                <Button size="small" onClick={() => handleCopy(row.id)}>复制编辑</Button>
                {row.status === 'draft' && (
                  <Button size="small" type="primary" onClick={() => handlePublish(row.id)}>发布</Button>
                )}
              </Space>
            ),
          },
        ]}
      />
    </Card>
  );
};

export default GenerationPacks;
