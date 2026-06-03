import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Empty, Image, Tag, Button, message } from 'antd';
import { getGallery } from '../services/api';

const Gallery: React.FC = () => {
  const [gallery, setGallery] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadGallery();
  }, []);

  const loadGallery = async () => {
    setLoading(true);
    try {
      const res = await getGallery();
      setGallery(res.data.gallery || []);
    } catch (e) {
      message.error('加载相册失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>我的相册</h2>
        <Button onClick={loadGallery}>刷新</Button>
      </div>
      {gallery.length === 0 ? (
        <Empty description="还没有生成Lookbook，去拍摄工作台创建一个吧！" />
      ) : (
        gallery.map((item: any) => (
          <Card key={item.task_id} title={`Lookbook - ${item.task_id.slice(0, 8)}`} style={{ marginBottom: 24 }} size="small">
            <Row gutter={[16, 16]}>
              {item.images?.map((img: any, idx: number) => (
                <Col span={6} key={idx}>
                  <Image
                    src={`/assets/generated/${item.task_id}/${img.path.split('/').pop()}`}
                    alt={img.angle}
                    style={{ height: 200, objectFit: 'cover', borderRadius: 8 }}
                  />
                  <div style={{ textAlign: 'center', marginTop: 4 }}>
                    <Tag>{img.angle}</Tag>
                  </div>
                </Col>
              ))}
            </Row>
          </Card>
        ))
      )}
    </div>
  );
};

export default Gallery;
