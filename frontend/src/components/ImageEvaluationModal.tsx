import React, { useCallback, useEffect, useState } from 'react';
import {
  Button,
  Col,
  Divider,
  Image,
  Input,
  Modal,
  Rate,
  Row,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd';
import { RobotOutlined, ReloadOutlined, SaveOutlined, ThunderboltOutlined } from '@ant-design/icons';
import {
  generateAiEvaluation,
  getEvaluation,
  optimizeImagePrompt,
  regenerateImage,
  saveEvaluation,
} from '../services/api';
import { toContentUrl } from '../utils/contentUrl';

const { Text, Paragraph, Title } = Typography;
const { TextArea } = Input;

const SCORE_KEYS = [
  { key: 'composition', label: '构图' },
  { key: 'lighting', label: '光线' },
  { key: 'color', label: '色彩' },
  { key: 'model_pose', label: '模特姿态' },
  { key: 'brand_fit', label: '品牌契合' },
];

const overallOptions = [
  { value: 'good', label: '良好' },
  { value: 'fair', label: '一般' },
  { value: 'poor', label: '较差' },
];

export interface ImageEvaluationModalProps {
  open: boolean;
  onClose: () => void;
  imageId: string;
  imagePath?: string;
  angle?: string;
  onRegenerated?: (newImage: any) => void;
}

const ImageEvaluationModal: React.FC<ImageEvaluationModalProps> = ({
  open,
  onClose,
  imageId,
  imagePath,
  angle,
  onRegenerated,
}) => {
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [optimizeLoading, setOptimizeLoading] = useState(false);
  const [regenLoading, setRegenLoading] = useState(false);
  const [overall, setOverall] = useState<string>('fair');
  const [scores, setScores] = useState<Record<string, number>>({});
  const [issues, setIssues] = useState<string[]>(['']);
  const [suggestions, setSuggestions] = useState<string[]>(['']);
  const [expertNote, setExpertNote] = useState('');
  const [aiDraft, setAiDraft] = useState('');
  const [diffOpen, setDiffOpen] = useState(false);
  const [previousPrompt, setPreviousPrompt] = useState('');
  const [optimizedPrompt, setOptimizedPrompt] = useState('');

  const loadEvaluation = useCallback(async () => {
    if (!imageId) return;
    setLoading(true);
    try {
      const res = await getEvaluation(imageId);
      const ev = res.data?.evaluation || res.data;
      if (ev) {
        setOverall(ev.overall || 'fair');
        setScores(ev.scores || {});
        setIssues(ev.issues?.length ? ev.issues : ['']);
        setSuggestions(ev.suggestions?.length ? ev.suggestions : ['']);
        setExpertNote(ev.expert_note || '');
        setAiDraft(ev.ai_draft || '');
      }
    } catch {
      /* 无评价记录 */
    } finally {
      setLoading(false);
    }
  }, [imageId]);

  useEffect(() => {
    if (open && imageId) {
      loadEvaluation();
    }
  }, [open, imageId, loadEvaluation]);

  const buildPayload = () => ({
    overall,
    scores,
    issues: issues.filter((x) => x.trim()),
    suggestions: suggestions.filter((x) => x.trim()),
    expert_note: expertNote,
    ai_draft: aiDraft,
    reviewer_name: '专家',
  });

  const handleSave = async () => {
    try {
      await saveEvaluation(imageId, buildPayload());
      message.success('评价已保存');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败');
    }
  };

  const handleAiDraft = async () => {
    setAiLoading(true);
    try {
      const res = await generateAiEvaluation(imageId);
      const ev = res.data;
      setOverall(ev.overall || 'fair');
      setScores(ev.scores || {});
      setIssues(ev.issues?.length ? ev.issues : ['']);
      setSuggestions(ev.suggestions?.length ? ev.suggestions : ['']);
      setExpertNote(ev.expert_note || '');
      setAiDraft(ev.ai_draft || '');
      message.success('AI 初评已生成，可编辑后保存');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'AI 初评失败，请检查对话模型配置');
    } finally {
      setAiLoading(false);
    }
  };

  const handleOptimize = async () => {
    await handleSave();
    setOptimizeLoading(true);
    try {
      const res = await optimizeImagePrompt(imageId);
      setPreviousPrompt(res.data.previous_prompt || '');
      setOptimizedPrompt(res.data.optimized_prompt || '');
      setDiffOpen(true);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '优化失败');
    } finally {
      setOptimizeLoading(false);
    }
  };

  const handleConfirmRegen = async () => {
    if (!optimizedPrompt.trim()) {
      message.warning('优化后的 prompt 为空');
      return;
    }
    setRegenLoading(true);
    try {
      const res = await regenerateImage(imageId, optimizedPrompt);
      message.success('局部重生完成');
      setDiffOpen(false);
      onRegenerated?.(res.data.image);
      onClose();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '重生失败');
    } finally {
      setRegenLoading(false);
    }
  };

  const updateList = (list: string[], idx: number, val: string, setter: (v: string[]) => void) => {
    const next = [...list];
    next[idx] = val;
    setter(next);
  };

  return (
    <>
      <Modal
        title={`专家评价 · ${angle || '图片'}`}
        open={open}
        onCancel={onClose}
        width={720}
        footer={[
          <Button key="close" onClick={onClose}>关闭</Button>,
          <Button key="ai" icon={<RobotOutlined />} loading={aiLoading} onClick={handleAiDraft}>
            AI 初评
          </Button>,
          <Button key="save" type="default" icon={<SaveOutlined />} onClick={handleSave}>
            保存评价
          </Button>,
          <Button key="opt" type="primary" icon={<ThunderboltOutlined />} loading={optimizeLoading} onClick={handleOptimize}>
            优化并重生成
          </Button>,
        ]}
        destroyOnClose
      >
        <Spin spinning={loading}>
          {imagePath && (
            <Image
              src={toContentUrl(imagePath)}
              alt={angle}
              style={{ maxHeight: 200, objectFit: 'contain', marginBottom: 16, borderRadius: 8 }}
            />
          )}
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Text strong>总体评价</Text>
              <Select
                style={{ width: '100%', marginTop: 8 }}
                value={overall}
                onChange={setOverall}
                options={overallOptions}
              />
            </div>
            <div>
              <Text strong>维度评分（1-5）</Text>
              <Row gutter={[16, 8]} style={{ marginTop: 8 }}>
                {SCORE_KEYS.map(({ key, label }) => (
                  <Col span={12} key={key}>
                    <Text type="secondary">{label}</Text>
                    <Rate
                      count={5}
                      value={scores[key] || 0}
                      onChange={(v) => setScores((s) => ({ ...s, [key]: v }))}
                    />
                  </Col>
                ))}
              </Row>
            </div>
            <div>
              <Text strong>问题清单</Text>
              {issues.map((item, idx) => (
                <Input
                  key={idx}
                  value={item}
                  onChange={(e) => updateList(issues, idx, e.target.value, setIssues)}
                  placeholder="描述发现的问题"
                  style={{ marginTop: 8 }}
                />
              ))}
              <Button type="link" size="small" onClick={() => setIssues([...issues, ''])}>+ 添加问题</Button>
            </div>
            <div>
              <Text strong>优化建议</Text>
              {suggestions.map((item, idx) => (
                <Input
                  key={idx}
                  value={item}
                  onChange={(e) => updateList(suggestions, idx, e.target.value, setSuggestions)}
                  placeholder="可执行的改进建议"
                  style={{ marginTop: 8 }}
                />
              ))}
              <Button type="link" size="small" onClick={() => setSuggestions([...suggestions, ''])}>+ 添加建议</Button>
            </div>
            <div>
              <Text strong>专家备注</Text>
              <TextArea rows={3} value={expertNote} onChange={(e) => setExpertNote(e.target.value)} style={{ marginTop: 8 }} />
            </div>
            {aiDraft && (
              <div>
                <Text strong>AI 初评摘要</Text>
                <Paragraph type="secondary" style={{ marginTop: 8 }}>{aiDraft}</Paragraph>
              </div>
            )}
          </Space>
        </Spin>
      </Modal>

      <Modal
        title="Prompt 优化确认"
        open={diffOpen}
        onCancel={() => setDiffOpen(false)}
        width={800}
        footer={[
          <Button key="cancel" onClick={() => setDiffOpen(false)}>取消</Button>,
          <Button
            key="edit"
            onClick={() => {
              Modal.info({
                title: '编辑优化 Prompt',
                width: 700,
                content: (
                  <TextArea
                    rows={12}
                    defaultValue={optimizedPrompt}
                    onChange={(e) => setOptimizedPrompt(e.target.value)}
                  />
                ),
              });
            }}
          >
            编辑 Prompt
          </Button>,
          <Button key="regen" type="primary" icon={<ReloadOutlined />} loading={regenLoading} onClick={handleConfirmRegen}>
            确认并局部重生
          </Button>,
        ]}
      >
        <Tag color="orange">请人工确认 diff 后再重生</Tag>
        <Divider />
        <Title level={5}>原 Prompt</Title>
        <Paragraph style={{ background: '#fff7e6', padding: 12, borderRadius: 8, whiteSpace: 'pre-wrap' }}>
          {previousPrompt || '（无）'}
        </Paragraph>
        <Title level={5}>优化后 Prompt</Title>
        <TextArea
          rows={10}
          value={optimizedPrompt}
          onChange={(e) => setOptimizedPrompt(e.target.value)}
          style={{ background: '#f6ffed' }}
        />
      </Modal>
    </>
  );
};

export default ImageEvaluationModal;
