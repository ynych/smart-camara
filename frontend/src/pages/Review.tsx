import React, { useState, useEffect } from 'react';
import {
  Row, Col, Card, Statistic, Tag, Button, Modal, Input,
  Select, Image, message, Spin, Typography, Empty
} from 'antd';
import {
  CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined,
  PictureOutlined, LikeOutlined, DislikeOutlined,
} from '@ant-design/icons';
import {
  getReviewImages, approveImage, rejectImage, getReviewStats, getTasks
} from '../services/api';

const { Text } = Typography;
const { TextArea } = Input;

interface ReviewImage {
  id: string;
  task_id: string;
  file_path: string;
  prompt?: string;
  status: string;
  feedback?: string;
  created_at: string;
}

interface ReviewStats {
  total: number;
  approved: number;
  rejected: number;
  pending: number;
}

const Review: React.FC = () => {
  const [images, setImages] = useState<ReviewImage[]>([]);
  const [stats, setStats] = useState<ReviewStats>({ total: 0, approved: 0, rejected: 0, pending: 0 });
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [taskFilter, setTaskFilter] = useState<string>('');
  const [tasks, setTasks] = useState<any[]>([]);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectImageId, setRejectImageId] = useState<string>('');
  const [rejectFeedback, setRejectFeedback] = useState<string>('');

  const fetchStats = async () => {
    try {
      const res = await getReviewStats();
      setStats(res.data || { total: 0, approved: 0, rejected: 0, pending: 0 });
    } catch (err) {
      // ignore
    }
  };

  const fetchTasks = async () => {
    try {
      const res = await getTasks();
      setTasks(res.data.tasks || res.data.items || res.data || []);
    } catch (err) {
      // ignore
    }
  };

  const fetchImages = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }
      if (taskFilter) {
        params.task_id = taskFilter;
      }
      const res = await getReviewImages(params);
      setImages(res.data.images || res.data.items || res.data || []);
    } catch (err) {
      message.error('获取验收图片失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchTasks();
  }, []);

  useEffect(() => {
    fetchImages();
  }, [statusFilter, taskFilter]);

  const handleApprove = async (id: string) => {
    try {
      await approveImage(id);
      message.success('已标记为合格');
      fetchImages();
      fetchStats();
    } catch (err) {
      message.error('操作失败');
    }
  };

  const handleRejectClick = (id: string) => {
    setRejectImageId(id);
    setRejectFeedback('');
    setRejectModalOpen(true);
  };

  const handleRejectConfirm = async () => {
    if (!rejectFeedback.trim()) {
      message.warning('请填写不合格原因');
      return;
    }
    try {
      await rejectImage(rejectImageId, rejectFeedback);
      message.success('已标记为不合格');
      setRejectModalOpen(false);
      setRejectFeedback('');
      fetchImages();
      fetchStats();
    } catch (err) {
      message.error('操作失败');
    }
  };

  const statusTag = (status: string) => {
    switch (status) {
      case 'approved':
        return <Tag color="success" icon={<CheckCircleOutlined />}>合格</Tag>;
      case 'rejected':
        return <Tag color="error" icon={<CloseCircleOutlined />}>不合格</Tag>;
      case 'pending':
      default:
        return <Tag color="warning" icon={<ClockCircleOutlined />}>待验收</Tag>;
    }
  };

  const passRate = stats.total > 0 ? ((stats.approved / stats.total) * 100).toFixed(1) : '0.0';

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card className="stat-card">
            <Statistic
              title="总生成数"
              value={stats.total}
              prefix={<PictureOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="stat-card">
            <Statistic
              title="合格数"
              value={stats.approved}
              prefix={<LikeOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="stat-card">
            <Statistic
              title="不合格数"
              value={stats.rejected}
              prefix={<DislikeOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="stat-card">
            <Statistic
              title="合格率"
              value={passRate}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 筛选栏 */}
      <div style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
        <Text>按任务筛选：</Text>
        <Select
          placeholder="全部任务"
          allowClear
          style={{ width: 200 }}
          value={taskFilter || undefined}
          onChange={(val) => setTaskFilter(val || '')}
          options={tasks.map((t: any) => ({
            label: t.id?.substring(0, 8) || t.name || '未知任务',
            value: t.id,
          }))}
        />
        <Text style={{ marginLeft: 16 }}>按状态筛选：</Text>
        <Select
          style={{ width: 140 }}
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            { label: '全部', value: 'all' },
            { label: '待验收', value: 'pending' },
            { label: '合格', value: 'approved' },
            { label: '不合格', value: 'rejected' },
          ]}
        />
      </div>

      {/* 图片网格 */}
      <Spin spinning={loading}>
        {images.length === 0 ? (
          <Empty description="暂无验收图片" />
        ) : (
          <Row gutter={[16, 16]}>
            {images.map((img) => (
              <Col key={img.id} xs={24} sm={12} md={8} lg={6}>
                <Card
                  className="image-card"
                  cover={
                    <Image
                      src={img.file_path}
                      alt="生成图片"
                      style={{ height: 240, objectFit: 'cover' }}
                      fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQwIiBoZWlnaHQ9IjI0MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjQwIiBoZWlnaHQ9IjI0MCIgZmlsbD0iI2YwZjBmMCIvPjx0ZXh0IHg9IjEyMCIgeT0iMTIwIiBmb250LXNpemU9IjE0IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjY2NjIj7ml6DnvKk8L3RleHQ+PC9zdmc+"
                    />
                  }
                  actions={
                    img.status === 'pending'
                      ? [
                          <Button
                            key="approve"
                            type="link"
                            style={{ color: '#52c41a' }}
                            icon={<CheckCircleOutlined />}
                            onClick={() => handleApprove(img.id)}
                          >
                            合格
                          </Button>,
                          <Button
                            key="reject"
                            type="link"
                            danger
                            icon={<CloseCircleOutlined />}
                            onClick={() => handleRejectClick(img.id)}
                          >
                            不合格
                          </Button>,
                        ]
                      : []
                  }
                >
                  <Card.Meta
                    title={
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Text ellipsis style={{ maxWidth: 150 }}>{img.prompt?.substring(0, 30) || '无提示词'}</Text>
                        {statusTag(img.status)}
                      </div>
                    }
                    description={
                      <div>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {img.created_at ? new Date(img.created_at).toLocaleString('zh-CN') : ''}
                        </Text>
                        {img.feedback && (
                          <div style={{ marginTop: 4 }}>
                            <Tag color="error">反馈：{img.feedback}</Tag>
                          </div>
                        )}
                      </div>
                    }
                  />
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Spin>

      {/* 不合格反馈弹窗 */}
      <Modal
        title="标记为不合格"
        open={rejectModalOpen}
        onOk={handleRejectConfirm}
        onCancel={() => {
          setRejectModalOpen(false);
          setRejectFeedback('');
        }}
        okText="确认"
        cancelText="取消"
        okButtonProps={{ danger: true }}
      >
        <div style={{ marginBottom: 12 }}>
          <Text>请填写不合格原因，以便后续改进：</Text>
        </div>
        <TextArea
          value={rejectFeedback}
          onChange={(e) => setRejectFeedback(e.target.value)}
          placeholder="例如：服装颜色偏差较大、模特姿势不自然等..."
          autoSize={{ minRows: 3, maxRows: 6 }}
        />
      </Modal>
    </div>
  );
};

export default Review;
