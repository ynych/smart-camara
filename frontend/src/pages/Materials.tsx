import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Upload, Button, message, Tabs, Image, Popconfirm, Empty, Tag, Space } from 'antd';
import { UploadOutlined, DeleteOutlined, UserOutlined, SkinOutlined, ReloadOutlined } from '@ant-design/icons';
import { listMaterials, uploadMaterials, deleteMaterial, scanMaterials } from '../services/api';

const Materials: React.FC = () => {
  const [materials, setMaterials] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState('model');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadMaterials();
  }, [activeTab]);

  const loadMaterials = async () => {
    setLoading(true);
    try {
      const res = await listMaterials(activeTab);
      setMaterials(res.data.materials || []);
    } catch (e) {
      message.error('加载素材失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (info: any) => {
    const { file, onSuccess, onError } = info;
    const formData = new FormData();
    formData.append('files', file);
    formData.append('category', activeTab);
    try {
      await uploadMaterials(formData);
      message.success('上传成功');
      loadMaterials();
      onSuccess?.();
    } catch (e) {
      message.error('上传失败');
      onError?.();
    }
    return false;
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteMaterial(id);
      message.success('已删除');
      loadMaterials();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const handleScan = async () => {
    try {
      const res = await scanMaterials();
      message.success(`导入${res.data.count || 0}个素材`);
      loadMaterials();
    } catch (e) {
      message.error('导入失败');
    }
  };

  const tabItems = [
    { key: 'model', label: '模特素材', icon: <UserOutlined /> },
    { key: 'clothing', label: '服装素材', icon: <SkinOutlined /> },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>素材管理</h2>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleScan}>扫描默认素材</Button>
          <Upload multiple beforeUpload={handleUpload} showUploadList={false}>
            <Button icon={<UploadOutlined />} type="primary">上传素材</Button>
          </Upload>
        </Space>
      </div>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      {materials.length === 0 ? (
        <Empty description={`暂无${activeTab === 'model' ? '模特' : '服装'}素材`} />
      ) : (
        <Row gutter={[16, 16]}>
          {materials.map((m: any) => (
            <Col span={6} key={m.id}>
              <Card size="small" cover={
                <Image src={`/assets/uploads/${m.file_path?.split('/').pop()}`} alt={m.name} style={{ height: 200, objectFit: 'cover' }} />
              } actions={[
                <Popconfirm title="确定删除?" onConfirm={() => handleDelete(m.id)}>
                  <Button danger size="small" icon={<DeleteOutlined />}>删除</Button>
                </Popconfirm>
              ]}>
                <Card.Meta title={m.name} description={<Tag>{m.type === 'upload' ? '上传' : 'AI生成'}</Tag>} />
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  );
};

export default Materials;
