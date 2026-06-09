import React, { useCallback, useEffect, useRef, useState } from 'react';
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
  Tabs,
  Tag,
  message,
} from 'antd';
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EditOutlined,
  EnvironmentOutlined,
  EyeOutlined,
  PictureOutlined,
  ReloadOutlined,
  RocketOutlined,
  SkinOutlined,
  UserOutlined,
  WarningOutlined,
  FormOutlined,
} from '@ant-design/icons';
import {
  checkClothingConflict,
  createStudioTask,
  generateLookbook,
  generatePrompt,
  getGroupedMaterials,
  getStudioTask,
  getTask,
  listStudioTasks,
  patchStudioTask,
  reviewGeneratedImage,
} from '../services/api';
import { toContentUrl } from '../utils/contentUrl';
import { toMediaUrl } from '../utils/mediaUrl';
import { apiErrorMessage } from '../utils/apiError';
import ImageEvaluationModal from '../components/ImageEvaluationModal';
import StudioTaskList, { type StudioTaskItem } from '../components/StudioTaskList';

const STEP_SECTIONS: Record<number, string> = {
  0: 'model',
  1: 'clothing',
  2: 'refs,scenes',
};

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

const STATUS_LABEL: Record<string, string> = {
  draft: '编辑中',
  prompts_ready: '待生图',
  generating: '生图中',
  completed: '已完成',
  failed: '失败',
};

