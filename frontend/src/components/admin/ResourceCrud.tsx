import React, { useCallback, useEffect, useState } from 'react';
import { Button, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Table, message } from 'antd';
import type { FieldDef, ResourceDef } from '../../admin/adminResources';
import { adminCreate, adminDelete, adminList, adminUpdate } from '../../services/adminApi';

const { TextArea } = Input;

type Props = { resource: ResourceDef };

const parseJson = (v: string) => {
  try {
    return JSON.parse(v);
  } catch {
    return v;
  }
};

const ResourceCrud: React.FC<Props> = ({ resource }) => {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await adminList(resource.apiPath));
    } catch {
      message.error('加载失败');
    } finally {
      setLoading(false);
    }
  }, [resource.apiPath]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setOpen(true);
  };

  const openEdit = (row: any) => {
    setEditing(row);
    const vals: Record<string, unknown> = {};
    resource.fields.forEach((f) => {
      const v = row[f.key];
      vals[f.key] = f.type === 'json' && (typeof v === 'object' || v === null)
        ? JSON.stringify(v ?? (f.key.endsWith('_json') ? {} : []), null, 2)
        : v;
    });
    form.setFieldsValue(vals);
    setOpen(true);
  };

  const submit = async () => {
    const vals = await form.validateFields();
    const payload: Record<string, unknown> = {};
    resource.fields.forEach((f) => {
      if (vals[f.key] === undefined) return;
      payload[f.key] = f.type === 'json' ? parseJson(vals[f.key]) : vals[f.key];
    });
    try {
      if (editing?.id) {
        await adminUpdate(resource.apiPath, editing.id, payload);
        message.success('已更新');
      } else {
        await adminCreate(resource.apiPath, payload);
        message.success('已创建');
      }
      setOpen(false);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败');
    }
  };

  const renderField = (f: FieldDef) => {
    if (f.type === 'textarea' || f.type === 'json') {
      return <TextArea rows={f.type === 'json' ? 8 : 3} />;
    }
    if (f.type === 'number') {
      return <InputNumber style={{ width: '100%' }} />;
    }
    if (f.type === 'select') {
      return <Select options={f.options} />;
    }
    return <Input />;
  };

  const columns = [
    ...resource.fields.filter((f) => f.table).map((f) => ({
      title: f.label,
      dataIndex: f.key,
      key: f.key,
      ellipsis: true,
      width: f.width,
      render: (v: unknown) => (typeof v === 'object' ? JSON.stringify(v) : String(v ?? '')),
    })),
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_: unknown, row: any) => (
        <Space>
          <Button type="link" size="small" onClick={() => openEdit(row)}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={async () => { await adminDelete(resource.apiPath, row.id); load(); }}>
            <Button type="link" size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>{resource.title}</h2>
        <Space>
          <Button onClick={load}>刷新</Button>
          {!resource.readOnlyCreate && (
            resource.key === 'agents' ? (
              <Button type="primary" disabled title="多 Agent 创建将在后续版本开放">+ 创建 Agent（即将开放）</Button>
            ) : (
              <Button type="primary" onClick={openCreate}>新建</Button>
            )
          )}
        </Space>
      </div>
      <Table rowKey="id" loading={loading} dataSource={items} columns={columns} scroll={{ x: true }} pagination={{ pageSize: 20 }} />
      <Modal title={editing ? '编辑' : '新建'} open={open} onCancel={() => setOpen(false)} onOk={submit} width={720} destroyOnClose>
        <Form form={form} layout="vertical">
          {resource.fields.map((f) => (
            <Form.Item key={f.key} name={f.key} label={f.label} rules={f.required ? [{ required: true }] : undefined}>
              {renderField(f)}
            </Form.Item>
          ))}
        </Form>
      </Modal>
    </div>
  );
};

export default ResourceCrud;
