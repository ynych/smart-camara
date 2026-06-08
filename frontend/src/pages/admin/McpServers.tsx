import React from 'react';
import { Alert, Button, Typography } from 'antd';

const { Paragraph } = Typography;

const McpServers: React.FC = () => (
  <div>
    <h2 style={{ marginTop: 0 }}>MCP Servers</h2>
    <Alert
      type="info"
      showIcon
      message="即将开放"
      description="MCP 注册表将用于挂载外部工具（素材、生图、飞书等）。MVP 占位。"
      style={{ marginBottom: 16 }}
    />
    <Paragraph>规划字段：name、transport、command、env、enabled、tool_prefix</Paragraph>
    <Button disabled>+ 注册 MCP Server</Button>
  </div>
);

export default McpServers;
