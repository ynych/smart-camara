import React from 'react';
import { Tabs } from 'antd';
import ResourceCrud from '../../components/admin/ResourceCrud';
import { getResourceByKey } from '../../admin/adminResources';

const Skills: React.FC = () => (
  <div>
    <h2 style={{ marginTop: 0 }}>Skills</h2>
    <Tabs
      items={[
        {
          key: 'tools',
          label: 'Tool 定义',
          children: <ResourceCrud resource={getResourceByKey('tool-definitions')!} />,
        },
        {
          key: 'prompts',
          label: '原子提示词包',
          children: <ResourceCrud resource={getResourceByKey('prompt-packs')!} />,
        },
      ]}
    />
  </div>
);

export default Skills;
