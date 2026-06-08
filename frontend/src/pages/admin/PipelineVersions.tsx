import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Popconfirm,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  CheckOutlined,
  CloseOutlined,
  CopyOutlined,
  ReloadOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import {
  clonePipelineDraft,
  comparePipelineVersions,
  getPipelineVersions,
  publishPipelineDraft,
  rejectPipelineDraft,
} from '../../services/adminApi';

const { Text, Title } = Typography;

const recColor: Record<string, string> = {
  approve: 'green',
  reject: 'red',
  hold: 'orange',
};

const PipelineVersions: React.FC = () => {
  const [versions, setVersions] = useState<any>(null);
  const [compare, setCompare] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [comparing, setComparing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setVersions(await getPipelineVersions());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const runCompare = async () => {
    setComparing(true);
    try {
      const res = await comparePipelineVersions({});
      setCompare(res);
      message.success('对比完成');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '对比失败');
    } finally {
      setComparing(false);
    }
  };

  const handleClone = async () => {
    try {
      await clonePipelineDraft();
      message.success('已从 published 克隆 draft');
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '克隆失败');
    }
  };

  const handlePublish = async () => {
    try {
      await publishPipelineDraft();
      message.success('draft 已发布');
      setCompare(null);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '发布失败');
    }
  };

  const handleReject = async () => {
    try {
      await rejectPipelineDraft();
      message.success('draft 已驳回');
      setCompare(null);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '驳回失败');
    }
  };

  const pub = versions?.published;
  const draft = versions?.draft;

  const caseColumns = [
    { title: '用例', dataIndex: 'case_name', ellipsis: true },
    { title: 'Pass', dataIndex: 'pass', width: 70, render: (v: boolean) => (v ? <Tag color="green">✓</Tag> : <Tag color="red">✗</Tag>) },
    { title: 'Avg', dataIndex: 'avg', width: 70 },
  ];

  return (
    <div>
      <Title level={4} style={{ marginTop: 0 }}>Harness · Versions</Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
        双轨决策：文本轨（published vs draft 跑 Agent + Judge）与人评轨（Gallery 导入的专家评价基线）等权参考；发布前须人工确认。
      </Text>

      <Row gutter={16}>
        <Col span={12}>
          <Card title="Published" size="small" loading={loading}>
            {pub ? (
              <Descriptions column={1} size="small">
                <Descriptions.Item label="Slug">{pub.slug}</Descriptions.Item>
                <Descriptions.Item label="Version">v{pub.version}</Descriptions.Item>
                <Descriptions.Item label="ID"><Text copyable>{pub.id}</Text></Descriptions.Item>
              </Descriptions>
            ) : (
              <Text type="secondary">无已发布配置</Text>
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card
            title="Draft"
            size="small"
            loading={loading}
            extra={
              <Space>
                <Button size="small" icon={<CopyOutlined />} onClick={handleClone}>克隆</Button>
                {draft && (
                  <>
                    <Popconfirm title="确认发布 draft？用户平台将使用新版 Pipeline" onConfirm={handlePublish}>
                      <Button size="small" type="primary" icon={<CheckOutlined />}>Approve</Button>
                    </Popconfirm>
                    <Popconfirm title="删除 draft？" onConfirm={handleReject}>
                      <Button size="small" danger icon={<CloseOutlined />}>Reject</Button>
                    </Popconfirm>
                  </>
                )}
              </Space>
            }
          >
            {draft ? (
              <Descriptions column={1} size="small">
                <Descriptions.Item label="Slug">{draft.slug}</Descriptions.Item>
                <Descriptions.Item label="Version">v{draft.version}</Descriptions.Item>
                <Descriptions.Item label="状态"><Tag color="orange">draft</Tag></Descriptions.Item>
              </Descriptions>
            ) : (
              <Text type="secondary">无 draft — 在 Pipeline 页编辑模板或运行 optimize 脚本</Text>
            )}
          </Card>
        </Col>
      </Row>

      <Card
        style={{ marginTop: 16 }}
        title={<Space><SwapOutlined /> 双轨对比</Space>}
        extra={
          <Button type="primary" loading={comparing} icon={<ReloadOutlined />} onClick={runCompare} disabled={!draft}>
            运行对比
          </Button>
        }
      >
        {!draft && <Alert type="info" message="请先克隆或创建 draft 后再对比" showIcon />}
        {compare && (
          <>
            <Space style={{ marginBottom: 16 }}>
              <Tag color={recColor[compare.recommendation] || 'default'}>
                建议：{compare.recommendation}
              </Tag>
              <Text type="secondary">{compare.dual_track_note}</Text>
            </Space>
            <Row gutter={16}>
              <Col span={8}>
                <Card size="small" title="Published · 文本轨">
                  <Statistic title="Pass Rate" value={compare.published?.text?.pass_rate} suffix="%" />
                  <Statistic title="Avg Score" value={compare.published?.text?.avg_score} precision={2} style={{ marginTop: 12 }} />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" title="Draft · 文本轨">
                  <Statistic title="Pass Rate" value={compare.draft?.text?.pass_rate} suffix="%" />
                  <Statistic title="Avg Score" value={compare.draft?.text?.avg_score} precision={2} style={{ marginTop: 12 }} />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" title="人评基线（SQLite）">
                  <Statistic title="Good Rate" value={compare.human_baseline?.good_rate ?? '—'} suffix={compare.human_baseline?.good_rate != null ? '%' : ''} />
                  <Statistic title="Avg Score" value={compare.human_baseline?.avg_score ?? '—'} precision={2} style={{ marginTop: 12 }} />
                  <Text type="secondary" style={{ fontSize: 12 }}>{compare.human_baseline?.case_count || 0} 条含人评</Text>
                </Card>
              </Col>
            </Row>
            <Row gutter={16} style={{ marginTop: 16 }}>
              <Col span={12}>
                <Text strong>Published 明细</Text>
                <Table size="small" rowKey="case_id" pagination={false} columns={caseColumns} dataSource={compare.published?.text?.cases || []} />
              </Col>
              <Col span={12}>
                <Text strong>Draft 明细</Text>
                <Table size="small" rowKey="case_id" pagination={false} columns={caseColumns} dataSource={compare.draft?.text?.cases || []} />
              </Col>
            </Row>
          </>
        )}
      </Card>
    </div>
  );
};

export default PipelineVersions;
