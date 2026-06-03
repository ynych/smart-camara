import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Upload, Button, Steps, Card, Input, Progress, Row, Col, Image, message, Space, Tag, Spin, Descriptions, Radio, Popconfirm, Divider } from 'antd';
import { CameraOutlined, ThunderboltOutlined, CheckCircleOutlined, UserOutlined, SkinOutlined, PlusOutlined, DeleteOutlined, LoadingOutlined } from '@ant-design/icons';
import { uploadSourceImage, analyzeRequirement, getStyles, generateLookbook, updateRequirement, getTask, getTaskList, deleteTask } from '../services/api';

const { Dragger } = Upload;
const { TextArea } = Input;

const LookbookStudio: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [requirementId, setRequirementId] = useState<string | null>(null);
  const [modelImage, setModelImage] = useState<string | null>(null);
  const [clothingImages, setClothingImages] = useState<string[]>([]);
  const [description, setDescription] = useState('');
  const [features, setFeatures] = useState<any>(null);
  const [styles, setStyles] = useState<any[]>([]);
  const [selectedStyle, setSelectedStyle] = useState<string>('');
  const [tasks, setTasks] = useState<any[]>([]);
  const [images, setImages] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const pollingTimers = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map());

  // 加载风格列表
  useEffect(() => {
    getStyles().then(res => setStyles(res.data.styles || [])).catch(() => {});
  }, []);

  // 加载任务列表
  const loadTasks = useCallback(async () => {
    try {
      const res = await getTaskList();
      setTasks(res.data.tasks || []);
    } catch (e) {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadTasks();
    return () => {
      // 清理所有轮询定时器
      pollingTimers.current.forEach(timer => clearInterval(timer));
      pollingTimers.current.clear();
    };
  }, [loadTasks]);

  // 上传模特图
  const handleUploadModel = async (file: File) => {
    try {
      setLoading(true);
      const res = await uploadSourceImage(file, '模特图');
      setModelImage(res.data.file_path);
      if (res.data.requirement_id) {
        setRequirementId(res.data.requirement_id);
      }
      message.success('模特图上传成功');
    } catch (e: any) {
      message.error('上传失败: ' + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
    return false;
  };

  // 上传服装图（支持多张）
  const handleUploadClothing = async (file: File) => {
    try {
      setLoading(true);
      const res = await uploadSourceImage(file, description || '服装图');
      setClothingImages(prev => [...prev, res.data.file_path]);
      if (res.data.requirement_id) {
        setRequirementId(res.data.requirement_id);
      }
      message.success('服装图上传成功');
    } catch (e: any) {
      message.error('上传失败: ' + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
    return false;
  };

  // 删除某张服装图
  const handleRemoveClothing = (index: number) => {
    setClothingImages(prev => prev.filter((_, i) => i !== index));
  };

  // 步骤1: 分析特征
  const handleAnalyze = async () => {
    if (!requirementId) return;
    try {
      setLoading(true);
      const res = await analyzeRequirement(requirementId, description);
      setFeatures(res.data.features);
      setCurrentStep(2);
      message.success('分析完成');
    } catch (e: any) {
      message.error('分析失败: ' + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  // 选择风格
  const handleSelectStyle = (styleId: string) => {
    setSelectedStyle(styleId);
  };

  // 轮询任务状态
  const pollTaskStatus = useCallback((taskId: string) => {
    // 如果已有该任务的轮询，先清除
    if (pollingTimers.current.has(taskId)) {
      clearInterval(pollingTimers.current.get(taskId));
    }

    const timer = setInterval(async () => {
      try {
        const res = await getTask(taskId);
        const taskData = res.data;
        setTasks(prev => {
          const exists = prev.some(t => t.id === taskId);
          if (exists) {
            return prev.map(t => t.id === taskId ? { ...t, ...taskData } : t);
          }
          return prev;
        });

        if (taskData.status === 'completed' || taskData.status === 'failed') {
          clearInterval(timer);
          pollingTimers.current.delete(taskId);

          if (taskData.status === 'completed') {
            setImages(taskData.generated_images || []);
            setCurrentStep(4);
            message.success('Lookbook生成完成！');
          } else {
            message.error('生成失败');
          }
        }
      } catch (e) {
        // ignore polling errors
      }
    }, 3000);

    pollingTimers.current.set(taskId, timer);
  }, []);

  // 确认风格并生成（异步，不阻塞）
  const handleConfirmAndGenerate = async () => {
    if (!requirementId || !selectedStyle) {
      message.warning('请先选择一种风格');
      return;
    }
    try {
      await updateRequirement(requirementId, { selected_style: selectedStyle });
      const res = await generateLookbook(requirementId);
      const newTaskId = res.data.task_id;
      const newTask = {
        id: newTaskId,
        status: 'generating',
        progress: 0,
        created_at: new Date().toISOString(),
      };
      setTasks(prev => [newTask, ...prev]);
      setCurrentStep(3);

      // 开始轮询
      pollTaskStatus(newTaskId);
      message.info('任务已创建，正在后台生成...');
    } catch (e: any) {
      message.error('创建任务失败: ' + (e.response?.data?.detail || e.message));
    }
  };

  // 删除任务
  const handleDeleteTask = async (taskId: string) => {
    try {
      await deleteTask(taskId);
      setTasks(prev => prev.filter(t => t.id !== taskId));
      message.success('任务已删除');
    } catch (e) {
      message.error('删除任务失败');
    }
  };

  // 查看任务结果
  const handleViewTaskResult = (task: any) => {
    if (task.status === 'completed' && task.generated_images) {
      setImages(task.generated_images);
      setCurrentStep(4);
    }
  };

  // 重置
  const handleReset = () => {
    setCurrentStep(0);
    setRequirementId(null);
    setModelImage(null);
    setClothingImages([]);
    setFeatures(null);
    setSelectedStyle('');
    setImages([]);
    setDescription('');
  };

  const steps = [
    { title: '上传素材', icon: <CameraOutlined /> },
    { title: '分析特征', icon: <ThunderboltOutlined /> },
    { title: '选择风格', icon: <CheckCircleOutlined /> },
    { title: '生成中', icon: <LoadingOutlined /> },
    { title: '查看结果', icon: <CheckCircleOutlined /> },
  ];

  // 获取任务状态标签
  const getTaskStatusTag = (status: string) => {
    switch (status) {
      case 'generating':
        return <Tag icon={<LoadingOutlined />} color="processing">生成中</Tag>;
      case 'completed':
        return <Tag icon={<CheckCircleOutlined />} color="success">已完成</Tag>;
      case 'failed':
        return <Tag color="error">失败</Tag>;
      default:
        return <Tag>{status}</Tag>;
    }
  };

  return (
    <div>
      <Steps current={currentStep} items={steps} style={{ marginBottom: 32 }} />

      <Spin spinning={loading} description="处理中...">
        {/* 步骤0: 上传素材 - 多张服装图 + 一张模特图 */}
        {currentStep === 0 && (
          <div style={{ maxWidth: 800, margin: '0 auto' }}>
            <Row gutter={24}>
              <Col span={12}>
                <Card title={<><UserOutlined /> 模特图</>} size="small" extra={<span style={{ fontSize: 12, color: '#999' }}>仅1张</span>}>
                  {modelImage ? (
                    <div style={{ textAlign: 'center' }}>
                      <Image
                        src={`/assets/uploads/${modelImage.split('/').pop()}`}
                        alt="模特图"
                        style={{ maxHeight: 200, borderRadius: 8 }}
                      />
                      <p style={{ color: '#52c41a', marginTop: 8 }}>已上传</p>
                    </div>
                  ) : (
                    <Dragger
                      name="model"
                      multiple={false}
                      accept="image/*"
                      showUploadList={false}
                      beforeUpload={handleUploadModel}
                    >
                      <p className="ant-upload-drag-icon"><UserOutlined style={{ fontSize: 36, color: '#1890ff' }} /></p>
                      <p className="ant-upload-text">点击或拖拽上传模特照片</p>
                      <p className="ant-upload-hint">支持 JPG、PNG</p>
                    </Dragger>
                  )}
                </Card>
              </Col>
              <Col span={12}>
                <Card title={<><SkinOutlined /> 服装图</>} size="small" extra={<span style={{ fontSize: 12, color: '#999' }}>支持多张</span>}>
                  <div style={{ marginBottom: 8, maxHeight: 200, overflow: 'auto' }}>
                    {clothingImages.length > 0 && (
                      <Row gutter={[8, 8]}>
                        {clothingImages.map((img, index) => (
                          <Col span={8} key={index} style={{ position: 'relative' }}>
                            <Image
                              src={`/assets/uploads/${img.split('/').pop()}`}
                              alt={`服装图${index + 1}`}
                              style={{ width: '100%', height: 60, objectFit: 'cover', borderRadius: 4 }}
                            />
                            <Button
                              danger
                              size="small"
                              icon={<DeleteOutlined />}
                              onClick={() => handleRemoveClothing(index)}
                              style={{
                                position: 'absolute', top: -4, right: -4,
                                width: 20, height: 20, minWidth: 20,
                                padding: 0, borderRadius: '50%', fontSize: 10,
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                              }}
                            />
                          </Col>
                        ))}
                      </Row>
                    )}
                  </div>
                  <Dragger
                    name="clothing"
                    multiple={true}
                    accept="image/*"
                    showUploadList={false}
                    beforeUpload={handleUploadClothing}
                  >
                    <p className="ant-upload-drag-icon"><PlusOutlined style={{ fontSize: 28, color: '#1890ff' }} /></p>
                    <p className="ant-upload-text">点击或拖拽上传服装照片</p>
                    <p className="ant-upload-hint">支持多张上传，JPG、PNG</p>
                  </Dragger>
                </Card>
              </Col>
            </Row>
            <div style={{ marginTop: 16 }}>
              <TextArea
                rows={2}
                placeholder="描述服装特征（可选，如：白色连衣裙，简约风格）"
                value={description}
                onChange={e => setDescription(e.target.value)}
              />
            </div>
            <div style={{ marginTop: 16, textAlign: 'center' }}>
              <Button
                type="primary"
                disabled={!modelImage || clothingImages.length === 0}
                onClick={() => setCurrentStep(1)}
              >
                下一步：分析特征
              </Button>
              {!modelImage && <p style={{ color: '#999', marginTop: 8 }}>请先上传模特图</p>}
              {modelImage && clothingImages.length === 0 && <p style={{ color: '#999', marginTop: 8 }}>请上传至少一张服装图</p>}
            </div>
          </div>
        )}

        {/* 步骤1: 分析特征 */}
        {currentStep === 1 && (
          <div style={{ maxWidth: 600, margin: '0 auto', textAlign: 'center' }}>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              {modelImage && (
                <Col span={12}>
                  <Image
                    src={`/assets/uploads/${modelImage.split('/').pop()}`}
                    alt="模特图"
                    style={{ maxHeight: 200, borderRadius: 8 }}
                  />
                  <p>模特图</p>
                </Col>
              )}
              {clothingImages.length > 0 && (
                <Col span={12}>
                  <div style={{ maxHeight: 200, overflow: 'auto' }}>
                    {clothingImages.map((img, index) => (
                      <Image
                        key={index}
                        src={`/assets/uploads/${img.split('/').pop()}`}
                        alt={`服装图${index + 1}`}
                        style={{ maxHeight: 80, borderRadius: 4, marginRight: 4 }}
                      />
                    ))}
                  </div>
                  <p>服装图 ({clothingImages.length}张)</p>
                </Col>
              )}
            </Row>
            <p style={{ marginBottom: 16 }}>AI将分析服装特征并推荐风格</p>
            <Space>
              <Button onClick={() => setCurrentStep(0)}>上一步</Button>
              <Button type="primary" onClick={handleAnalyze} loading={loading}>
                开始分析
              </Button>
            </Space>
          </div>
        )}

        {/* 步骤2: 选择风格 */}
        {currentStep === 2 && (
          <div>
            {features && (
              <Card title="AI识别结果" size="small" style={{ marginBottom: 24 }}>
                <Descriptions column={3} size="small">
                  <Descriptions.Item label="服装类型">{features.clothing_type}</Descriptions.Item>
                  <Descriptions.Item label="颜色">{features.color}</Descriptions.Item>
                  <Descriptions.Item label="风格">{features.style}</Descriptions.Item>
                  <Descriptions.Item label="材质">{features.material}</Descriptions.Item>
                  <Descriptions.Item label="目标人群">{features.target_audience}</Descriptions.Item>
                  <Descriptions.Item label="卖点">{features.selling_points?.join(', ')}</Descriptions.Item>
                </Descriptions>
              </Card>
            )}
            <h3>选择Lookbook风格</h3>
            <Radio.Group
              onChange={(e) => handleSelectStyle(e.target.value)}
              value={selectedStyle}
              style={{ width: '100%' }}
            >
              <Row gutter={16}>
                {styles.map(style => (
                  <Col span={8} key={style.id}>
                    <Radio value={style.id} style={{ width: '100%' }}>
                      <Card
                        hoverable
                        size="small"
                        style={{
                          border: selectedStyle === style.id ? '2px solid #1890ff' : '1px solid #d9d9d9',
                          borderRadius: 8,
                          width: '100%',
                        }}
                      >
                        <Card.Meta
                          title={style.name}
                          description={
                            <div>
                              <p style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>{style.description}</p>
                              <div>
                                {style.angles?.map((a: any, i: number) => (
                                  <Tag key={i} style={{ fontSize: 11 }}>{a.name}</Tag>
                                ))}
                              </div>
                            </div>
                          }
                        />
                      </Card>
                    </Radio>
                  </Col>
                ))}
              </Row>
            </Radio.Group>
            <div style={{ marginTop: 24, textAlign: 'center' }}>
              <Space>
                <Button onClick={() => setCurrentStep(1)}>上一步</Button>
                <Button
                  type="primary"
                  disabled={!selectedStyle}
                  onClick={handleConfirmAndGenerate}
                  loading={loading}
                >
                  确认风格，开始生成
                </Button>
              </Space>
            </div>
          </div>
        )}

        {/* 步骤3: 生成进度 */}
        {currentStep === 3 && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin size="large" />
            <h3 style={{ marginTop: 16 }}>正在生成Lookbook...</h3>
            <p style={{ color: '#999' }}>任务已提交到后台，请稍候。每张图片约需20-30秒。</p>
            <p style={{ color: '#999' }}>您可以在下方任务列表中查看进度。</p>
          </div>
        )}

        {/* 步骤4: 查看结果 */}
        {currentStep === 4 && images.length > 0 && (
          <div>
            <h3>生成结果</h3>
            <Row gutter={[16, 16]}>
              {images.map((img, index) => (
                <Col span={6} key={index}>
                  <Card size="small" cover={
                    <Image
                      src={`/assets/generated/${img.path?.split('/').pop() || img.url}`}
                      alt={img.angle}
                      style={{ height: 240, objectFit: 'cover' }}
                    />
                  }>
                    <Card.Meta title={img.angle} description={<Tag color="green">已完成</Tag>} />
                  </Card>
                </Col>
              ))}
            </Row>
            <div style={{ marginTop: 24, textAlign: 'center' }}>
              <Button type="primary" onClick={handleReset}>
                生成新的Lookbook
              </Button>
            </div>
          </div>
        )}
      </Spin>

      {/* 任务列表区域 - 始终显示在底部 */}
      {tasks.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <Divider />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ margin: 0 }}>任务列表</h3>
            <Button size="small" onClick={loadTasks}>刷新</Button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {tasks.map(task => (
              <Card key={task.id} size="small" style={{ background: '#fafafa' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <Space>
                      <span style={{ fontWeight: 500 }}>任务 {task.id?.slice(0, 8)}...</span>
                      {getTaskStatusTag(task.status)}
                    </Space>
                    {task.progress !== undefined && task.status === 'generating' && (
                      <Progress percent={task.progress} size="small" style={{ width: 200, marginTop: 4 }} />
                    )}
                    <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>
                      {task.created_at && new Date(task.created_at).toLocaleString()}
                    </div>
                  </div>
                  <Space>
                    {task.status === 'completed' && (
                      <Button size="small" type="link" onClick={() => handleViewTaskResult(task)}>查看结果</Button>
                    )}
                    <Popconfirm title="确定删除该任务?" onConfirm={() => handleDeleteTask(task.id)}>
                      <Button danger size="small" icon={<DeleteOutlined />}>删除</Button>
                    </Popconfirm>
                  </Space>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default LookbookStudio;
