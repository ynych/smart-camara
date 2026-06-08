import React, { useCallback, useEffect, useState } from 'react';
import {
  Button,
  Card,
  Checkbox,
  Col,
  Collapse,
  Input,
  Row,
  Space,
  Switch,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import { PlayCircleOutlined, SaveOutlined } from '@ant-design/icons';
import { getHarnessPipeline, runHarnessPipeline } from '../services/api';
import {
  clonePipelineDraft,
  getPipelineVersions,
  updatePipelineDraftModules,
} from '../services/adminApi';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

const DEFAULT_CONTEXT = `{
  "model_id": "",
  "clothing_ids": [],
  "reference_id": "",
  "size": "3:4",
  "model_desc": "优雅的亚洲女性模特",
  "clothing_desc": "时尚服装",
  "scene_desc": "电商Lookbook拍摄场景",
  "style_hint": "",
  "goal_text": "电商 Lookbook 主图/详情页展示",
  "constraint_text": "",
  "angle_name": "正面全身",
  "angle_desc": "模特正面站立，完整展示穿搭",
  "evaluation": {}
}`;

const HarnessPipeline: React.FC = () => {
  const [pipeline, setPipeline] = useState<any>(null);
  const [draftModules, setDraftModules] = useState<Record<string, any>>({});
  const [enabledModules, setEnabledModules] = useState<string[]>([]);
  const [includeRegen, setIncludeRegen] = useState(false);
  const [contextJson, setContextJson] = useState(DEFAULT_CONTEXT);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadPipeline = useCallback(async () => {
    try {
      const [res, versions] = await Promise.all([
        getHarnessPipeline(),
        getPipelineVersions(),
      ]);
      setPipeline(res.data);
      setEnabledModules(res.data.module_order || []);
      const src = versions?.draft?.modules_json || versions?.draft?.modules
        || versions?.published?.modules_json || versions?.published?.modules || res.data.modules;
      const mods = typeof src === 'string' ? JSON.parse(src) : src;
      setDraftModules(mods || {});
    } catch {
      message.error('加载 Pipeline 配置失败');
    }
  }, []);

  useEffect(() => { loadPipeline(); }, [loadPipeline]);

  const ensureDraft = async () => {
    const versions = await getPipelineVersions();
    if (!versions?.draft) {
      await clonePipelineDraft();
      message.info('已自动从 published 克隆 draft');
      await loadPipeline();
    }
  };

  const saveTemplates = async () => {
    setSaving(true);
    try {
      await ensureDraft();
      await updatePipelineDraftModules(draftModules);
      message.success('draft 模板已保存（未发布，请到 Versions 审批）');
      loadPipeline();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleRun = async () => {
    let context: Record<string, unknown>;
    try {
      context = JSON.parse(contextJson);
    } catch {
      message.error('Context JSON 格式错误');
      return;
    }
    setLoading(true);
    try {
      const res = await runHarnessPipeline({
        context,
        enabled_modules: enabledModules,
        include_regen: includeRegen,
      });
      setResult(res.data);
      message.success('Pipeline 执行完成');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '执行失败');
    } finally {
      setLoading(false);
    }
  };

  const moduleItems = (result?.modules || []).map((m: any) => ({
    key: m.module_id,
    label: (
      <Space>
        <Tag>{m.module_id}</Tag>
        <Text>{m.label}</Text>
      </Space>
    ),
    children: (
      <Paragraph style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 13 }}>{m.text}</Paragraph>
    ),
  }));

  const templateEditor = (
    <Row gutter={16}>
      <Col span={24}>
        <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          摄影指导可编辑 A1–A8 的 template 文本；保存写入 draft，须在 Versions 页 Approve 后生效。
        </Text>
        <Space style={{ marginBottom: 12 }}>
          <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={saveTemplates}>
            保存到 draft
          </Button>
        </Space>
      </Col>
      {(pipeline?.module_order || Object.keys(draftModules)).map((id: string) => (
        <Col span={12} key={id} style={{ marginBottom: 12 }}>
          <Card size="small" title={`${id} — ${draftModules[id]?.label || id}`}>
            <TextArea
              rows={6}
              value={draftModules[id]?.template || ''}
              onChange={(e) => setDraftModules((prev) => ({
                ...prev,
                [id]: { ...prev[id], template: e.target.value },
              }))}
            />
          </Card>
        </Col>
      ))}
    </Row>
  );

  const debugPanel = (
    <Row gutter={16}>
      <Col span={10}>
        <Card title="配置" size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text strong>启用模块</Text>
              <Checkbox.Group
                style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}
                value={enabledModules}
                onChange={(v) => setEnabledModules(v as string[])}
                options={(pipeline?.module_order || []).map((id: string) => ({
                  label: `${id} — ${pipeline?.modules?.[id]?.label || id}`,
                  value: id,
                }))}
              />
            </div>
            <Space>
              <Switch checked={includeRegen} onChange={setIncludeRegen} />
              <Text>包含 regen 迭代模块</Text>
            </Space>
            <TextArea rows={14} value={contextJson} onChange={(e) => setContextJson(e.target.value)} />
            <Button type="primary" icon={<PlayCircleOutlined />} loading={loading} onClick={handleRun}>
              运行 Pipeline
            </Button>
          </Space>
        </Card>
      </Col>
      <Col span={14}>
        <Card title="组装结果" size="small">
          {result ? (
            <Space direction="vertical" style={{ width: '100%' }}>
              <Tag color="blue">{result.pipeline_id}</Tag>
              <Text type="secondary">耗时 {result.elapsed_ms}ms</Text>
              <Paragraph
                style={{
                  whiteSpace: 'pre-wrap',
                  background: '#fafafa',
                  padding: 12,
                  borderRadius: 8,
                  border: '1px solid #f0f0f0',
                }}
              >
                {result.prompt}
              </Paragraph>
              <Collapse items={moduleItems} size="small" />
            </Space>
          ) : (
            <Text type="secondary">（等待运行）</Text>
          )}
        </Card>
      </Col>
    </Row>
  );

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Harness · Pipeline</h2>
      <Tabs
        items={[
          { key: 'templates', label: '模板编辑（运营）', children: templateEditor },
          { key: 'debug', label: '调试运行（工程）', children: debugPanel },
        ]}
      />
    </div>
  );
};

export default HarnessPipeline;
