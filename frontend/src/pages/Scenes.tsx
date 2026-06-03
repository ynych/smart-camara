import React, { useState, useEffect } from 'react';
import {
  Table, Button, Modal, Form, Input, Select, Tag, Space, message, Popconfirm
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { getScenes, createScene, updateScene, deleteScene } from '../services/api';

interface Scene {
  id: string;
  name: string;
  type: string;
  description?: string;
  created_at: string;
  updated_at?: string;
}

const Scenes: React.FC = () => {
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingScene, setEditingScene] = useState<Scene | null>(null);
  const [form] = Form.useForm();

  const fetchScenes = async () => {
    setLoading(true);
    try {
      const res = await getScenes();
      setScenes(res.data.scenes || res.data.items || res.data || []);
    } catch (err) {
      message.error('获取场景列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScenes();
  }, []);

  const handleCreate = () => {
    setEditingScene(null);
    form.resetFields();
    setModalOpen(true);
  };

  const handleEdit = (record: Scene) => {
    setEditingScene(record);
    form.setFieldsValue({
      name: record.name,
      type: record.type,
      description: record.description,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingScene) {
        await updateScene(editingScene.id, values);
        message.success('场景更新成功');
      } else {
        await createScene(values);
        message.success('场景创建成功');
      }
      setModalOpen(false);
      form.resetFields();
      setEditingScene(null);
      fetchScenes();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(editingScene ? '更新失败' : '创建失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteScene(id);
      message.success('场景删除成功');
      fetchScenes();
    } catch (err) {
      message.error('删除失败');
    }
  };

  const columns: ColumnsType<Scene> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => (
        <Tag color={type === 'indoor' ? 'blue' : 'green'}>
          {type === 'indoor' ? '室内' : '室外'}
        </Tag>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc: string) => desc || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_: any, record: Scene) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除"
            description="确定要删除这个场景吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新建场景
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={scenes}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
      />

      <Modal
        title={editingScene ? '编辑场景' : '新建场景'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => {
          setModalOpen(false);
          form.resetFields();
          setEditingScene(null);
        }}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="场景名称"
            rules={[{ required: true, message: '请输入场景名称' }]}
          >
            <Input placeholder="请输入场景名称" />
          </Form.Item>
          <Form.Item
            name="type"
            label="场景类型"
            rules={[{ required: true, message: '请选择场景类型' }]}
          >
            <Select placeholder="请选择场景类型">
              <Select.Option value="indoor">室内</Select.Option>
              <Select.Option value="outdoor">室外</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea
              placeholder="请输入场景描述（可选）"
              autoSize={{ minRows: 2, maxRows: 6 }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Scenes;