const LookbookStudio: React.FC = () => {
  const [viewMode, setViewMode] = useState<'list' | 'edit'>('list');
  const [studioTasks, setStudioTasks] = useState<StudioTaskItem[]>([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [studioTaskId, setStudioTaskId] = useState<string | null>(null);
  const [studioTaskStatus, setStudioTaskStatus] = useState<string>('draft');

  const [currentStep, setCurrentStep] = useState(0);
  const [materials, setMaterials] = useState<any>({});
  const [materialsLoading, setMaterialsLoading] = useState(false);
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
  const [promptRunId, setPromptRunId] = useState<string | null>(null);

  const [generatingPrompts, setGeneratingPrompts] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [taskStatus, setTaskStatus] = useState('');
  const [generationError, setGenerationError] = useState('');
  const [taskProgress, setTaskProgress] = useState(0);
  const [generatedImages, setGeneratedImages] = useState<any[]>([]);

  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectImageId, setRejectImageId] = useState('');
  const [rejectFeedback, setRejectFeedback] = useState('');
  const [evalModal, setEvalModal] = useState<{ open: boolean; imageId: string; path?: string; angle?: string }>({
    open: false,
    imageId: '',
  });
  const [previewItem, setPreviewItem] = useState<any>(null);
  const loadedSectionsRef = useRef<Set<string>>(new Set());
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isEditable = studioTaskStatus !== 'completed' && studioTaskStatus !== 'generating';
  const canGenerate = isEditable && prompts.length > 0 && prompts.some((p) => p.prompt?.trim());

  const loadTasks = useCallback(async () => {
    setTasksLoading(true);
    try {
      const tasks = await listStudioTasks();
      setStudioTasks(tasks);
    } catch (e: any) {
      const detail = e.response?.data?.detail;
      message.error('加载任务列表失败: ' + (typeof detail === 'string' ? detail : e.message));
    } finally {
      setTasksLoading(false);
    }
  }, []);

  useEffect(() => {
    if (viewMode === 'list') {
      loadTasks();
    }
  }, [viewMode, loadTasks]);

  const restoreSelections = useCallback((task: Record<string, unknown>, mats: Record<string, unknown>) => {
    const modelCards = (mats.model_cards as any[]) || [];
    const model = modelCards.find((m) => m.id === task.model_id);
    setSelectedModel(model || null);

    const clothingIds = (task.clothing_ids as string[]) || [];
    const clothing: ClothingItem[] = [];
    for (const set of (mats.clothing_sets as any[]) || []) {
      for (const item of set.items || []) {
        if (clothingIds.includes(item.id)) {
          clothing.push({
            id: item.id,
            outfit_set: set.name,
            file_path: item.file_path,
            name: item.name,
            sub_type: item.shoot_type || item.sub_type || item.sub_category,
          });
        }
      }
    }
    setSelectedClothing(clothing);

    const refs = (mats.lookbook_refs as any[]) || [];
    setSelectedReference(refs.find((r) => r.id === task.reference_id) || null);
    const scenes = (mats.scenes as any[]) || [];
    setSelectedScene(scenes.find((s) => s.id === task.scene_id) || null);
  }, []);

  const inferStep = (task: Record<string, unknown>): number => {
    const status = task.status as string;
    const taskPrompts = (task.prompts as unknown[]) || [];
    if (status === 'completed' || status === 'generating') return 4;
    if (status === 'prompts_ready' || taskPrompts.length > 0) return 3;
    if (task.model_id && ((task.clothing_ids as string[]) || []).length > 0) return 2;
    if (task.model_id) return 1;
    return 0;
  };

  const resetEditor = () => {
    setCurrentStep(0);
    setSelectedModel(null);
    setSelectedClothing([]);
    setSelectedReference(null);
    setSelectedScene(null);
    setPromptRunId(null);
    setPrompts([]);
    setAcceptanceCriteria('');
    setGeneratedImages([]);
    setTaskStatus('');
    setGenerationError('');
    setTaskProgress(0);
    setMerchantNeed('电商Lookbook效果图，用于商品详情页和投放素材');
    setTargetAudience('关注质感、通勤和日常穿搭的女性用户');
    setSize('3:4');
    setQuantity(4);
    loadedSectionsRef.current.clear();
  };

  const buildPatchPayload = useCallback((overrides: Record<string, unknown> = {}) => ({
    model_id: selectedModel?.id,
    model_name: selectedModel?.name,
    clothing_ids: selectedClothing.map((c) => c.id),
    reference_id: selectedReference?.id || null,
    scene_id: selectedScene?.id || null,
    size,
    quantity,
    business_context: { merchant_need: merchantNeed, target_audience: targetAudience },
    acceptance_criteria: acceptanceCriteria,
    prompts,
    prompt_run_id: promptRunId,
    ...overrides,
  }), [
    selectedModel, selectedClothing, selectedReference, selectedScene,
    size, quantity, merchantNeed, targetAudience, acceptanceCriteria, prompts, promptRunId,
  ]);

  const persistStudioTask = useCallback(async (overrides: Record<string, unknown> = {}) => {
    if (!studioTaskId || !isEditable) return;
    try {
      const updated = await patchStudioTask(studioTaskId, buildPatchPayload(overrides));
      if (updated.status) setStudioTaskStatus(updated.status);
    } catch (e: any) {
      const detail = e.response?.data?.detail || e.message;
      if (!String(detail).includes('不可编辑')) {
        message.error('保存任务失败: ' + detail);
      }
    }
  }, [studioTaskId, isEditable, buildPatchPayload]);

  const scheduleSave = useCallback(() => {
    if (!studioTaskId || !isEditable) return;
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => { persistStudioTask(); }, 800);
  }, [studioTaskId, isEditable, persistStudioTask]);

  const openTask = async (item: StudioTaskItem) => {
    setTasksLoading(true);
    try {
      const task = await getStudioTask(item.id);
      resetEditor();
      setStudioTaskId(task.id);
      setStudioTaskStatus(task.status || 'draft');
      setSize(task.size || '3:4');
      setQuantity(task.quantity || 4);
      const bc = task.business_context || {};
      setMerchantNeed(bc.merchant_need || merchantNeed);
      setTargetAudience(bc.target_audience || targetAudience);
      setAcceptanceCriteria(task.acceptance_criteria || '');
      setPromptRunId(task.prompt_run_id || null);
      setPrompts((task.prompts || []).map((p: any, i: number) => ({
        index: i,
        angle_name: p.angle_name || `图片${i + 1}`,
        prompt: p.prompt || '',
      })));

      await getGroupedMaterials({ sections: 'model,clothing,refs,scenes' }).then((res) => {
        const mats = res.data || {};
        setMaterials(mats);
        restoreSelections(task, mats);
      });

      const step = inferStep(task);
      setCurrentStep(step);

      if (task.status === 'completed' && task.lookbook_task_id) {
        setTaskStatus('completed');
        setTaskProgress(100);
        try {
          const tr = await getTask(task.lookbook_task_id);
          setGeneratedImages(tr.data?.generated_images || []);
        } catch {
          message.warning('加载生成结果失败');
        }
      } else if (task.status === 'failed') {
        setTaskStatus('failed');
        setGenerationError((task.error_message as string) || '');
      } else if (task.status === 'generating') {
        setTaskStatus('generating');
      }

      setViewMode('edit');
    } catch (e: any) {
      message.error('打开任务失败: ' + (e.response?.data?.detail || e.message));
    } finally {
      setTasksLoading(false);
    }
  };

  const handleNewTask = async () => {
    try {
      const task = await createStudioTask({});
      resetEditor();
      setStudioTaskId(task.id);
      setStudioTaskStatus('draft');
      setViewMode('edit');
      await fetchSection(0, true);
    } catch (e: any) {
      message.error('创建任务失败: ' + (e.response?.data?.detail || e.message));
    }
  };

  const backToList = async () => {
    if (studioTaskId && isEditable) {
      await persistStudioTask();
    }
    setStudioTaskId(null);
    setStudioTaskStatus('draft');
    resetEditor();
    setViewMode('list');
  };

  const fetchSection = useCallback(async (step: number, force = false) => {
    const sections = STEP_SECTIONS[step];
    if (!sections) return;
    if (!force && loadedSectionsRef.current.has(sections)) return;

    setMaterialsLoading(true);
    try {
      const res = await getGroupedMaterials({ sections });
      setMaterials((prev: Record<string, unknown>) => ({ ...prev, ...res.data }));
      loadedSectionsRef.current.add(sections);
    } catch (e) {
      message.error(apiErrorMessage(e, '加载素材失败'));
    } finally {
      setMaterialsLoading(false);
    }
  }, []);

  const goToStep = async (step: number) => {
    if (step >= 0 && step <= 2) {
      await fetchSection(step, true);
    }
    setCurrentStep(step);
  };

  useEffect(() => {
    if (currentStep <= 2) {
      fetchSection(currentStep);
    }
  }, [currentStep, fetchSection]);

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
      sub_type: item.shoot_type || item.sub_type || item.sub_category,
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
    if (!studioTaskId) {
      message.warning('请先新建或打开任务');
      return;
    }
    setGeneratingPrompts(true);
    try {
      const res = await generatePrompt({
        studio_task_id: studioTaskId,
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
      setPromptRunId(res.data?.prompt_run_id || null);
      const mapped = promptList.map((p: any, i: number) => ({
        index: i,
        angle_name: p.angle_name || `图片${i + 1}`,
        prompt: p.prompt || '',
      }));
      setPrompts(mapped);
      setStudioTaskStatus('prompts_ready');
      setCurrentStep(3);
      const src = res.data?.prompt_source;
      const slug = res.data?.agent_slug || 'lookbook_prompt_agent_v1';
      if (src === 'llm') {
        message.success(`Agent「${slug}」已生成提示词（LLM）`);
      } else if (src === 'harness') {
        const detail = res.data?.llm_error || 'LLM 未可用';
        const hint = detail.includes('未配置') || detail.includes('VOLCANO_CHAT')
          ? ' → 请到「设置」页配置 ep- 豆包对话接入点'
          : '';
        message.warning(`Agent「${slug}」已运行；${detail}${hint}；已用 Harness 组装`, 10);
      } else {
        message.info(`Agent「${slug}」来源：${src || 'unknown'}`);
      }
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
    if (!studioTaskId) {
      message.warning('请先新建或打开任务');
      return;
    }
    setGenerating(true);
    setStudioTaskStatus('generating');
    setTaskStatus('generating');
    setGenerationError('');
    setTaskProgress(8);
    setCurrentStep(4);
    try {
      await persistStudioTask({ status: 'generating', prompts });
      const res = await generateLookbook({
        studio_task_id: studioTaskId,
        prompt_run_id: promptRunId || undefined,
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
      setStudioTaskStatus('completed');
      setTaskStatus('completed');
      setGenerationError('');
      setTaskProgress(100);
      message.success('Seedream 生图完成');
    } catch (e: any) {
      const detail = e.response?.data?.detail || e.message;
      setStudioTaskStatus('failed');
      setTaskStatus('failed');
      setGenerationError(typeof detail === 'string' ? detail : JSON.stringify(detail));
      message.error('生图失败: ' + (typeof detail === 'string' ? detail : e.message));
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
    backToList();
  };

  const updatePrompt = (index: number, text: string) => {
    setPrompts((prev) => prev.map((p) => (p.index === index ? { ...p, prompt: text } : p)));
    scheduleSave();
  };

  const renderImageCard = (
    item: any,
    selected: boolean,
    onSelect: () => void,
    height = 220,
  ) => (
    <Card
      size="small"
      hoverable
      onClick={onSelect}
      style={{
        border: selected ? '2px solid #1677ff' : '1px solid #d9d9d9',
        borderRadius: 8,
        cursor: 'pointer',
      }}
      cover={
        <div style={{ position: 'relative', height, overflow: 'hidden' }}>
          <img
            src={toMediaUrl(item)}
            alt={item.name}
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block', pointerEvents: 'none' }}
            loading="lazy"
          />
        </div>
      }
      actions={[
        <Button
          key="preview"
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={(e) => {
            e.stopPropagation();
            setPreviewItem(item);
          }}
        >
          查看大图
        </Button>,
      ]}
    >
      <Card.Meta
        title={item.name || '未命名素材'}
        description={selected ? <Tag color="blue">已选择</Tag> : <Tag>点击卡片选中</Tag>}
      />
    </Card>
  );

  const renderStep0 = () => {
    const modelCards = materials.model_cards || [];
    return (
      <div>
        <h3>选择模特</h3>
        {modelCards.length === 0 ? (
          <Alert message="暂无模特卡素材，请先在素材管理中上传" type="info" showIcon />
        ) : (
          <Row gutter={[16, 16]}>
            {modelCards.map((item: any, index: number) => (
              <Col span={6} key={item.id || `model-${index}`}>
                {renderImageCard(
                  item,
                  selectedModel?.id === item.id,
                  () => setSelectedModel(selectedModel?.id === item.id ? null : item),
                  240,
                )}
              </Col>
            ))}
          </Row>
        )}
        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <Button type="primary" disabled={!selectedModel} onClick={() => goToStep(1)}>下一步</Button>
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
          <Alert message="暂无服装素材，请先在素材管理中上传" type="info" showIcon />
        ) : (
          <Collapse
            defaultActiveKey={[]}
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
                <Tabs
                  type="card"
                  size="small"
                  items={['人台图', '平铺图', '时尚拍摄'].map((typeName) => ({
                    key: typeName,
                    label: typeName,
                    children: (
                      <Row gutter={[12, 12]}>
                        {(set.items || [])
                          .filter((item: any) => {
                            const st = item.shoot_type || item.sub_type || item.sub_category || '';
                            return st === typeName || (typeName === '时尚拍摄' && !st);
                          })
                          .map((item: any) => {
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
              ),
            }))}
          />
        )}
        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <Space>
            <Button onClick={() => goToStep(0)}>上一步</Button>
            <Button type="primary" disabled={selectedClothing.length === 0} onClick={() => goToStep(2)}>下一步</Button>
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
          <Button onClick={() => goToStep(1)}>上一步</Button>
        </div>
      </div>
    );
  };

  const renderStep3 = () => (
    <div>
      <h3>{isEditable ? '编辑提示词' : '提示词（只读）'}</h3>
      <Card size="small" title="验收标准" style={{ marginBottom: 16 }}>
        <TextArea
          rows={4}
          value={acceptanceCriteria}
          readOnly={!isEditable}
          onChange={(e) => {
            setAcceptanceCriteria(e.target.value);
            scheduleSave();
          }}
        />
      </Card>
      <Row gutter={[16, 16]}>
        {prompts.map((item) => (
          <Col span={12} key={item.index}>
            <Card size="small" title={<Space><EyeOutlined />{item.angle_name}</Space>}>
              <TextArea
                rows={7}
                value={item.prompt}
                readOnly={!isEditable}
                onChange={(e) => updatePrompt(item.index, e.target.value)}
              />
            </Card>
          </Col>
        ))}
      </Row>
      <div style={{ marginTop: 24, textAlign: 'center' }}>
        <Space>
          <Button onClick={() => goToStep(2)} disabled={!isEditable}>上一步</Button>
          <Button
            icon={<RocketOutlined />}
            type="primary"
            loading={generating}
            disabled={!canGenerate}
            onClick={handleStartGeneration}
          >
            点击生图
          </Button>
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
      {taskStatus === 'failed' && (
        <Alert
          message="生成失败"
          description={
            generationError.includes('database is locked')
              ? '数据库繁忙（生图耗时较长导致锁冲突），请直接重试；若仍失败请运行 ./start.sh restart'
              : generationError.includes('生图API') || generationError.includes('VOLCANO')
                ? `${generationError}。请到「设置」页检查火山 Seedream 配置。`
                : generationError || '请检查火山 Seedream 配置或修改提示词后重试'
          }
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          action={isEditable && prompts.length > 0 ? (
            <Button size="small" onClick={() => { setStudioTaskStatus('prompts_ready'); setCurrentStep(3); }}>
              返回编辑
            </Button>
          ) : undefined}
        />
      )}
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
                    img.id && (
                      <Button
                        key="eval"
                        type="link"
                        icon={<FormOutlined />}
                        onClick={() => setEvalModal({ open: true, imageId: img.id, path: img.path, angle: img.angle })}
                      >
                        评价
                      </Button>
                    ),
                  ].filter(Boolean)}
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
            <Button type="primary" onClick={resetAll}>返回任务列表</Button>
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

  if (viewMode === 'list') {
    return (
      <StudioTaskList
        tasks={studioTasks}
        loading={tasksLoading}
        onNew={handleNewTask}
        onOpen={openTask}
      />
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={backToList}>返回任务列表</Button>
        {studioTaskStatus && (
          <Tag color={studioTaskStatus === 'prompts_ready' ? 'processing' : studioTaskStatus === 'completed' ? 'success' : 'default'}>
            {STATUS_LABEL[studioTaskStatus] || studioTaskStatus}
          </Tag>
        )}
      </div>
      <Steps current={currentStep} items={steps} style={{ marginBottom: 32 }} />
      <Spin spinning={materialsLoading && currentStep < 4} tip="加载素材中...">
        {currentStep === 0 && renderStep0()}
        {currentStep === 1 && renderStep1()}
        {currentStep === 2 && renderStep2()}
        {currentStep === 3 && renderStep3()}
        {currentStep === 4 && renderStep4()}
      </Spin>

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

      <ImageEvaluationModal
        open={evalModal.open}
        imageId={evalModal.imageId}
        imagePath={evalModal.path}
        angle={evalModal.angle}
        onClose={() => setEvalModal({ open: false, imageId: '' })}
        onRegenerated={(newImg) => setGeneratedImages((prev) => [...prev, newImg])}
      />

      {previewItem && (
        <div style={{ display: 'none' }}>
          <Image
            src={toMediaUrl(previewItem, true)}
            preview={{
              visible: true,
              src: toMediaUrl(previewItem, true),
              onVisibleChange: (visible) => {
                if (!visible) setPreviewItem(null);
              },
            }}
          />
        </div>
      )}
    </div>
  );
};

export default LookbookStudio;
