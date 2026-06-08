import React from 'react';
import { Tabs } from 'antd';
import ResourceCrud from '../../components/admin/ResourceCrud';
import { getResourceByKey } from '../../admin/adminResources';
import AgentStudio from './AgentStudio';

const AgentsPage: React.FC = () => (
  <div>
    <h2 style={{ marginTop: 0 }}>Agents</h2>
    <Tabs
      items={[
        { key: 'def', label: 'Agent 定义', children: <ResourceCrud resource={getResourceByKey('agents')!} /> },
        { key: 'studio', label: '工作室 / 调试', children: <AgentStudio /> },
        { key: 'legacy-tc', label: 'Legacy TestCases', children: <ResourceCrud resource={getResourceByKey('test-cases')!} /> },
      ]}
    />
  </div>
);

export default AgentsPage;
