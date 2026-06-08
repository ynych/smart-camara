import React from 'react';
import { useParams } from 'react-router-dom';
import ResourceCrud from '../../components/admin/ResourceCrud';
import { getResourceByKey } from '../../admin/adminResources';
import { Empty } from 'antd';

const AdminDataPage: React.FC = () => {
  const { resourceKey } = useParams();
  const resource = getResourceByKey(resourceKey || '');
  if (!resource) {
    return <Empty description="未知资源类型" />;
  }
  return <ResourceCrud resource={resource} />;
};

export default AdminDataPage;
