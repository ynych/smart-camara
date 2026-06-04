import React, { useState, useEffect } from 'react';
import {
  Card, Row, Col, Button, message, Tabs, Image, Popconfirm, Empty, Tag, Space,
  Collapse, Spin, Select, Modal, Upload, Input, Form,
} from 'antd';
import { UploadOutlined, DeleteOutlined, UserOutlined, SkinOutlined, PictureOutlined } from '@ant-design/icons';
import { uploadMaterials, deleteMaterial, getGroupedMaterials } from '../services/api';
import { toMediaUrl, mediaPreview } from '../utils/mediaUrl';

const SHOOT_TYPES = ['人台图', '平铺图', '时尚拍摄'];

const categoryMap: Record<string, string> = {
  model_cards: 'model',
  clothing: 'clothing',
  lookbook_refs: 'lookbook_ref',
};

const Materials: React.FC = () => {
  const [groupedData, setGroupedData] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('model_cards');
  const [loading, setLoading] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [filterOutfitSet, setFilterOutfitSet] = useState<string | undefined>();
  const [filterShootType, setFilterShootType] = useState<string | undefined>();
  const [uploadForm] = Form.useForm();

  useEffect(() => {
    loadGroupedMaterials();
  }, [activeTab, filterOutfitSet, filterShootType]);

  const loadGroupedMaterials = async () => {
    setLoading(true);
    try {
      const params: { sections?: string; outfit_set?: string; shoot_type?: string } = {};
      if (activeTab === 'model_cards') params.sections = 'model';
      else if (activeTab === 'clothing') {
        params.sections = 'clothing';
        if (filterOutfitSet) params.outfit_set = filterOutfitSet;
        if (filterShootType) params.shoot_type = filterShootType;
      } else if (activeTab === 'lookbook_refs') params.sections = 'refs';
      const res = await getGroupedMaterials(params);
      setGroupedData(res.data || {});
    } catch {
      message.error('加载素材失败');
    } finally {
      setLoading(false);
    }
  };

  const openUploadModal = () => {
    uploadForm.setFieldsValue({
      outfit_set: filterOutfitSet || '',
      shoot_type: filterShootType || '人台图',
    });
    setUploadOpen(true);
  };

  const handleUploadSubmit = async () => {
    const fileList = uploadForm.getFieldValue('files') as { originFileObj?: File }[] | undefined;
    const files = (fileList || []).map((f) => f.originFileObj).filter(Boolean) as File[];
    if (files.length === 0) {
      message.warning('请选择要上传的图片');
      return;
    }

    const values = await uploadForm.validateFields().catch(() => null);
    if (!values) return;

    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    formData.append('category', categoryMap[activeTab] || 'clothing');
    if (activeTab === 'clothing') {
      formData.append('outfit_set', values.outfit_set);
      formData.append('shoot_type', values.shoot_type);
    }

    setUploading(true);
    try {
      const res = await uploadMaterials(formData);
      message.success(res.data?.message || `上传 ${res.data?.count || files.length} 个素材`);
      setUploadOpen(false);
      uploadForm.resetFields();
      loadGroupedMaterials();
    } catch (e: any) {
      message.error('上传失败: ' + (e.response?.data?.detail || e.message));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteMaterial(id);
      message.success('已删除');
      loadGroupedMaterials();
    } catch {
      message.error('删除失败');
    }
  };

  const renderCardActions = (id: string) => [
    <Popconfirm key="del" title="确定删除?" onConfirm={() => handleDelete(id)}>
      <Button danger size="small" icon={<DeleteOutlined />}>删除</Button>
    </Popconfirm>,
  ];

  const renderModelCards = () => {
    const modelCards = groupedData?.model_cards || [];
    if (modelCards.length === 0) {
      return <Empty description="暂无模特卡，请点击右上角上传素材" />;
    }
    return (
      <Row gutter={[16, 16]}>
        {modelCards.map((item: any) => (
          <Col span={6} key={item.id}>
            <Card
              size="small"
              hoverable
              cover={
                <Image
                  src={toMediaUrl(item)}
                  alt={item.name}
                  style={{ height: 240, objectFit: 'cover' }}
                  loading="lazy"
                  preview={mediaPreview(item)}
                />
              }
              actions={renderCardActions(item.id)}
            >
              <Card.Meta title={item.name} />
            </Card>
          </Col>
        ))}
      </Row>
    );
  };

  const matchShootType = (item: any, typeName: string) => {
    const st = item.shoot_type || item.sub_type || item.sub_category || '';
    return st === typeName || (typeName === '时尚拍摄' && (!st || st === '未分类'));
  };

  const renderClothing = () => {
    const clothingSets = groupedData?.clothing_sets || [];
    const outfitOptions = groupedData?.outfit_sets || [...new Set(clothingSets.map((s: any) => s.name))];

    if (clothingSets.length === 0) {
      return <Empty description="暂无服装素材，请点击右上角上传素材" />;
    }

    const collapseItems = clothingSets.map((set: any, setIndex: number) => ({
      key: `set-${setIndex}`,
      label: (
        <Space>
          <SkinOutlined />
          <span style={{ fontWeight: 500 }}>{set.name}</span>
          <Tag color="blue">{set.items?.length || 0}件</Tag>
        </Space>
      ),
      children: (
        <Tabs
          type="card"
          size="small"
          items={SHOOT_TYPES.map((typeName) => ({
            key: typeName,
            label: (
              <span>
                {typeName}
                <Tag style={{ marginLeft: 6 }}>
                  {(set.items || []).filter((i: any) => matchShootType(i, typeName)).length}
                </Tag>
              </span>
            ),
            children: (() => {
              const filteredItems = (set.items || []).filter((item: any) => matchShootType(item, typeName));
              if (filteredItems.length === 0) {
                return <Empty description={`暂无${typeName}`} image={Empty.PRESENTED_IMAGE_SIMPLE} />;
              }
              return (
                <Row gutter={[12, 12]}>
                  {filteredItems.map((item: any) => (
                    <Col span={6} key={item.id}>
                      <Card
                        size="small"
                        hoverable
                        cover={
                          <Image
                            src={toMediaUrl(item)}
                            alt={item.name}
                            style={{ height: 180, objectFit: 'cover' }}
                            loading="lazy"
                            preview={mediaPreview(item)}
                          />
                        }
                        actions={renderCardActions(item.id)}
                      >
                        <Card.Meta
                          title={item.name}
                          description={<Tag>{item.shoot_type || item.sub_type || '未分类'}</Tag>}
                        />
                      </Card>
                    </Col>
                  ))}
                </Row>
              );
            })(),
          }))}
        />
      ),
    }));

    return (
      <div>
        <Space wrap style={{ marginBottom: 16 }}>
          <span>服装套装：</span>
          <Select
            allowClear
            placeholder="全部套装"
            style={{ minWidth: 200 }}
            value={filterOutfitSet}
            onChange={setFilterOutfitSet}
            options={outfitOptions.map((name: string) => ({ label: name, value: name }))}
          />
          <span>拍摄类型：</span>
          <Select
            allowClear
            placeholder="全部类型"
            style={{ minWidth: 140 }}
            value={filterShootType}
            onChange={setFilterShootType}
            options={SHOOT_TYPES.map((t) => ({ label: t, value: t }))}
          />
        </Space>
        <Collapse items={collapseItems} defaultActiveKey={[]} />
      </div>
    );
  };

  const renderLookbookRefs = () => {
    const refs = groupedData?.lookbook_refs || [];
    if (refs.length === 0) {
      return <Empty description="暂无 Lookbook 参考图，请点击右上角上传素材" />;
    }
    return (
      <Row gutter={[16, 16]}>
        {refs.map((item: any) => (
          <Col span={6} key={item.id}>
            <Card
              size="small"
              hoverable
              cover={
                <Image
                  src={toMediaUrl(item)}
                  alt={item.name}
                  style={{ height: 240, objectFit: 'cover' }}
                  loading="lazy"
                  preview={mediaPreview(item)}
                />
              }
              actions={renderCardActions(item.id)}
            >
              <Card.Meta title={item.name} />
            </Card>
          </Col>
        ))}
      </Row>
    );
  };

  const tabItems = [
    { key: 'model_cards', label: '模特卡', icon: <UserOutlined /> },
    { key: 'clothing', label: '服装素材', icon: <SkinOutlined /> },
    { key: 'lookbook_refs', label: 'Lookbook参考', icon: <PictureOutlined /> },
  ];

  const categoryLabel = activeTab === 'model_cards' ? '模特卡' : activeTab === 'clothing' ? '服装素材' : 'Lookbook参考';

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>素材管理</h2>
        <Button type="primary" icon={<UploadOutlined />} onClick={openUploadModal}>
          上传素材
        </Button>
      </div>

      <Spin spinning={loading}>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
        {activeTab === 'model_cards' && renderModelCards()}
        {activeTab === 'clothing' && renderClothing()}
        {activeTab === 'lookbook_refs' && renderLookbookRefs()}
      </Spin>

      <Modal
        title={`上传${categoryLabel}`}
        open={uploadOpen}
        onCancel={() => setUploadOpen(false)}
        onOk={handleUploadSubmit}
        confirmLoading={uploading}
        okText="开始上传"
        destroyOnClose
      >
        <Form form={uploadForm} layout="vertical">
          {activeTab === 'clothing' && (
            <>
              <Form.Item
                name="outfit_set"
                label="服装套装"
                rules={[{ required: true, message: '请填写套装名称，如：连衣裙' }]}
              >
                <Input placeholder="例如：连衣裙、白色上衣+黑色裙子" />
              </Form.Item>
              <Form.Item name="shoot_type" label="拍摄类型" rules={[{ required: true }]}>
                <Select options={SHOOT_TYPES.map((t) => ({ label: t, value: t }))} />
              </Form.Item>
            </>
          )}
          <Form.Item
            name="files"
            label="图片文件"
            valuePropName="fileList"
            getValueFromEvent={(e) => (Array.isArray(e) ? e : e?.fileList)}
            rules={[{ required: true, message: '请选择图片' }]}
          >
            <Upload.Dragger
              multiple
              accept="image/*"
              beforeUpload={() => false}
              listType="picture"
            >
              <p className="ant-upload-drag-icon"><UploadOutlined /></p>
              <p>点击或拖拽图片到此处，支持多选</p>
              <p className="ant-upload-hint">将保存到 content 目录并自动生成缩略图</p>
            </Upload.Dragger>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Materials;
