import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Empty, Image, Tag, Button, message, Drawer, Divider, Typography } from 'antd';
import { EyeOutlined, UserOutlined, SkinOutlined, PictureOutlined, EnvironmentOutlined } from '@ant-design/icons';
import { getGallery } from '../services/api';
import { toContentUrl } from '../utils/contentUrl';
import { toMediaUrl, mediaPreview } from '../utils/mediaUrl';

const { Text } = Typography;

const Gallery: React.FC = () => {
  const [gallery, setGallery] = useState<any[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeItem, setActiveItem] = useState<any>(null);

  useEffect(() => {
    loadGallery();
  }, []);

  const loadGallery = async () => {
    try {
      const res = await getGallery();
      setGallery(res.data.gallery || []);
    } catch (e) {
      message.error('加载相册失败');
    }
  };

  const openMaterials = (item: any) => {
    setActiveItem(item);
    setDrawerOpen(true);
  };

  const renderMaterialThumb = (m: any, height = 140) => (
    <Card size="small" key={m.id} style={{ marginBottom: 8 }}>
      <Image
        src={toMediaUrl(m)}
        alt={m.name}
        style={{ height, objectFit: 'cover', borderRadius: 6 }}
        preview={mediaPreview(m)}
      />
      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 6 }} ellipsis>
        {m.name}
      </Text>
    </Card>
  );

  const renderSourceMaterials = () => {
    const src = activeItem?.source_materials;
    if (!src) {
      return <Empty description="该任务未记录关联素材（可能是早期任务）" />;
    }
    const { model, clothing = [], reference, scene } = src;

    return (
      <div>
        <Text strong><UserOutlined /> 模特</Text>
        {model ? renderMaterialThumb(model, 200) : <Text type="secondary">未记录</Text>}

        <Divider />
        <Text strong><SkinOutlined /> 服装 ({clothing.length})</Text>
        {clothing.length === 0 ? (
          <Text type="secondary">未记录</Text>
        ) : (
          <Row gutter={[8, 8]}>
            {clothing.map((c: any) => (
              <Col span={8} key={c.id}>{renderMaterialThumb(c, 120)}</Col>
            ))}
          </Row>
        )}

        <Divider />
        <Text strong><PictureOutlined /> Lookbook 参考</Text>
        {reference ? renderMaterialThumb(reference, 160) : <Text type="secondary">未选择</Text>}

        <Divider />
        <Text strong><EnvironmentOutlined /> 场景/背景</Text>
        {scene ? renderMaterialThumb(scene, 160) : <Text type="secondary">未选择</Text>}
      </div>
    );
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>我的相册</h2>
        <Button onClick={loadGallery}>刷新</Button>
      </div>
      {gallery.length === 0 ? (
        <Empty description="还没有生成 Lookbook，去生图工作台创建一个吧！" />
      ) : (
        gallery.map((item: any) => (
          <Card
            key={item.task_id}
            title={`Lookbook · ${item.task_id.slice(0, 8)}`}
            style={{ marginBottom: 24 }}
            size="small"
            extra={(
              <Button type="link" icon={<EyeOutlined />} onClick={() => openMaterials(item)}>
                查看素材
              </Button>
            )}
          >
            <SpaceRowMeta item={item} />
            <Row gutter={[16, 16]} style={{ marginTop: 12 }}>
              {item.images?.map((img: any, idx: number) => (
                <Col span={6} key={img.id || idx}>
                  <Image
                    src={toContentUrl(img.path || '')}
                    alt={img.angle}
                    style={{ height: 200, objectFit: 'cover', borderRadius: 8 }}
                    loading="lazy"
                  />
                  <div style={{ textAlign: 'center', marginTop: 4 }}>
                    <Tag>{img.angle}</Tag>
                    {img.status && (
                      <Tag color={img.status === 'approved' ? 'success' : img.status === 'rejected' ? 'error' : 'default'}>
                        {img.status === 'approved' ? '合格' : img.status === 'rejected' ? '不合格' : '待验收'}
                      </Tag>
                    )}
                  </div>
                </Col>
              ))}
            </Row>
          </Card>
        ))
      )}

      <Drawer
        title={`关联素材 · ${activeItem?.task_id?.slice(0, 8) || ''}`}
        width={520}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        destroyOnClose
      >
        {renderSourceMaterials()}
      </Drawer>
    </div>
  );
};

const SpaceRowMeta: React.FC<{ item: any }> = ({ item }) => (
  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
    {item.size && <Tag>{item.size}</Tag>}
    {item.created_at && <Tag color="default">{new Date(item.created_at).toLocaleString()}</Tag>}
    {item.source_materials?.model && <Tag color="blue">含模特素材</Tag>}
    {item.source_materials?.clothing?.length > 0 && (
      <Tag color="purple">{item.source_materials.clothing.length} 件服装</Tag>
    )}
  </div>
);

export default Gallery;
