import React, { useState, useEffect } from 'react';
import {
  Row, Col, Card, Select, Radio, Button, Input, Image,
  Space, message, Spin, Typography, Tag, Table, Modal,
  Empty, Tooltip, Popconfirm
} from 'antd';
import {
  ThunderboltOutlined, EyeOutlined,
  DeleteOutlined, ReloadOutlined,
  PictureOutlined, CheckOutlined, CloseOutlined,
} from '@ant-design/icons';
import {
  getDeliveries, createDelivery, updateDelivery,
  deleteDelivery, regenerateDelivery, approveDelivery, rejectDelivery,
  getMaterials, getClothingNames, previewPrompt, createGenerationTask,
  getTasks, getTaskStatus, deleteTask, retryTask, executeTask
} from '../services/api';

const { TextArea } = Input;
const { Text } = Typography;

// 交付物类型配置
const DELIVERY_TYPES = [
  { value: 'main_image', label: '电商主图', icon: '🖼️', desc: '淘宝/京东等平台商品主图' },
  { value: 'detail_image', label: '详情页图', icon: '📄', desc: '商品详情展示图' },
  { value: 'lookbook', label: 'Lookbook', icon: '📚', desc: '时尚画册风格' },
  { value: 'outfit', label: '穿搭图', icon: '👗', desc: '模特上身效果图' },
  { value: 'flat_lay', label: '平铺图', icon: '👕', desc: '服装平铺展示' },
  { value: 'scene', label: '场景图', icon: '🏠', desc: '特定场景下的服装展示' },
];

interface Delivery {
  id: string;
  name: string;
  delivery_type: string;
  status: string;
  prompt?: string;
  feedback?: string;
  created_at: string;
  task_id?: string;
  images?: any[];
}

interface Material {
  id: string;
  name: string;
  category: string;
  sub_category: string;
  clothing_name?: string;
  file_path: string;
  thumbnail_path?: string;
  created_at: string;
}

interface Task {
  id: string;
  status: string;
  prompt?: string;
  size?: string;
  quantity?: number;
  created_at: string;
  images?: any[];
}

