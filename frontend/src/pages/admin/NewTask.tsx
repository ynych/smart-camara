import React from 'react';
import { Button, Card, Steps, Typography } from 'antd';
import { Link } from 'react-router-dom';

const { Paragraph, Text } = Typography;

const NewTask: React.FC = () => (
  <div>
    <h2 style={{ marginTop: 0 }}>New Task</h2>
    <Paragraph>创建 Lookbook 任务的推荐路径：</Paragraph>
    <Steps
      direction="vertical"
      current={-1}
      items={[
        { title: '选择素材', description: '模特、服装、参考图' },
        { title: 'Conversations / Agent', description: '与 Agent 对话补全需求，或在工作台生成提示词' },
        { title: 'Seedream 生图', description: '执行生图并验收' },
        { title: 'Harness TestCase', description: '沉淀为 TestCase，驱动模块迭代' },
      ]}
    />
    <Card style={{ marginTop: 24 }}>
      <Link to="/studio"><Button type="primary">打开生图工作台</Button></Link>
      <Link to="/admin/conversations" style={{ marginLeft: 12 }}>
        <Button>Agent 对话</Button>
      </Link>
      <Link to="/admin/harness/testcases" style={{ marginLeft: 12 }}>
        <Button>Harness TestCases</Button>
      </Link>
    </Card>
    <Text type="secondary" style={{ display: 'block', marginTop: 16 }}>
      完整向导将与 Harness TestCase 合并为一条链路（MVP 先跳转现有页面）。
    </Text>
  </div>
);

export default NewTask;
