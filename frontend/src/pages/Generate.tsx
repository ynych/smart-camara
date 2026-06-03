import React, { useState, useEffect } from 'react';
import {
  Row, Col, Card, Select, Radio, Button, Input, Image,
  Space, message, Spin, Typography, Tag
} from 'antd';
import {
  ThunderboltOutlined, EyeOutlined, SendOutlined,
  CheckCircleOutlined, WomanOutlined, ManOutlined,
  HomeOutlined, CloudOutlined, PictureOutlined,
  UserOutlined, EnvironmentOutlined,
} from '@ant-design/icons';
import {
  getMaterials, getClothingNames, createGenerationTask, previewPrompt
} from '../services/api';
import { useNavigate } from 'react-router-dom';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

interface Material {
  id: string;
  name: string;
  category: string;
  sub_category: string;
  clothing_name?: string;
  file_path: string;
  thumbnail_path?: string;
}

const Generate: React.FC = () => {
  const navigate = useNavigate();

  // 服装相关
  const [clothingNames, setClothingNames] = useState<string[]>([]);
  const [selectedClothing, setSelectedClothing] = useState<string>('');
  const [clothingMaterials, setClothingMaterials] = useState<Material[]>([]);
  const [selectedClothingMaterials, setSelectedClothingMaterials] = useState<string[]>([]);

  // 模特相关
  const [modelMaterials, setModelMaterials] = useState<Material[]>([]);
  const [selectedModelMaterials, setSelectedModelMaterials] = useState<string[]>([]);

  // 场景相关
  const [sceneMaterials, setSceneMaterials] = useState<Material[]>([]);
  const [selectedSceneMaterials, setSelectedSceneMaterials] = useState<string[]>([]);

  // 参数
  const [gender, setGender] = useState<string>('female');
  const [sceneType, setSceneType] = useState<string>('indoor');
  const [aspectRatio, setAspectRatio] = useState<string>('3:4');
  const [quantity, setQuantity] = useState<number>(4);

  // 提示词
  const [prompt, setPrompt] = useState<string>('');
  const [previewResult, setPreviewResult] = useState<string>('');

  // 状态
  const [generating, setGenerating] = useState(false);
  const [previewing, setPreviewing] = useState(false);

  useEffect(() => {
    fetchClothingNames();
    fetchModelMaterials();
    fetchSceneMaterials();
  }, []);

  useEffect(() => {
    if (selectedClothing) {
      fetchClothingMaterials(selectedClothing);
    } else {
      setClothingMaterials([]);
      setSelectedClothingMaterials([]);
    }
  }, [selectedClothing]);

  const fetchClothingNames = async () => {
    try {
      const res = await getClothingNames();
      setClothingNames(res.data.clothing_names || res.data || []);
    } catch (err) {
      // ignore
    }
  };

  const fetchClothingMaterials = async (name: string) => {
    try {
      const res = await getMaterials({ clothing_name: name, category: 'clothing' });
      setClothingMaterials(res.data.materials || res.data.items || res.data || []);
      setSelectedClothingMaterials([]);
    } catch (err) {
      message.error('获取服装素材失败');
    }
  };

  const fetchModelMaterials = async () => {
    try {
      const res = await getMaterials({ category: 'model' });
      setModelMaterials(res.data.materials || res.data.items || res.data || []);
    } catch (err) {
      // ignore
    }
  };

  const fetchSceneMaterials = async () => {
    try {
      const res = await getMaterials({ category: 'scene' });
      setSceneMaterials(res.data.materials || res.data.items || res.data || []);
    } catch (err) {
      // ignore
    }
  };

  const toggleClothingMaterial = (id: string) => {
    setSelectedClothingMaterials((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );
  };

  const toggleModelMaterial = (id: string) => {
    setSelectedModelMaterials((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );
  };

  const toggleSceneMaterial = (id: string) => {
    setSelectedSceneMaterials((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );
  };

  const handlePreviewPrompt = async () => {
    setPreviewing(true);
    try {
      // 使用第一个选中的服装素材来预览提示词
      const clothingMaterialId = selectedClothingMaterials[0];
      if (!clothingMaterialId) {
        message.warning('请先选择服装素材');
        setPreviewing(false);
        return;
      }
      const data: any = {
        clothing_material_id: clothingMaterialId,
        model_gender: gender,
        scene_type: sceneType,
        size: aspectRatio,
        prompt: prompt || undefined,
        clothing_desc: selectedClothing,
      };
      const res = await previewPrompt(data);
      const resultPrompt = res.data.prompt || '';
      setPreviewResult(resultPrompt);
      if (!prompt) {
        setPrompt(resultPrompt);
      }
      message.success('提示词预览生成成功');
    } catch (err) {
      message.error('生成提示词预览失败');
    } finally {
      setPreviewing(false);
    }
  };

  const handleGenerate = async () => {
    if (selectedClothingMaterials.length === 0) {
      message.warning('请至少选择一个服装素材');
      return;
    }
    setGenerating(true);
    try {
      const data: any = {
        clothing_material_id: selectedClothingMaterials[0],
        model_material_id: selectedModelMaterials[0] || null,
        scene_material_id: selectedSceneMaterials[0] || null,
        size: aspectRatio,
        quantity: String(quantity),
        model_gender: gender,
        scene_type: sceneType,
        prompt: prompt || undefined,
      };
      await createGenerationTask(data);
      message.success('图片生成任务已提交！');
      navigate('/review');
    } catch (err: any) {
      const errMsg = err?.response?.data?.detail || '生成任务提交失败';
      message.error(errMsg);
    } finally {
      setGenerating(false);
    }
  };

  const genderLabel = gender === 'female' ? '女性' : '男性';
  const sceneTypeLabel = sceneType === 'indoor' ? '室内' : '室外';

  const summaryText = selectedClothing
    ? `使用 [${selectedClothing}] 素材，${genderLabel}模特，${sceneTypeLabel}场景，${aspectRatio}尺寸，生成${quantity}张图片`
    : '请先选择服装素材';

  const renderMaterialGrid = (
    materials: Material[],
    selectedIds: string[],
    onToggle: (id: string) => void
  ) => (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
      {materials.length === 0 ? (
        <Text type="secondary">暂无素材</Text>
      ) : (
        materials.map((m) => (
          <div
            key={m.id}
            style={{
              position: 'relative',
              border: selectedIds.includes(m.id) ? '2px solid #1890ff' : '2px solid #f0f0f0',
              borderRadius: 8,
              overflow: 'hidden',
              cursor: 'pointer',
              width: 80,
              height: 80,
            }}
            onClick={() => onToggle(m.id)}
          >
            <Image
              src={m.thumbnail_path || m.file_path}
              alt={m.name}
              width={76}
              height={76}
              style={{ objectFit: 'cover' }}
              preview={false}
              fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNzYiIGhlaWdodD0iNzYiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9Ijc2IiBoZWlnaHQ9Ijc2IiBmaWxsPSIjZjBmMGYwIi8+PC9zdmc+"
            />
            {selectedIds.includes(m.id) && (
              <div style={{
                position: 'absolute', top: 2, right: 2,
                background: '#1890ff', borderRadius: '50%',
                width: 18, height: 18, display: 'flex',
                alignItems: 'center', justifyContent: 'center',
              }}>
                <CheckCircleOutlined style={{ color: '#fff', fontSize: 12 }} />
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );

  return (
    <div>
      <Spin spinning={generating} tip="正在生成图片，请稍候...">
        <Row gutter={24}>
          {/* 左栏 - 参数配置区 */}
          <Col span={14}>
            <div className="generate-left">
              {/* 服装素材选择 */}
              <Card
                size="small"
                title={
                  <Space>
                    <PictureOutlined />
                    <span>服装素材选择</span>
                  </Space>
                }
                style={{ marginBottom: 16 }}
              >
                <div style={{ marginBottom: 12 }}>
                  <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>
                    选择服装名称：
                  </Text>
                  <Select
                    placeholder="请选择服装"
                    style={{ width: '100%' }}
                    value={selectedClothing || undefined}
                    onChange={(val) => setSelectedClothing(val)}
                    allowClear
                    options={clothingNames.map((n) => ({ label: n, value: n }))}
                  />
                </div>
                {selectedClothing && (
                  <div>
                    <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>
                      选择素材图片（点击选中）：
                    </Text>
                    {renderMaterialGrid(clothingMaterials, selectedClothingMaterials, toggleClothingMaterial)}
                  </div>
                )}
              </Card>

              {/* 模特图选择 */}
              <Card
                size="small"
                title={
                  <Space>
                    <UserOutlined />
                    <span>模特图选择（可选）</span>
                  </Space>
                }
                style={{ marginBottom: 16 }}
              >
                {renderMaterialGrid(modelMaterials, selectedModelMaterials, toggleModelMaterial)}
              </Card>

              {/* 场景图选择 */}
              <Card
                size="small"
                title={
                  <Space>
                    <EnvironmentOutlined />
                    <span>场景图选择（可选）</span>
                  </Space>
                }
                style={{ marginBottom: 16 }}
              >
                {renderMaterialGrid(sceneMaterials, selectedSceneMaterials, toggleSceneMaterial)}
              </Card>

              {/* 参数配置 */}
              <Card
                size="small"
                title={
                  <Space>
                    <ThunderboltOutlined />
                    <span>参数配置</span>
                  </Space>
                }
              >
                <div style={{ marginBottom: 16 }}>
                  <Text style={{ marginBottom: 8, display: 'block' }}>模特性别</Text>
                  <Radio.Group value={gender} onChange={(e) => setGender(e.target.value)}>
                    <Radio.Button value="female"><WomanOutlined /> 女性</Radio.Button>
                    <Radio.Button value="male"><ManOutlined /> 男性</Radio.Button>
                  </Radio.Group>
                </div>
                <div style={{ marginBottom: 16 }}>
                  <Text style={{ marginBottom: 8, display: 'block' }}>场景类型</Text>
                  <Radio.Group value={sceneType} onChange={(e) => setSceneType(e.target.value)}>
                    <Radio.Button value="indoor"><HomeOutlined /> 室内</Radio.Button>
                    <Radio.Button value="outdoor"><CloudOutlined /> 室外</Radio.Button>
                  </Radio.Group>
                </div>
                <div style={{ marginBottom: 16 }}>
                  <Text style={{ marginBottom: 8, display: 'block' }}>生成尺寸</Text>
                  <Radio.Group value={aspectRatio} onChange={(e) => setAspectRatio(e.target.value)}>
                    <Radio.Button value="1:1">1:1</Radio.Button>
                    <Radio.Button value="3:4">3:4</Radio.Button>
                    <Radio.Button value="9:16">9:16</Radio.Button>
                  </Radio.Group>
                </div>
                <div>
                  <Text style={{ marginBottom: 8, display: 'block' }}>生成数量</Text>
                  <Radio.Group value={quantity} onChange={(e) => setQuantity(e.target.value)}>
                    <Radio.Button value={1}>1张</Radio.Button>
                    <Radio.Button value={4}>4张</Radio.Button>
                    <Radio.Button value={6}>6张</Radio.Button>
                  </Radio.Group>
                </div>
              </Card>
            </div>
          </Col>

          {/* 右栏 - 提示词与操作区 */}
          <Col span={10}>
            <div className="generate-right">
              {/* 提示词编辑区 */}
              <Card
                size="small"
                title={
                  <Space>
                    <EyeOutlined />
                    <span>提示词编辑</span>
                  </Space>
                }
                style={{ marginBottom: 16 }}
              >
                <Button
                  type="dashed"
                  icon={<ThunderboltOutlined />}
                  onClick={handlePreviewPrompt}
                  loading={previewing}
                  block
                  style={{ marginBottom: 12 }}
                >
                  生成提示词
                </Button>
                <TextArea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="点击上方按钮自动生成提示词，或在此手动编辑..."
                  autoSize={{ minRows: 8, maxRows: 20 }}
                  style={{ marginBottom: 8 }}
                />
                {previewResult && (
                  <div style={{ background: '#f6f6f6', padding: 12, borderRadius: 6, maxHeight: 200, overflow: 'auto' }}>
                    <Text type="secondary" strong>预览结果：</Text>
                    <Paragraph style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>{previewResult}</Paragraph>
                  </div>
                )}
              </Card>

              {/* 验收标准展示区 */}
              <Card
                size="small"
                title={
                  <Space>
                    <CheckCircleOutlined />
                    <span>验收标准摘要</span>
                  </Space>
                }
                style={{ marginBottom: 16 }}
              >
                <div className="review-summary">
                  <Paragraph>{summaryText}</Paragraph>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <Tag color="blue">性别：{genderLabel}</Tag>
                    <Tag color="green">场景：{sceneTypeLabel}</Tag>
                    <Tag color="orange">尺寸：{aspectRatio}</Tag>
                    <Tag color="purple">数量：{quantity}张</Tag>
                  </div>
                </div>
              </Card>

              {/* 操作按钮 */}
              <Card size="small">
                <div className="action-buttons" style={{ flexDirection: 'column' }}>
                  <Button
                    icon={<EyeOutlined />}
                    onClick={handlePreviewPrompt}
                    loading={previewing}
                    block
                    size="large"
                  >
                    预览提示词
                  </Button>
                  <Button
                    type="primary"
                    icon={<SendOutlined />}
                    onClick={handleGenerate}
                    loading={generating}
                    block
                    size="large"
                    style={{ height: 56, fontSize: 18 }}
                  >
                    开始生图
                  </Button>
                </div>
              </Card>
            </div>
          </Col>
        </Row>
      </Spin>
    </div>
  );
};

export default Generate;
