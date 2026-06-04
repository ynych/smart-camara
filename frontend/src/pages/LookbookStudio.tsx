import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Collapse,
  Divider,
  Image,
  Input,
  InputNumber,
  Modal,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Steps,
  Tag,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  EditOutlined,
  EnvironmentOutlined,
  PictureOutlined,
  ReloadOutlined,
  RocketOutlined,
  SkinOutlined,
  UserOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import {
  checkClothingConflict,
  generateLookbook,
  generatePrompt,
  getGroupedMaterials,
  getTaskList,
  reviewGeneratedImage,
} from '../services/api';
import { toContentUrl } from '../utils/contentUrl';

const { TextArea } = Input;

interface PromptItem {
  index: number;
  angle_name: string;
  prompt: string;
}

interface ClothingItem {
  id: string;
  outfit_set: string;
  file_path: string;
  name?: string;
  sub_type?: string;
}

const sizeOptions = [
  { label: '1:1 主图', value: '1:1' },
  { label: '3:4 详情页', value: '3:4' },
  { label: '9:16 移动端', value: '9:16' },
];

const LookbookStudio: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [materials, setMaterials] = useState<any>({});
  const [materialsLoading, setMaterialsLoading] = useState(false);
  const [tasks, setTasks] = useState<any[]>([]);

  const [selectedModel, setSelectedModel] = useState<any>(null);
  const [selectedClothing, setSelectedClothing] = useState<ClothingItem[]>([]);
  const [selectedReference, setSelectedReference] = useState<any>(null);
  const [selectedScene, setSelectedScene] = useState<any>(null);
  const [conflictWarning, setConflictWarning] = useState('');

  const [size, setSize] = useState('3:4');
  const [quantity, setQuantity] = useState(4);
  const [merchantNeed, setMerchantNeed] = useState('电商Lookbook效果图，用于商品详情页和投放素材');
  const [targetAudience, setTargetAudience] = useState('关注质感、通勤和日常穿搭的女性用户');
  const [acceptanceCriteria, setAcceptanceCriteria] = useState('');
  const [prompts, setPrompts] = useState<PromptItem[]>([]);

  const [generatingPrompts, setGeneratingPrompts] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [taskStatus, setTaskStatus] = useState('');
  const [taskProgress, setTaskProgress] = useState(0);
  const [generatedImages, setGeneratedImages] = useState<any[]>([]);

  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectImageId, setRejectImageId] = useState('');
  const [rejectFeedback, setRejectFeedback] = useState('');

  const loadMaterials = useCallback(async () => {
    setMaterialsLoading(true);
    try {
      const res = await getGroupedMaterials();
      setMaterials(res.data || {});
    } catch {
      message.error('加载素材失败');
    } finally {
      setMaterialsLoading(false);
    }
  }, []);

  const loadTasks = useCallback(async () => {
    try {
      const res = await getTaskList();
      setTasks(res.data.tasks || []);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadMaterials();
    loadTasks();
  }, [loadMaterials, loadTasks]);

  useEffect(() => {
    if (selectedClothing.length < 2) {
      setConflictWarning('');
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res = await checkClothingConflict(selectedClothing);
        setConflictWarning((res.data?.conflicts || []).join('; '));
      } catch {
        setConflictWarning('');
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [selectedClothing]);

  const toggleClothing = (item: any, outfitSetName: string) => {
    const clothingItem: ClothingItem = {
      id: item.id,
      outfit_set: outfitSetName,
      file_path: item.file_path,
      name: item.name,
      sub_type: item.sub_type || item.sub_category,
    };
    setSelectedClothing((prev) =>
      prev.some((c) => c.id === clothingItem.id)
        ? prev.filter((c) => c.id !== clothingItem.id)
        : [...prev, clothingItem],
    );
  };

  const businessContext = {
    merchant_need: merchantNeed,
    target_audience: targetAudience,
  };

  const handleGeneratePrompts = async () => {
    if (!selectedModel || selectedClothing.length === 0) {
      message.warning('请先选择模特和服装素材');
      return;
    }
    setGeneratingPrompts(true);
    try {
      const res = await generatePrompt({
        model_id: selectedModel.id,
        clothing_ids: selectedClothing.map((c) => c.id),
        reference_id: selectedReference?.id || '',
        scene_id: selectedScene?.id || '',
        quantity,
        size,
        business_context: businessContext,
        acceptance_criteria: acceptanceCriteria,
      });
      const criteria = res.data?.acceptance_criteria || acceptanceCriteria;
      const promptList = res.data?.prompts || [];
      setAcceptanceCriteria(criteria);
      setPrompts(promptList.map((p: any, i: number) => ({
        index: i,
        angle_name: p.angle_name || `图片${i + 1}`,
        prompt: p.prompt || '',
      })));
      setCurrentStep(3);
      message.success('已生成验收标准和提示词');
    } catch (e: any) {
      message.error('生成提示词失败: ' + (e.response?.data?.detail || e.message));
    } finally {
      setGeneratingPrompts(false);
    }
  };

  const handleStartGeneration = async () => {
    if (!selectedModel || selectedClothing.length === 0 || prompts.length === 0) {
      message.warning('请先完成素材选择和提示词生成');
      return;
    }
    setGenerating(true);
    setTaskStatus('generating');
    setTaskProgress(8);
    setCurrentStep(4);
    try {
      const res = await generateLookbook({
        model_id: selectedModel.id,
        clothing_ids: selectedClothing.map((c) => c.id),
        reference_id: selectedReference?.id || '',
        scene_id: selectedScene?.id || '',
        size,
        quantity: prompts.length,
        prompts,
        acceptance_criteria: acceptanceCriteria,
        business_context: businessContext,
      });
      setGeneratedImages(res.data.images || []);
      setTaskStatus('completed');
      setTaskProgress(100);
      await loadTasks();
      message.success('Seedream 生图完成，等待验收');
    } catch (e: any) {
      setTaskStatus('failed');
      message.error('生图失败: ' + (e.response?.data?.detail || e.message));
    } finally {
      setGenerating(false);
    }
  };

  const handleReview = async (imageId: string, status: 'approved' | 'rejected', feedback = '') => {
    try {
      await reviewGeneratedImage(imageId, status, feedback);
      setGeneratedImages((prev) => prev.map((img) =>
        img.id === imageId ? { ...img, status, feedback } : img,
      ));
      message.success(status === 'approved' ? '已标记合格' : '已记录不合格反馈');
    } catch (e: any) {
      message.error('记录验收失败: ' + (e.response?.data?.detail || e.message));
    }
  };

  const confirmReject = async () => {
    if (!rejectFeedback.trim()) {
      message.warning('请填写不合格原因');
      return;
    }
    await handleReview(rejectImageId, 'rejected', rejectFeedback);
    setRejectModalOpen(false);
    setRejectImageId('');
    setRejectFeedback('');
  };

  const resetAll = () => {
    setCurrentStep(0);
    setSelectedModel(null);
    setSelectedClothing([]);
    setSelectedReference(null);
    setSelectedScene(null);
    setPrompts([]);
    setAcceptanceCriteria('');
    setGeneratedImages([]);
    setTaskStatus('');
    setTaskProgress(0);
  };

  const renderImageCard = (
    item: any,
    selected: boolean,
    onClick: () => void,
    height = 220,
  ) => (
    <Card
      size="small"
      hoverable
      onClick={onClick}
      style={{
        border: selected ? '2px solid #1677ff' : '1px solid #d9d9d9',
        borderRadius: 8,
        cursor: 'pointer',
      }}
      cover={
        <Image
          src={toContentUrl(item.file_path || item.path || '')}
          alt={item.name}
          style={{ height, objectFit: 'cover' }}
          preview={false}
        />
      }
    >
      <Card.Meta title={item.name || '未命名素材'} description={selected ? <Tag color="blue">已选择</Tag> : null} />
    </Card>
  );

  const renderStep0 = () => {
    const modelCards = materials.model_cards || [];
    return (
      <div>
        <h3>选择模特</h3>
        {modelCards.length === 0 ? (
          <Alert message="暂无模特卡素材，请先在素材管理中扫描或上传" type="info" showIcon />
        ) : (
          <Row gutter={[16, 16]}>
            {modelCards.map((item: any) => (
              <Col span={6} key={item.id}>
                {renderImageCard(item, selectedModel?.id === item.id, () => setSelectedModel(item), 240)}
              </Col>
            ))}
          </Row>
        )}
        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <Button type="primary" disabled={!selectedModel} onClick={() => setCurrentStep(1)}>下一步</Button>
        </div>
      </div>
    );
  };

  const renderStep1 = () => {
    const clothingSets = materials.clothing_sets || [];
    return (
      <div>
        <h3>选择服装</h3>
        {conflictWarning && (
          <Alert
            message="服装冲突提醒"
            description={conflictWarning}
            type="warning"
            icon={<WarningOutlined />}
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
        {clothingSets.length === 0 ? (
          <Alert message="暂无服装素材，请先在素材管理中扫描或上传" type="info" showIcon />
        ) : (
          <Collapse
            defaultActiveKey={clothingSets.map((_: any, index: number) => `set-${index}`)}
            items={clothingSets.map((set: any, setIndex: number) => ({
              key: `set-${setIndex}`,
              label: (
                <Space>
                  <SkinOutlined />
                  <span>{set.name}</span>
                  <Tag>{set.items?.length || 0}件</Tag>
                  <Tag color="blue">已选 {selectedClothing.filter((c) => c.outfit_set === set.name).length}</Tag>
                </Space>
              ),
              children: (
                <Row gutter={[12, 12]}>
                  {(set.items || []).map((item: any) => {
                    const selected = selectedClothing.some((c) => c.id === item.id);
                    return (
                      <Col span={6} key={item.id}>
                        {renderImageCard(item, selected, () => toggleClothing(item, set.name), 170)}
                      </Col>
                    );
                  })}
                </Row>
              ),
            }))}
          />
        )}
        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <Space>
            <Button onClick={() => setCurrentStep(0)}>上一步</Button>
            <Button type="primary" disabled={selectedClothing.length === 0} onClick={() => setCurrentStep(2)}>下一步</Button>
          </Space>
        </div>
      </div>
    );
  };

  const renderStep2 = () => {
    const refs = materials.lookbook_refs || [];
    const scenes = materials.scenes || [];
    const panelStyle: React.CSSProperties = {
      border: '1px solid #f0f0f0',
      borderRadius: 8,
      padding: 16,
      minHeight: 220,
    };
    return (
      <div>
        <h3>选择参考/场景并填写需求</h3>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={12}>
            <div style={panelStyle}>
              <h4 style={{ marginTop: 0 }}><Space><PictureOutlined />Lookbook参考图（可选）</Space></h4>
              {refs.length === 0 ? <Alert message="暂无参考图" type="info" /> : (
                <Row gutter={[12, 12]}>
                  {refs.map((item: any) => (
                    <Col span={8} key={item.id}>
                      {renderImageCard(item, selectedReference?.id === item.id, () => setSelectedReference(selectedReference?.id === item.id ? null : item), 150)}
                    </Col>
                  ))}
                </Row>
              )}
            </div>
          </Col>
          <Col span={12}>
            <div style={panelStyle}>
              <h4 style={{ marginTop: 0 }}><Space><EnvironmentOutlined />场景/背景图（可选）</Space></h4>
              {scenes.length === 0 ? <Alert message="暂无场景图，可直接使用参考图风格" type="info" /> : (
                <Row gutter={[12, 12]}>
                  {scenes.map((item: any) => (
                    <Col span={8} key={item.id}>
                      {renderImageCard(item, selectedScene?.id === item.id, () => setSelectedScene(selectedScene?.id === item.id ? null : item), 150)}
                    </Col>
                  ))}
                </Row>
              )}
            </div>
          </Col>
        </Row>

        <div style={panelStyle}>
          <h4 style={{ marginTop: 0 }}>商家需求与目标用户画像</h4>
          <Row gutter={16}>
            <Col span={12}>
              <TextArea rows={3} value={merchantNeed} onChange={(e) => setMerchantNeed(e.target.value)} placeholder="商家需求" />
            </Col>
            <Col span={12}>
              <TextArea rows={3} value={targetAudience} onChange={(e) => setTargetAudience(e.target.value)} placeholder="目标用户画像" />
            </Col>
          </Row>
          <Divider />
          <Space>
            <span>尺寸</span>
            <Select style={{ width: 160 }} value={size} onChange={setSize} options={sizeOptions} />
            <span>数量</span>
            <InputNumber min={1} max={8} value={quantity} onChange={(value) => setQuantity(value || 1)} />
            <Button icon={<ReloadOutlined />} type="primary" loading={generatingPrompts} onClick={handleGeneratePrompts}>
              生成验收标准和提示词
            </Button>
          </Space>
        </div>

        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <Button onClick={() => setCurrentStep(1)}>上一步</Button>
        </div>
      </div>
    );
  };

  const renderStep3 = () => (
    <div>
      <h3>确认验收标准与提示词</h3>
      <Card size="small" title="验收标准" style={{ marginBottom: 16 }}>
        <TextArea rows={7} value={acceptanceCriteria} onChange={(e) => setAcceptanceCriteria(e.target.value)} />
      </Card>
      <Row gutter={[16, 16]}>
        {prompts.map((item) => (
          <Col span={12} key={item.index}>
            <Card size="small" title={<Space><EditOutlined />{item.angle_name}</Space>}>
              <TextArea
                rows={7}
                value={item.prompt}
                onChange={(e) => setPrompts((prev) => prev.map((p) => p.index === item.index ? { ...p, prompt: e.target.value } : p))}
              />
            </Card>
          </Col>
        ))}
      </Row>
      <div style={{ marginTop: 24, textAlign: 'center' }}>
        <Space>
          <Button onClick={() => setCurrentStep(2)}>上一步</Button>
          <Button icon={<RocketOutlined />} type="primary" loading={generating} onClick={handleStartGeneration}>点击生图</Button>
        </Space>
      </div>
    </div>
  );

  const renderStep4 = () => (
    <div>
      <h3>生成结果与验收</h3>
      {taskStatus === 'generating' && (
        <div style={{ textAlign: 'center', padding: '36px 0' }}>
          <Spin size="large" />
          <Progress percent={taskProgress} status="active" style={{ maxWidth: 420, margin: '20px auto' }} />
        </div>
      )}
      {taskStatus === 'failed' && <Alert message="生成失败，请检查火山 Seedream 配置或重试" type="error" showIcon style={{ marginBottom: 16 }} />}
      {generatedImages.length > 0 && (
        <>
          <Alert
            message="验收标准"
            description={<pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{acceptanceCriteria}</pre>}
            type="info"
            style={{ marginBottom: 16 }}
          />
          <Row gutter={[16, 16]}>
            {generatedImages.map((img, index) => (
              <Col span={6} key={img.id || index}>
                <Card
                  size="small"
                  cover={<Image src={toContentUrl(img.path || '')} alt={img.angle} style={{ height: 240, objectFit: 'cover' }} />}
                  actions={[
                    <Button key="ok" type="link" icon={<CheckCircleOutlined />} onClick={() => handleReview(img.id, 'approved')} disabled={img.status === 'approved'}>
                      合格
                    </Button>,
                    <Button key="bad" type="link" danger icon={<CloseCircleOutlined />} onClick={() => { setRejectImageId(img.id); setRejectModalOpen(true); }}>
                      不合格
                    </Button>,
                  ]}
                >
                  <Card.Meta
                    title={img.angle || `图片${index + 1}`}
                    description={
                      <Space direction="vertical" size={4}>
                        <Tag color={img.status === 'approved' ? 'success' : img.status === 'rejected' ? 'error' : 'warning'}>
                          {img.status === 'approved' ? '合格' : img.status === 'rejected' ? '不合格' : '待验收'}
                        </Tag>
                        {img.feedback && <span style={{ color: '#999' }}>{img.feedback}</span>}
                      </Space>
                    }
                  />
                </Card>
              </Col>
            ))}
          </Row>
          <div style={{ marginTop: 24, textAlign: 'center' }}>
            <Button type="primary" onClick={resetAll}>生成新的Lookbook</Button>
          </div>
        </>
      )}
    </div>
  );

  const steps = [
    { title: '选择模特', icon: <UserOutlined /> },
    { title: '选择服装', icon: <SkinOutlined /> },
    { title: '需求与参考', icon: <PictureOutlined /> },
    { title: '提示词确认', icon: <EditOutlined /> },
    { title: '结果验收', icon: <RocketOutlined /> },
  ];

  return (
    <div>
      <Steps current={currentStep} items={steps} style={{ marginBottom: 32 }} />
      <Spin spinning={materialsLoading && currentStep < 4} tip="加载素材中...">
        {currentStep === 0 && renderStep0()}
        {currentStep === 1 && renderStep1()}
        {currentStep === 2 && renderStep2()}
        {currentStep === 3 && renderStep3()}
        {currentStep === 4 && renderStep4()}
      </Spin>

      {tasks.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <Divider />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>最近任务</h3>
            <Button size="small" onClick={loadTasks}>刷新</Button>
          </div>
          <Space direction="vertical" style={{ width: '100%' }}>
            {tasks.slice(0, 6).map((task) => (
              <Card size="small" key={task.id}>
                <Space>
                  <span>任务 {task.id?.slice(0, 8)}</span>
                  <Tag color={task.status === 'completed' ? 'success' : task.status === 'failed' ? 'error' : 'processing'}>{task.status}</Tag>
                  <span>{task.size}</span>
                  <span>{task.quantity || task.generated_images?.length || 0}张</span>
                </Space>
              </Card>
            ))}
          </Space>
        </div>
      )}

      <Modal
        title="不合格反馈"
        open={rejectModalOpen}
        onOk={confirmReject}
        onCancel={() => setRejectModalOpen(false)}
        okText="提交反馈"
        cancelText="取消"
      >
        <TextArea
          rows={4}
          value={rejectFeedback}
          onChange={(e) => setRejectFeedback(e.target.value)}
          placeholder="例如：服装颜色偏差、模特手部异常、背景不符合参考图、构图裁切等"
        />
      </Modal>
    </div>
  );
};

export default LookbookStudio;
