import React, { useEffect, useState } from 'react';
import { Card, Table, Tag } from 'antd';
import axios from 'axios';

const API = 'http://127.0.0.1:8155';

const HarnessModules: React.FC = () => {
  const [modules, setModules] = useState<any[]>([]);

  useEffect(() => {
    axios.get(`${API}/api/agent-runtime/modules`).then((r) => setModules(r.data.modules || []));
  }, []);

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Harness · 优化模块</h2>
      <p>已选迭代范围：A1–A8, B1–B3, C1, D1–D2, E1–E2。通过 Promptfoo + Regression 对比 pass_rate。</p>
      <Card size="small">
        <Table
          rowKey="id"
          dataSource={modules}
          pagination={false}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 60 },
            { title: '层级', dataIndex: 'layer', render: (l: string) => <Tag>{l}</Tag> },
            { title: '名称', dataIndex: 'label' },
            { title: '模块/Handler', render: (_: unknown, r: any) => r.module_id || r.handler_key || r.key },
          ]}
        />
      </Card>
    </div>
  );
};

export default HarnessModules;
