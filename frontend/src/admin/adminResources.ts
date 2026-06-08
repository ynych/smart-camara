export type FieldDef = {
  key: string;
  label: string;
  type?: 'text' | 'textarea' | 'json' | 'number' | 'select';
  options?: { value: string; label: string }[];
  required?: boolean;
  table?: boolean;
  width?: number;
};

export type ResourceDef = {
  key: string;
  title: string;
  apiPath: string;
  fields: FieldDef[];
  readOnlyCreate?: boolean;
};

const jsonField = (key: string, label: string, table = false): FieldDef => ({
  key, label, type: 'json', table,
});

export const adminResources: ResourceDef[] = [
  {
    key: 'agents',
    title: 'Agent 定义',
    apiPath: '/api/admin/agents',
    fields: [
      { key: 'slug', label: 'Slug', required: true, table: true },
      { key: 'name', label: '名称', required: true, table: true },
      { key: 'description', label: '描述', type: 'textarea', table: true },
      { key: 'role_prompt', label: '角色 Prompt', type: 'textarea' },
      { key: 'pipeline_config_id', label: 'Pipeline 配置 ID', table: true },
      { key: 'knowledge_tree_id', label: '知识树 ID', table: true },
      jsonField('tool_ids_json', 'Tool IDs (JSON)'),
      jsonField('graph_config_json', 'Graph 配置 (JSON)'),
      { key: 'status', label: '状态', type: 'select', options: [{ value: 'draft', label: '草稿' }, { value: 'published', label: '已发布' }], table: true },
    ],
  },
  {
    key: 'test-cases',
    title: 'Agent TestCase',
    apiPath: '/api/admin/test-cases',
    fields: [
      { key: 'agent_id', label: 'Agent ID', required: true, table: true },
      { key: 'name', label: '名称', required: true, table: true },
      { key: 'description', label: '描述', type: 'textarea' },
      jsonField('inputs_json', '输入 (JSON)', true),
      jsonField('expected_json', '期望 (JSON)'),
      { key: 'sort_order', label: '排序', type: 'number', table: true },
    ],
  },
  {
    key: 'knowledge-trees',
    title: '知识树',
    apiPath: '/api/admin/knowledge-trees',
    fields: [
      { key: 'slug', label: 'Slug', required: true, table: true },
      { key: 'name', label: '名称', required: true, table: true },
      { key: 'description', label: '描述', type: 'textarea', table: true },
      { key: 'root_node_id', label: '根节点 ID' },
      { key: 'version', label: '版本', type: 'number', table: true },
    ],
  },
  {
    key: 'knowledge-nodes',
    title: '知识节点',
    apiPath: '/api/admin/knowledge-nodes',
    fields: [
      { key: 'tree_id', label: '知识树 ID', required: true, table: true },
      { key: 'parent_id', label: '父节点 ID', table: true },
      { key: 'title', label: '标题', required: true, table: true },
      { key: 'summary', label: '摘要', type: 'textarea', table: true },
      { key: 'content', label: '内容', type: 'textarea' },
      { key: 'source_type', label: '来源类型', table: true },
      { key: 'source_ref', label: '来源引用' },
      { key: 'sort_order', label: '排序', type: 'number' },
      jsonField('meta_json', '元数据 (JSON)'),
    ],
  },
  {
    key: 'pipeline-configs',
    title: 'Pipeline 配置',
    apiPath: '/api/admin/pipeline-configs',
    fields: [
      { key: 'slug', label: 'Slug', required: true, table: true },
      { key: 'name', label: '名称', required: true, table: true },
      { key: 'description', label: '描述', type: 'textarea' },
      jsonField('module_order_json', '模块顺序 (JSON)'),
      jsonField('modules_json', '模块定义 (JSON)'),
      { key: 'status', label: '状态', type: 'select', options: [{ value: 'draft', label: '草稿' }, { value: 'published', label: '已发布' }], table: true },
      { key: 'version', label: '版本', type: 'number', table: true },
    ],
  },
  {
    key: 'tool-definitions',
    title: 'Tool 定义',
    apiPath: '/api/admin/tool-definitions',
    fields: [
      { key: 'slug', label: 'Slug', required: true, table: true },
      { key: 'name', label: '名称', required: true, table: true },
      { key: 'handler_key', label: 'Handler Key', required: true, table: true },
      { key: 'description', label: '描述', type: 'textarea' },
      jsonField('module_ids_json', '关联模块 (JSON)'),
      jsonField('input_schema_json', '输入 Schema'),
      jsonField('output_schema_json', '输出 Schema'),
      jsonField('config_json', '配置 (JSON)'),
      { key: 'status', label: '状态', type: 'select', options: [{ value: 'draft', label: '草稿' }, { value: 'published', label: '已发布' }], table: true },
    ],
  },
  {
    key: 'prompt-packs',
    title: '原子提示词包',
    apiPath: '/api/admin/prompt-packs',
    fields: [
      { key: 'domain', label: '领域', table: true },
      { key: 'module_id', label: '模块 ID', table: true },
      { key: 'name', label: '名称', required: true, table: true },
      { key: 'template', label: '模板', type: 'textarea', required: true },
      jsonField('tags_json', '标签 (JSON)'),
      { key: 'status', label: '状态', type: 'select', options: [{ value: 'draft', label: '草稿' }, { value: 'published', label: '已发布' }], table: true },
      { key: 'version', label: '版本', type: 'number', table: true },
    ],
  },
  {
    key: 'golden-cases',
    title: '黄金评测集',
    apiPath: '/api/admin/golden-cases',
    fields: [
      { key: 'name', label: '名称', required: true, table: true },
      { key: 'source_type', label: '来源', table: true },
      { key: 'source_ref', label: '来源 ID', table: true },
      jsonField('context_json', '上下文 (JSON)', true),
      jsonField('human_eval_json', '人工评价 (JSON)'),
      jsonField('baseline_output_json', '基线输出 (JSON)'),
      { key: 'pass_label', label: 'Pass (1/0)', type: 'number', table: true },
      { key: 'notes', label: '备注', type: 'textarea' },
    ],
  },
  {
    key: 'harness-testcases',
    title: 'Harness TestCases',
    apiPath: '/api/admin/harness-testcases',
    fields: [
      { key: 'name', label: '名称', required: true, table: true },
      { key: 'status', label: '状态', table: true },
      { key: 'model_id', label: '模特 ID', table: true },
      { key: 'reference_id', label: '参考图 ID' },
      { key: 'size', label: '尺寸', table: true },
      { key: 'quantity', label: '数量', type: 'number', table: true },
      jsonField('clothing_ids_json', '服装 IDs'),
      jsonField('business_context_json', '商家需求/画像'),
      { key: 'acceptance_criteria', label: '验收标准', type: 'textarea' },
      jsonField('prompts_json', '提示词'),
      jsonField('images_json', '生成图'),
      jsonField('evaluation_json', '评价'),
    ],
  },
  {
    key: 'golden-runs',
    title: '黄金集回归记录',
    apiPath: '/api/admin/golden-runs',
    readOnlyCreate: true,
    fields: [
      { key: 'name', label: '名称', table: true },
      { key: 'target_type', label: '目标类型', table: true },
      { key: 'target_ref', label: '目标 ID', table: true },
      jsonField('metrics_json', '指标 (JSON)', true),
      jsonField('case_results_json', '用例结果 (JSON)'),
    ],
  },
];

export const getResourceByKey = (key: string) => adminResources.find((r) => r.key === key);
