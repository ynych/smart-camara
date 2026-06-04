import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Upload, Button, message, Tabs, Image, Popconfirm, Empty, Tag, Space, Collapse, Spin } from 'antd';
import { UploadOutlined, DeleteOutlined, UserOutlined, SkinOutlined, ReloadOutlined, PictureOutlined } from '@ant-design/icons';
import { listMaterials, uploadMaterials, deleteMaterial, scanContentMaterials, getGroupedMaterials } from '../services/api';
import { toContentUrl } from '../utils/contentUrl';

const Materials: React.FC = () => {
  const [materials, setMaterials] = useState<any[]>([]);
  const [groupedData, setGroupedData] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('model_cards');
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    loadGroupedMaterials();
  }, []);

  useEffect(() => {
    loadMaterials();
  }, [activeTab]);

  const loadGroupedMaterials = async () => {
    setLoading(true);
    try {
      const res = await getGroupedMaterials();
      setGroupedData(res.data || {});
    } catch (e) {
      // ignore - grouped data may not be available yet
    } finally {
      setLoading(false);
    }
  };

  const loadMaterials = async () => {
    setLoading(true);
    try {
      const res = await listMaterials(activeTab === 'model_cards' ? 'model' : activeTab === 'clothing' ? 'clothing' : 'reference');
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
    formData.append('category', activeTab === 'model_cards' ? 'model' : activeTab === 'clothing' ? 'clothing' : 'reference');
    try {
      await uploadMaterials(formData);
      message.success('上传成功');
      loadMaterials();
      loadGroupedMaterials();
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
      loadGroupedMaterials();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const handleScanContent = async () => {
    setScanning(true);
    try {
      const res = await scanContentMaterials();
      message.success(`扫描完成，导入${res.data.count || 0}个素材`);
      loadGroupedMaterials();
      loadMaterials();
    } catch (e: any) {
      message.error('扫描失败: ' + (e.response?.data?.detail || e.message));
    } finally {
      setScanning(false);
    }
  };

  // 模特卡内容
  const renderModelCards = () => {
    const modelCards = groupedData?.model_cards || [];
    if (modelCards.length === 0) {
      return <Empty description="暂无模特卡素材，请先扫描素材目录" />;
    }
    return (
      <Row gutter={[16, 16]}>
        {modelCards.map((item: any, index: number) => (
          <Col span={6} key={index}>
            <Card
              size="small"
              hoverable
              cover={
                <Image
                  src={toContentUrl(item.file_path || item.path || '')}
                  alt={item.name || `模特卡${index + 1}`}
                  style={{ height: 240, objectFit: 'cover' }}
                  fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjI0MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjI0MCIgZmlsbD0iI2YwZjBmMCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjY2NjIiBmb250LXNpemU9IjE0Ij7ml6Dlm77niYc8L3RleHQ+PC9zdmc+"
                />
              }
            >
              <Card.Meta title={item.name || `模特卡${index + 1}`} />
            </Card>
          </Col>
        ))}
      </Row>
    );
  };

  // 服装素材内容
  const renderClothing = () => {
    const clothingSets = groupedData?.clothing_sets || [];
    if (clothingSets.length === 0) {
      return <Empty description="暂无服装素材，请先扫描素材目录" />;
    }
    const collapseItems = clothingSets.map((set: any, setIndex: number) => {
      const subTypes = ['人台图', '平铺图', '时尚拍摄'];
      const subTypeKeys = ['mannequin', 'flat_lay', 'fashion_shot'];
      return {
        key: `set-${setIndex}`,
        label: (
          <Space>
            <SkinOutlined />
            <span style={{ fontWeight: 500 }}>{set.name || `服装组${setIndex + 1}`}</span>
            <Tag color="blue">{set.items?.length || 0}件</Tag>
          </Space>
        ),
        children: (
          <Tabs
            type="card"
            size="small"
            items={subTypes.map((typeName, typeIdx) => ({
              key: subTypeKeys[typeIdx],
              label: typeName,
              children: (() => {
                const filteredItems = (set.items || []).filter(
                  (item: any) => item.sub_type === subTypeKeys[typeIdx] || (typeIdx === 0 && !item.sub_type)
                );
                if (filteredItems.length === 0) {
                  return <Empty description={`暂无${typeName}`} image={Empty.PRESENTED_IMAGE_SIMPLE} />;
                }
                return (
                  <Row gutter={[12, 12]}>
                    {filteredItems.map((item: any, itemIdx: number) => (
                      <Col span={6} key={itemIdx}>
                        <Card
                          size="small"
                          hoverable
                          cover={
                            <Image
                              src={toContentUrl(item.file_path || item.path || '')}
                              alt={item.name || `${typeName}${itemIdx + 1}`}
                              style={{ height: 180, objectFit: 'cover' }}
                              fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE4MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE4MCIgZmlsbD0iI2YwZjBmMCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjY2NjIiBmb250LXNpemU9IjE0Ij7ml6Dlm77niYc8L3RleHQ+PC9zdmc+"
                            />
                          }
                        >
                          <Card.Meta title={item.name || `${typeName}${itemIdx + 1}`} />
                        </Card>
                      </Col>
                    ))}
                  </Row>
                );
              })(),
            }))}
          />
        ),
      };
    });
    return <Collapse items={collapseItems} defaultActiveKey={[]} />;
  };

  // Lookbook参考内容
  const renderLookbookRefs = () => {
    const refs = groupedData?.lookbook_refs || [];
    if (refs.length === 0) {
      return <Empty description="暂无Lookbook参考图，请先扫描素材目录" />;
    }
    return (
      <Row gutter={[16, 16]}>
        {refs.map((item: any, index: number) => (
          <Col span={6} key={index}>
            <Card
              size="small"
              hoverable
              cover={
                <Image
                  src={toContentUrl(item.file_path || item.path || '')}
                  alt={item.name || `参考图${index + 1}`}
                  style={{ height: 240, objectFit: 'cover' }}
                  fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjI0MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjI0MCIgZmlsbD0iI2YwZjBmMCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjY2NjIiBmb250LXNpemU9IjE0Ij7ovpPlhaXlm77niYc8L3RleHQ+PC9zdmc+"
                />
              }
            >
              <Card.Meta title={item.name || `参考图${index + 1}`} />
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

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>素材管理</h2>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleScanContent}
            loading={scanning}
          >
            扫描素材目录
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />

        {activeTab === 'model_cards' && renderModelCards()}
        {activeTab === 'clothing' && renderClothing()}
        {activeTab === 'lookbook_refs' && renderLookbookRefs()}
      </Spin>

      {/* 上传素材区域 */}
      <div style={{ marginTop: 32 }}>
        <Card title="上传素材" size="small">
          <Row gutter={16} align="middle">
            <Col>
              <Upload beforeUpload={handleUpload} showUploadList={false}>
                <Button icon={<UploadOutlined />} type="primary">上传素材</Button>
              </Upload>
            </Col>
            <Col>
              <span style={{ color: '#999', fontSize: 13 }}>
                当前分类：{activeTab === 'model_cards' ? '模特卡' : activeTab === 'clothing' ? '服装素材' : 'Lookbook参考'}
              </span>
            </Col>
          </Row>
          {materials.length > 0 && (
            <div style={{ marginTop: 16 }}>
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
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default Materials;
