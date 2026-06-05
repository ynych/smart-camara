import React, { useCallback, useEffect, useState } from 'react';
import {
  Card,
  Collapse,
  Row,
  Col,
  Empty,
  Image,
  Tag,
  Button,
  message,
  Drawer,
  Divider,
  Typography,
  Select,
  Input,
  Space,
  Alert,
} from 'antd';
import {
  EyeOutlined,
  UserOutlined,
  SkinOutlined,
  PictureOutlined,
  EnvironmentOutlined,
  SearchOutlined,
  ClearOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { getGallery, type GalleryFilters } from '../services/api';
import { toContentUrl } from '../utils/contentUrl';
import { toMediaUrl, mediaPreview } from '../utils/mediaUrl';

const { Text, Paragraph } = Typography;

type FilterOption = { id: string; name: string };

const statusTag: Record<string, { color: string; label: string }> = {
  completed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
  generating: { color: 'processing', label: '生成中' },
  pending: { color: 'default', label: '待处理' },
};

const Gallery: React.FC = () => {
  const [gallery, setGallery] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [filterOptions, setFilterOptions] = useState<{
    models: FilterOption[];
    clothing: FilterOption[];
    references: FilterOption[];
  }>({ models: [], clothing: [], references: [] });
  const [filters, setFilters] = useState<GalleryFilters>({});
  const [taskIdInput, setTaskIdInput] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeItem, setActiveItem] = useState<any>(null);
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);

  const loadGallery = useCallback(async (applied?: GalleryFilters) => {
    setLoading(true);
    try {
      const res = await getGallery(applied);
      const items = res.data.gallery || [];
      setGallery(items);
      setTotal(res.data.total ?? items.length ?? 0);
      const opts = res.data.filter_options;
      if (opts) {
        setFilterOptions({
          models: opts.models || [],
          clothing: opts.clothing || [],
          references: opts.references || [],
        });
      }
    } catch {
      message.error('加载历史任务失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGallery();
  }, []);

  useEffect(() => {
    if (gallery.length > 0 && expandedKeys.length === 0) {
      setExpandedKeys([gallery[0].task_id]);
    }
  }, [gallery, expandedKeys.length]);

  const applyFilters = () => {
    const next: GalleryFilters = {
      ...filters,
      task_id: taskIdInput.trim() || undefined,
    };
    if (!next.task_id) delete next.task_id;
    setFilters(next);
    setExpandedKeys([]);
    loadGallery(next);
  };

  const clearFilters = () => {
    setFilters({});
    setTaskIdInput('');
    setExpandedKeys([]);
    loadGallery({});
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

  const renderPromptsSection = () => {
    const images = activeItem?.images || [];
    const hasPrompt = images.some((img: any) => img.prompt);
    if (!hasPrompt && !(activeItem?.prompts?.length)) {
      return <Text type="secondary">该任务未保存提示词记录</Text>;
    }
    const list = hasPrompt
      ? images
      : (activeItem?.prompts || []).map((p: any, idx: number) => ({
          angle: p.angle_name || `图片${idx + 1}`,
          prompt: p.prompt,
          status: undefined,
        }));

    return (
      <div>
        {list.map((img: any, idx: number) => (
          <div key={img.id || idx} style={{ marginBottom: 16 }}>
            <Text strong>
              <FileTextOutlined /> {img.angle || `图片 ${idx + 1}`}
              {img.status && (
                <Tag
                  style={{ marginLeft: 8 }}
                  color={img.status === 'approved' ? 'success' : img.status === 'rejected' ? 'error' : 'default'}
                >
                  {img.status === 'approved' ? '合格' : img.status === 'rejected' ? '不合格' : '待验收'}
                </Tag>
              )}
            </Text>
            <Paragraph
              style={{
                marginTop: 8,
                marginBottom: 0,
                whiteSpace: 'pre-wrap',
                fontSize: 13,
                background: '#fafafa',
                padding: 12,
                borderRadius: 8,
                border: '1px solid #f0f0f0',
              }}
            >
              {img.prompt || '（无）'}
            </Paragraph>
          </div>
        ))}
      </div>
    );
  };

  const renderSeedreamPlan = () => {
    const slots = activeItem?.seedream_image_slots;
    if (!slots?.length) return null;
    return (
      <>
        <Divider />
        <Text strong>生图参考图顺序（Seedream 多图融合）</Text>
        <ul style={{ paddingLeft: 20, marginTop: 8, fontSize: 13 }}>
          {slots.map((s: any) => (
            <li key={s.index} style={{ marginBottom: 4 }}>
              图{s.index}：{s.role}
              {!s.resolved && <Tag color="error" style={{ marginLeft: 6 }}>文件未读取</Tag>}
              {s.name && <Text type="secondary"> — {s.name}</Text>}
            </li>
          ))}
        </ul>
      </>
    );
  };

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

  const renderTaskPanel = (item: any) => (
    <>
      {item.status === 'failed' && item.error_message && (
        <Alert type="error" message={item.error_message} style={{ marginBottom: 12 }} showIcon />
      )}
      {item.images?.length > 0 ? (
        <Row gutter={[16, 16]}>
          {item.images.map((img: any, idx: number) => (
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
      ) : (
        <Text type="secondary">{item.status === 'generating' ? '生成中…' : '暂无生成图'}</Text>
      )}
    </>
  );

  const collapseItems = gallery.map((item: any) => {
    const st = statusTag[item.status] || { color: 'default', label: item.status || '未知' };
    return {
      key: item.task_id,
      label: (
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, width: '100%' }}>
          <Text strong>任务 {item.task_id.slice(0, 8)}…</Text>
          <Tag color={st.color}>{st.label}</Tag>
          {item.size && <Tag>{item.size}</Tag>}
          {item.images?.length > 0 && <Tag>{item.images.length} 张</Tag>}
          {item.created_at && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {new Date(item.created_at).toLocaleString()}
            </Text>
          )}
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              openMaterials(item);
            }}
          >
            查看素材与提示词
          </Button>
        </div>
      ),
      children: renderTaskPanel(item),
    };
  });

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>历史任务</h2>
        <Button onClick={() => loadGallery(filters)} loading={loading}>刷新</Button>
      </div>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap style={{ width: '100%' }} align="start">
          <Input
            placeholder="任务 ID（支持部分匹配）"
            value={taskIdInput}
            onChange={(e) => setTaskIdInput(e.target.value)}
            onPressEnter={applyFilters}
            style={{ width: 220 }}
            allowClear
          />
          <Select
            placeholder="模特图"
            allowClear
            style={{ minWidth: 160 }}
            value={filters.model_id}
            onChange={(v) => setFilters((f) => ({ ...f, model_id: v }))}
            options={filterOptions.models.map((m) => ({ value: m.id, label: m.name }))}
          />
          <Select
            placeholder="服装图"
            allowClear
            style={{ minWidth: 160 }}
            value={filters.clothing_id}
            onChange={(v) => setFilters((f) => ({ ...f, clothing_id: v }))}
            options={filterOptions.clothing.map((c) => ({ value: c.id, label: c.name }))}
          />
          <Select
            placeholder="参考图"
            allowClear
            style={{ minWidth: 160 }}
            value={filters.reference_id}
            onChange={(v) => setFilters((f) => ({ ...f, reference_id: v }))}
            options={filterOptions.references.map((r) => ({ value: r.id, label: r.name }))}
          />
          <Button type="primary" icon={<SearchOutlined />} onClick={applyFilters}>
            筛选
          </Button>
          <Button icon={<ClearOutlined />} onClick={clearFilters}>
            清空
          </Button>
        </Space>
        {total > 0 && (
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            共 {total} 条历史任务
          </Text>
        )}
      </Card>

      {gallery.length === 0 ? (
        <Empty description="暂无历史任务，去生图工作台创建吧" />
      ) : (
        <Collapse
          accordion
          items={collapseItems}
          activeKey={expandedKeys[0]}
          onChange={(key) => setExpandedKeys(key ? [String(key)] : [])}
        />
      )}

      <Drawer
        title={`素材与提示词 · ${activeItem?.task_id?.slice(0, 8) || ''}`}
        width={560}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        destroyOnClose
      >
        <Text strong><FileTextOutlined /> 生图提示词</Text>
        <div style={{ marginTop: 8, marginBottom: 8 }}>{renderPromptsSection()}</div>
        {renderSeedreamPlan()}
        <Divider />
        <Text strong>关联素材</Text>
        <div style={{ marginTop: 8 }}>{renderSourceMaterials()}</div>
      </Drawer>
    </div>
  );
};

export default Gallery;
