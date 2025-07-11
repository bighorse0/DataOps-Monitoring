import React from 'react';
import { useQuery } from 'react-query';
import { dashboardAPI } from '../services/api';
import {
  CubeIcon,
  DatabaseIcon,
  BellIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const Dashboard = () => {
  const { data: overview, isLoading: overviewLoading } = useQuery(
    ['dashboard-overview'],
    () => dashboardAPI.getOverview(),
    { refetchInterval: 30000 } // Refresh every 30 seconds
  );

  const { data: pipelineHealth, isLoading: pipelineLoading } = useQuery(
    ['pipeline-health'],
    () => dashboardAPI.getPipelineHealth()
  );

  const { data: recentActivity, isLoading: activityLoading } = useQuery(
    ['recent-activity'],
    () => dashboardAPI.getRecentActivity()
  );

  const { data: metrics, isLoading: metricsLoading } = useQuery(
    ['dashboard-metrics'],
    () => dashboardAPI.getMetrics({ days: 7 })
  );

  if (overviewLoading || pipelineLoading || activityLoading || metricsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  const overviewData = overview?.overview || {};
  const pipelineData = pipelineHealth?.pipelines || [];
  const activityData = recentActivity?.activities || [];
  const metricsData = metrics || {};

  // Prepare chart data
  const pipelineChartData = metricsData.pipeline_metrics || [];
  const healthChartData = metricsData.health_metrics || [];

  const COLORS = ['#22c55e', '#f59e0b', '#ef4444'];

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
      case 'healthy':
        return <CheckCircleIcon className="h-5 w-5 text-success-500" />;
      case 'warning':
        return <ExclamationTriangleIcon className="h-5 w-5 text-warning-500" />;
      case 'failed':
      case 'critical':
        return <XCircleIcon className="h-5 w-5 text-danger-500" />;
      default:
        return <ClockIcon className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'success':
      case 'healthy':
        return 'text-success-600';
      case 'warning':
        return 'text-warning-600';
      case 'failed':
      case 'critical':
        return 'text-danger-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Overview of your data pipelines and monitoring status
        </p>
      </div>

      {/* Overview cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <CubeIcon className="h-6 w-6 text-primary-600" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Pipelines</dt>
                  <dd className="text-lg font-medium text-gray-900">{overviewData.pipelines?.total || 0}</dd>
                </dl>
              </div>
            </div>
            <div className="mt-4">
              <div className="text-sm text-gray-500">
                Uptime: <span className="font-medium text-success-600">{overviewData.pipelines?.uptime_percentage || 0}%</span>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <DatabaseIcon className="h-6 w-6 text-primary-600" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Data Sources</dt>
                  <dd className="text-lg font-medium text-gray-900">{overviewData.data_sources?.total || 0}</dd>
                </dl>
              </div>
            </div>
            <div className="mt-4">
              <div className="text-sm text-gray-500">
                Active: <span className="font-medium text-success-600">{overviewData.data_sources?.active || 0}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <CheckCircleIcon className="h-6 w-6 text-success-600" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Health Checks</dt>
                  <dd className="text-lg font-medium text-gray-900">{overviewData.health_checks?.total || 0}</dd>
                </dl>
              </div>
            </div>
            <div className="mt-4">
              <div className="text-sm text-gray-500">
                Healthy: <span className="font-medium text-success-600">{overviewData.health_checks?.healthy || 0}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <BellIcon className="h-6 w-6 text-warning-600" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Active Alerts</dt>
                  <dd className="text-lg font-medium text-gray-900">{overviewData.alerts?.active || 0}</dd>
                </dl>
              </div>
            </div>
            <div className="mt-4">
              <div className="text-sm text-gray-500">
                Total: <span className="font-medium text-gray-600">{overviewData.alerts?.total || 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Charts and metrics */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Pipeline Success Rate Chart */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Pipeline Success Rate (Last 7 Days)</h3>
          </div>
          <div className="card-body">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={pipelineChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="success_rate" stroke="#22c55e" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Health Check Status Chart */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Health Check Status (Last 7 Days)</h3>
          </div>
          <div className="card-body">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={healthChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="health_rate" stroke="#3b82f6" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Pipeline Health and Recent Activity */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Pipeline Health */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Pipeline Health</h3>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              {pipelineData.slice(0, 5).map((pipeline) => (
                <div key={pipeline.id} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className={`status-indicator ${pipeline.is_healthy ? 'status-healthy' : 'status-critical'}`} />
                    <div className="ml-3">
                      <p className="text-sm font-medium text-gray-900">{pipeline.name}</p>
                      <p className="text-sm text-gray-500">{pipeline.type}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">{pipeline.uptime_percentage}%</p>
                    <p className="text-sm text-gray-500">uptime</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Recent Activity</h3>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              {activityData.slice(0, 5).map((activity, index) => (
                <div key={index} className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-1">
                    {getStatusIcon(activity.status)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{activity.title}</p>
                    <p className="text-sm text-gray-500">{activity.description}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(activity.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 