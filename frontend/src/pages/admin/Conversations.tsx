import React, { useEffect, useState } from 'react';
import { Button, Card, Col, List, Row, Typography, message } from 'antd';
import { Link } from 'react-router-dom';
import { adminList, getDefaultAgent } from '../../services/adminApi';

const { Text, Paragraph } = Typography;

const Conversations: React.FC = () => {
  const [sessions, setSessions] = useState<any[]>([]);
  const [active, setActive] = useState<any>(null);
  const [agent, setAgent] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [items, a] = await Promise.all([
        adminList('/api/admin/chat-sessions'),
        getDefaultAgent(),
      ]);
      setSessions(items.sort((x: any, y: any) => (y.updated_at || '').localeCompare(x.updated_at || '')));
      setAgent(a);
      if (!active && items.length) setActive(items[0]);
    } catch {
      message.error('加载对话历史失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const messages = active?.messages_json || active?.messages || [];
  const runId = active?.last_run_id || active?.langfuse_trace_id;

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Conversations</h2>
      <Text type="secondary">Agent 对话历史（本地 SQLite，运行详情见 Runs 账本）</Text>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={8}>
          <Card title="历史记录" size="small" loading={loading}>
            <List
              dataSource={sessions}
              locale={{ emptyText: '暂无对话，可在 Agent 工作室发起' }}
              renderItem={(item: any) => (
                <List.Item
                  style={{ cursor: 'pointer', background: active?.id === item.id ? '#f0f5ff' : undefined, padding: 8, borderRadius: 6 }}
                  onClick={() => setActive(item)}
                >
                  <List.Item.Meta
                    title={item.title || '未命名会话'}
                    description={
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {item.updated_at ? new Date(item.updated_at).toLocaleString() : ''}
                      </Text>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col span={16}>
          <Card
            title={active?.title || '会话详情'}
            size="small"
            extra={
              runId && (
                <Link to={`/admin/runs?id=${runId}`}>
                  <Button type="link" size="small">查看运行记录 →</Button>
                </Link>
              )
            }
          >
            {!active ? (
              <Text type="secondary">选择左侧会话</Text>
            ) : (
              <>
                {(Array.isArray(messages) ? messages : []).map((m: any, i: number) => (
                  <Paragraph key={i}>
                    <Text strong>{m.role === 'user' ? '你' : 'Agent'}：</Text>
                    {m.content}
                  </Paragraph>
                ))}
                {agent && (
                  <Link to="/admin/agents/studio">
                    <Button type="link">继续此 Agent 对话 →</Button>
                  </Link>
                )}
              </>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Conversations;
