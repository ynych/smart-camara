import React, { useEffect, useState } from 'react';
import { Button, Card, message } from 'antd';
import { runGoldenRegression } from '../../services/adminApi';
import { getDefaultAgent } from '../../services/adminApi';

const GoldenRegression: React.FC = () => {
  const [agentId, setAgentId] = useState<string>();
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getDefaultAgent().then((a) => setAgentId(a.id)).catch(() => {});
  }, []);

  const run = async () => {
    setLoading(true);
    try {
      const res = await runGoldenRegression({ agent_id: agentId, name: `回归 ${new Date().toLocaleString()}` });
      setResult(res);
      message.success(`Pass rate: ${res.metrics?.pass_rate}%`);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '回归失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>黄金集回归</h2>
      <p>对黄金评测集批量运行 Agent，文本侧 LLM Judge 打分（MVP）。</p>
      <Button type="primary" loading={loading} onClick={run}>运行回归</Button>
      {result && (
        <Card style={{ marginTop: 16 }} title={`Pass Rate: ${result.metrics?.pass_rate}%`}>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{JSON.stringify(result, null, 2)}</pre>
        </Card>
      )}
    </div>
  );
};

export default GoldenRegression;
