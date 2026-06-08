import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import AdminLayout from './layouts/AdminLayout';
import LookbookStudio from './pages/LookbookStudio';
import Materials from './pages/Materials';
import Gallery from './pages/Gallery';
import Settings from './pages/Settings';
import NewTask from './pages/admin/NewTask';
import Conversations from './pages/admin/Conversations';
import AgentsPage from './pages/admin/AgentsPage';
import SkillsPage from './pages/admin/SkillsPage';
import HarnessTestCases from './pages/admin/HarnessTestCases';
import PipelineVersions from './pages/admin/PipelineVersions';
import AgentRuns from './pages/admin/AgentRuns';
import GoldenRegression from './pages/admin/GoldenRegression';
import HarnessPipeline from './pages/HarnessPipeline';
import HarnessTools from './pages/HarnessTools';
import './App.css';

const App: React.FC = () => (
  <Routes>
    <Route element={<MainLayout />}>
      <Route path="/studio" element={<LookbookStudio />} />
      <Route path="/materials" element={<Materials />} />
      <Route path="/history" element={<Gallery />} />
      <Route path="/gallery" element={<Navigate to="/history" replace />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/" element={<LookbookStudio />} />
      <Route path="/harness/*" element={<Navigate to="/admin/harness/testcases" replace />} />
      <Route path="/admin" element={<Navigate to="/admin/new-task" replace />} />
    </Route>

    <Route path="/admin" element={<AdminLayout />}>
      <Route path="new-task" element={<NewTask />} />
      <Route path="conversations" element={<Conversations />} />
      <Route path="runs" element={<AgentRuns />} />
      <Route path="agents" element={<AgentsPage />} />
      <Route path="agents/studio" element={<Navigate to="/admin/agents" replace />} />
      <Route path="skills" element={<SkillsPage />} />
      <Route path="mcp-servers" element={<Navigate to="/admin/conversations" replace />} />
      <Route path="tasks" element={<Navigate to="/studio" replace />} />
      <Route path="harness/testcases" element={<HarnessTestCases />} />
      <Route path="harness/versions" element={<PipelineVersions />} />
      <Route path="harness/modules" element={<Navigate to="/admin/harness/pipeline" replace />} />
      <Route path="harness/pipeline" element={<HarnessPipeline />} />
      <Route path="harness/tools" element={<HarnessTools />} />
      <Route path="harness/prompts" element={<Navigate to="/admin/harness/pipeline" replace />} />
      <Route path="harness/regression" element={<GoldenRegression />} />
      <Route index element={<Navigate to="new-task" replace />} />
    </Route>

    <Route path="*" element={<Navigate to="/studio" replace />} />
  </Routes>
);

export default App;