const Deliveries: React.FC = () => {
  // 状态
  const [activeTab, setActiveTab] = useState<'create' | 'list'>('create');
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [loading, setLoading] = useState(false);

  // 创建交付物相关
  const [selectedType, setSelectedType] = useState<string>('');
  const [clothingNames, setClothingNames] = useState<string[]>([]);
  const [selectedClothing, setSelectedClothing] = useState<string>('');
  const [clothingMaterials, setClothingMaterials] = useState<Material[]>([]);
  const [selectedMaterials, setSelectedMaterials] = useState<string[]>([]);
  const [gender, setGender] = useState<string>('female');
  const [sceneType, setSceneType] = useState<string>('indoor');
  const [aspectRatio, setAspectRatio] = useState<string>('3:4');
  const [quantity, setQuantity] = useState<number>(4);
  const [prompt, setPrompt] = useState<string>('');
  const [generating, setGenerating] = useState(false);

  // 任务列表相关
  const [tasks, setTasks] = useState<Task[]>([]);
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  // 筛选
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');

  // 反馈弹窗
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
  const [feedbackId, setFeedbackId] = useState<string>('');
  const [feedbackText, setFeedbackText] = useState('');

  useEffect(() => {
    fetchClothingNames();
    fetchDeliveries();
    fetchTasks();
  }, []);

  const fetchClothingNames = async () => {
    try {
      const res = await getClothingNames();
      setClothingNames(res.data.clothing_names || []);
    } catch (err) { /* ignore */ }
  };

  const fetchDeliveries = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      if (typeFilter !== 'all') params.delivery_type = typeFilter;
      const res = await getDeliveries(params);
      setDeliveries(res.data.deliveries || []);
    } catch (err) {
      message.error('获取交付物列表失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchTasks = async () => {
    try {
      const res = await getTasks();
      setTasks(res.data.tasks || []);
    } catch (err) { /* ignore */ }
  };

  const fetchMaterials = async (name: string) => {
    try {
      const res = await getMaterials({ clothing_name: name, category: 'clothing' });
      setClothingMaterials(res.data.materials || res.data.items || []);
      setSelectedMaterials([]);
    } catch (err) { /* ignore */ }
  };

  useEffect(() => {
    if (selectedClothing) fetchMaterials(selectedClothing);
  }, [selectedClothing]);

  const handlePreviewPrompt = async () => {
    if (selectedMaterials.length === 0) {
      message.warning('请先选择服装素材');
      return;
    }
    try {
      const res = await previewPrompt({
        clothing_material_id: selectedMaterials[0],
        model_gender: gender,
        scene_type: sceneType,
        size: aspectRatio,
        clothing_desc: selectedClothing,
      });
      const typeLabel = DELIVERY_TYPES.find(t => t.value === selectedType)?.label || '';
      const enhancedPrompt = `[${typeLabel}] ${res.data.prompt}`;
      setPrompt(enhancedPrompt);
      message.success('提示词生成成功');
    } catch (err) {
      message.error('生成提示词失败');
    }
  };

  const handleCreateDelivery = async () => {
    if (!selectedType || selectedMaterials.length === 0 || !prompt.trim()) {
      message.warning('请完善交付物信息');
      return;
    }
    setGenerating(true);
    try {
      // 1. 创建交付物
      const deliveryRes = await createDelivery({
        name: `${DELIVERY_TYPES.find(t => t.value === selectedType)?.label || ''}-${selectedClothing}`,
        delivery_type: selectedType,
        clothing_material_id: selectedMaterials[0],
        model_gender: gender,
        scene_type: sceneType,
        size: aspectRatio,
        prompt: prompt,
        status: 'pending',
      });

      // 2. 创建生图任务
      const taskRes = await createGenerationTask({
        clothing_material_id: selectedMaterials[0],
        model_gender: gender,
        scene_type: sceneType,
        size: aspectRatio,
        quantity: String(quantity),
        prompt: prompt,
      });

      const taskId = taskRes.data.task?.id;

      // 3. 更新交付物关联任务
      if (taskId) {
        await updateDelivery(deliveryRes.data.delivery?.id, { task_id: taskId });

        // 4. 执行生图
        await executeTask(taskId);

        // 5. 等待图片生成后刷新
        setTimeout(() => {
          fetchTasks();
        }, 2000);
      }

      message.success('交付物创建成功！');
      fetchDeliveries();
      fetchTasks();
      setActiveTab('list');

      // 重置表单
      setSelectedType('');
      setSelectedClothing('');
      setSelectedMaterials([]);
      setPrompt('');
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '创建失败');
    } finally {
      setGenerating(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await approveDelivery(id);
      message.success('已标记为合格');
      fetchDeliveries();
    } catch (err) {
      message.error('操作失败');
    }
  };

  const handleReject = async () => {
    if (!feedbackText.trim()) {
      message.warning('请填写不合格原因');
      return;
    }
    try {
      await rejectDelivery(feedbackId, feedbackText);
      message.success('已标记为不合格');
      setFeedbackModalOpen(false);
      setFeedbackText('');
      fetchDeliveries();
    } catch (err) {
      message.error('操作失败');
    }
  };

  const handleRegenerate = async (delivery: Delivery) => {
    try {
      await regenerateDelivery(delivery.id);
      message.success('已创建新的生成任务');
      fetchTasks();
    } catch (err) {
      message.error('操作失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteDelivery(id);
      message.success('删除成功');
      fetchDeliveries();
    } catch (err) {
      message.error('删除失败');
    }
  };

  const handleRetryTask = async (taskId: string) => {
    try {
      await retryTask(taskId);
      message.success('任务已重新提交');
      fetchTasks();
    } catch (err) {
      message.error('重试失败');
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    try {
      await deleteTask(taskId);
      message.success('任务已删除');
      fetchTasks();
    } catch (err) {
      message.error('删除失败');
    }
  };

  const viewTaskDetail = async (taskId: string) => {
    try {
      const res = await getTaskStatus(taskId);
      setSelectedTask(res.data);
      setTaskModalOpen(true);
    } catch (err) {
      message.error('获取任务详情失败');
    }
  };

  const statusTag = (status: string) => {
    const map: Record<string, { color: string; text: string }> = {
      pending: { color: 'warning', text: '待验收' },
      approved: { color: 'success', text: '合格' },
      rejected: { color: 'error', text: '不合格' },
    };
    const item = map[status] || { color: 'default', text: status };
    return <Tag color={item.color}>{item.text}</Tag>;
  };

  const taskStatusTag = (status: string) => {
    const map: Record<string, { color: string; text: string }> = {
      pending: { color: 'default', text: '排队中' },
      generating: { color: 'processing', text: '生成中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
    };
    const item = map[status] || { color: 'default', text: status };
    return <Tag color={item.color}>{item.text}</Tag>;
  };

  const deliveryTypeTag = (type: string) => {
    const item = DELIVERY_TYPES.find(t => t.value === type);
    return <Tag icon={<span>{item?.icon}</span>}>{item?.label || type}</Tag>;
  };

  // 渲染创建表单
  const renderCreateForm = () => (
    <Row gutter={24}>
      {/* 左侧：参数配置 */}
      <Col span={14}>
        <Card title={<><PictureOutlined /> 交付物配置</>} style={{ marginBottom: 16 }}>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>交付物类型</Text>
          <Row gutter={[8, 8]} style={{ marginBottom: 16 }}>
            {DELIVERY_TYPES.map(type => (
              <Col span={8} key={type.value}>
                <Card
                  size="small"
                  hoverable
                  onClick={() => setSelectedType(type.value)}
                  style={{
                    borderColor: selectedType === type.value ? '#1890ff' : '#f0f0f0',
                    background: selectedType === type.value ? '#e6f7ff' : '#fff',
                    cursor: 'pointer',
                    textAlign: 'center',
                  }}
                >
                  <Text style={{ fontSize: 20 }}>{type.icon}</Text>
                  <br />
                  <Text strong={selectedType === type.value}>{type.label}</Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: 10 }}>{type.desc}</Text>
                </Card>
              </Col>
            ))}
          </Row>

          <div style={{ marginBottom: 12 }}>
            <Text strong style={{ marginBottom: 8, display: 'block' }}>选择服装</Text>
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
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>
                选择素材图片（点击选中）：
              </Text>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {clothingMaterials.map((m) => (
                  <div
                    key={m.id}
                    onClick={() => {
                      setSelectedMaterials(prev =>
                        prev.includes(m.id) ? prev.filter(id => id !== m.id) : [...prev, m.id]
                      );
                    }}
                    style={{
                      width: 70, height: 70,
                      border: selectedMaterials.includes(m.id) ? '2px solid #1890ff' : '2px solid #f0f0f0',
                      borderRadius: 8, overflow: 'hidden', cursor: 'pointer',
                    }}
                  >
                    <Image
                      src={m.thumbnail_path || m.file_path}
                      width={66} height={66}
                      style={{ objectFit: 'cover' }}
                      preview={false}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ marginBottom: 12 }}>
            <Text strong style={{ marginBottom: 8, display: 'block' }}>参数配置</Text>
            <Space wrap>
              <div>
                <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>性别</Text>
                <Radio.Group value={gender} onChange={e => setGender(e.target.value)}>
                  <Radio.Button value="female">女性</Radio.Button>
                  <Radio.Button value="male">男性</Radio.Button>
                </Radio.Group>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>场景</Text>
                <Radio.Group value={sceneType} onChange={e => setSceneType(e.target.value)}>
                  <Radio.Button value="indoor">室内</Radio.Button>
                  <Radio.Button value="outdoor">室外</Radio.Button>
                </Radio.Group>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>尺寸</Text>
                <Radio.Group value={aspectRatio} onChange={e => setAspectRatio(e.target.value)}>
                  <Radio.Button value="1:1">1:1</Radio.Button>
                  <Radio.Button value="3:4">3:4</Radio.Button>
                  <Radio.Button value="9:16">9:16</Radio.Button>
                </Radio.Group>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>数量</Text>
                <Radio.Group value={quantity} onChange={e => setQuantity(e.target.value)}>
                  <Radio.Button value={1}>1张</Radio.Button>
                  <Radio.Button value={4}>4张</Radio.Button>
                  <Radio.Button value={6}>6张</Radio.Button>
                </Radio.Group>
              </div>
            </Space>
          </div>
        </Card>
      </Col>

      {/* 右侧：提示词编辑 */}
      <Col span={10}>
        <Card title={<><EyeOutlined /> 提示词编辑</>} style={{ marginBottom: 16 }}>
          <Button
            type="dashed"
            icon={<ThunderboltOutlined />}
            onClick={handlePreviewPrompt}
            block
            style={{ marginBottom: 12 }}
          >
            生成提示词
          </Button>
          <TextArea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="点击上方按钮自动生成，或手动编辑..."
            autoSize={{ minRows: 6, maxRows: 12 }}
            style={{ marginBottom: 12 }}
          />
        </Card>

        <Card size="small">
          <div style={{ marginBottom: 12 }}>
            <Text strong>验收标准摘要</Text>
            <div style={{ marginTop: 8 }}>
              {selectedType && (
                <Tag color="blue">{DELIVERY_TYPES.find(t => t.value === selectedType)?.label}</Tag>
              )}
              {selectedClothing && <Tag color="green">{selectedClothing}</Tag>}
              <Tag color="orange">{gender === 'female' ? '女性' : '男性'}模特</Tag>
              <Tag color="purple">{sceneType === 'indoor' ? '室内' : '室外'}场景</Tag>
              <Tag color="cyan">{aspectRatio}</Tag>
              <Tag>{quantity}张</Tag>
            </div>
          </div>

          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={handleCreateDelivery}
            loading={generating}
            block
            size="large"
            style={{ height: 56, fontSize: 18 }}
          >
            开始生成
          </Button>
        </Card>
      </Col>
    </Row>
  );

  // 渲染交付物列表
  const renderDeliveryList = () => (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
        <Select
          placeholder="按类型筛选"
          style={{ width: 150 }}
          value={typeFilter || undefined}
          onChange={(val) => { setTypeFilter(val || 'all'); }}
          allowClear
          options={[
            { label: '全部类型', value: 'all' },
            ...DELIVERY_TYPES.map(t => ({ label: t.label, value: t.value })),
          ]}
        />
        <Select
          style={{ width: 120 }}
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            { label: '全部', value: 'all' },
            { label: '待验收', value: 'pending' },
            { label: '合格', value: 'approved' },
            { label: '不合格', value: 'rejected' },
          ]}
        />
        <Button onClick={fetchDeliveries}>刷新</Button>
      </div>

      {deliveries.length === 0 ? (
        <Empty description="暂无交付物" />
      ) : (
        <Row gutter={[16, 16]}>
          {deliveries.map(d => (
            <Col xs={24} sm={12} md={8} lg={6} key={d.id}>
              <Card
                cover={
                  <div style={{ height: 200, background: '#f5f5f5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Text type="secondary">暂无预览图</Text>
                  </div>
                }
                actions={
                  d.status === 'pending' ? [
                    <Tooltip title="合格"><Button type="text" icon={<CheckOutlined />} onClick={() => handleApprove(d.id)} style={{ color: '#52c41a' }} /></Tooltip>,
                    <Tooltip title="不合格"><Button type="text" icon={<CloseOutlined />} onClick={() => { setFeedbackId(d.id); setFeedbackModalOpen(true); }} style={{ color: '#ff4d4f' }} /></Tooltip>,
                    <Tooltip title="重新生成"><Button type="text" icon={<ReloadOutlined />} onClick={() => handleRegenerate(d)} /></Tooltip>,
                  ] : [
                    <Tooltip title="重新生成"><Button type="text" icon={<ReloadOutlined />} onClick={() => handleRegenerate(d)} /></Tooltip>,
                    <Popconfirm title="确认删除？" onConfirm={() => handleDelete(d.id)}>
                      <Button type="text" danger icon={<DeleteOutlined />} />
                    </Popconfirm>,
                  ]
                }
              >
                <Card.Meta
                  title={
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text ellipsis style={{ maxWidth: 120 }}>{d.name}</Text>
                      {statusTag(d.status)}
                    </div>
                  }
                  description={
                    <div>
                      {deliveryTypeTag(d.delivery_type)}
                      {d.task_id && (
                        <Button type="link" size="small" onClick={() => viewTaskDetail(d.task_id!)}>
                          查看任务
                        </Button>
                      )}
                    </div>
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  );

  // 渲染任务列表
  const renderTaskList = () => (
    <Card title="生图任务" style={{ marginBottom: 16 }}>
      <Table
        dataSource={tasks}
        rowKey="id"
        pagination={{ pageSize: 10 }}
        columns={[
          { title: '任务ID', dataIndex: 'id', render: (id: string) => id.substring(0, 8) + '...' },
          { title: '状态', dataIndex: 'status', render: (s: string) => taskStatusTag(s) },
          { title: '尺寸', dataIndex: 'size' },
          { title: '数量', dataIndex: 'quantity' },
          {
            title: '创建时间',
            dataIndex: 'created_at',
            render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-'
          },
          {
            title: '操作',
            render: (_: any, record: Task) => (
              <Space>
                <Button size="small" onClick={() => viewTaskDetail(record.id)}>查看</Button>
                {record.status === 'failed' && (
                  <Button size="small" onClick={() => handleRetryTask(record.id)}>重试</Button>
                )}
                <Popconfirm title="确认删除？" onConfirm={() => handleDeleteTask(record.id)}>
                  <Button size="small" danger>删除</Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
    </Card>
  );

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Radio.Group value={activeTab} onChange={e => setActiveTab(e.target.value)}>
          <Radio.Button value="create">创建交付物</Radio.Button>
          <Radio.Button value="list">交付物列表</Radio.Button>
        </Radio.Group>
        {activeTab === 'list' && (
          <Button onClick={() => setTaskModalOpen(true)}>查看任务</Button>
        )}
      </div>

      <Spin spinning={loading}>
        {activeTab === 'create' ? renderCreateForm() : renderDeliveryList()}
        {activeTab === 'list' && tasks.length > 0 && renderTaskList()}
      </Spin>

      {/* 任务详情弹窗 */}
      <Modal
        title="任务详情"
        open={taskModalOpen}
        onCancel={() => setTaskModalOpen(false)}
        footer={null}
        width={600}
      >
        {selectedTask && (
          <div>
            <p><Text strong>任务ID：</Text>{selectedTask.id}</p>
            <p><Text strong>状态：</Text>{taskStatusTag(selectedTask.status)}</p>
            <p><Text strong>提示词：</Text></p>
            <TextArea value={selectedTask.prompt || ''} readOnly autoSize />
            {selectedTask.images && selectedTask.images.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Text strong>生成图片：</Text>
                <Row gutter={[8, 8]} style={{ marginTop: 8 }}>
                  {selectedTask.images.map((img: any) => (
                    <Col span={6} key={img.id}>
                      <Image src={img.file_path} width="100%" height={100} style={{ objectFit: 'cover' }} />
                    </Col>
                  ))}
                </Row>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* 反馈弹窗 */}
      <Modal
        title="标记为不合格"
        open={feedbackModalOpen}
        onOk={handleReject}
        onCancel={() => { setFeedbackModalOpen(false); setFeedbackText(''); }}
        okText="确认"
        okButtonProps={{ danger: true }}
      >
        <p>请填写不合格原因：</p>
        <TextArea
          value={feedbackText}
          onChange={(e) => setFeedbackText(e.target.value)}
          placeholder="例如：服装颜色偏差较大、模特姿势不自然等..."
          autoSize={{ minRows: 3 }}
        />
      </Modal>
    </div>
  );
};

export default Deliveries;
