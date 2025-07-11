import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { toast } from 'react-hot-toast';
import { 
  ArrowLeftIcon,
  PlayIcon,
  PauseIcon,
  TrashIcon,
  CogIcon,
  ChartBarIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  EyeIcon
} from '@heroicons/react/24/outline';
import { Line, Bar } from 'react-chartjs-2';
import { pipelinesAPI } from '../services/api';

const PipelineDetail = () => {
  const { id } = useParams();
  const [activeTab, setActiveTab] = useState('overview');
  const queryClient = useQueryClient();

  // Fetch pipeline details
  const { data: pipeline, isLoading: pipelineLoading, error: pipelineError } = useQuery(
    ['pipeline', id],
    () => pipelinesAPI.getById(id),
    { select: (data) => data.pipeline }
  );

  // Fetch pipeline runs
  const { data: runsData, isLoading: runsLoading } = useQuery(
    ['pipeline-runs', id],
    () => pipelinesAPI.getRuns(id, { per_page: 50 }),
    { select: (data) => data.runs }
  );

  // Fetch pipeline metrics
  const { data: metricsData, isLoading: metricsLoading } = useQuery(
    ['pipeline-metrics', id],
    () => pipelinesAPI.getMetrics(id, { days: 30 }),
    { select: (data) => data.metrics }
  );

  // Mutations
  const triggerMutation = useMutation(
    () => pipelinesAPI.trigger(id),
    {
      onSuccess: () => {
        toast.success('Pipeline triggered successfully');
        queryClient.invalidateQueries(['pipeline', id]);
        queryClient.invalidateQueries(['pipeline-runs', id]);
      },
      onError: (error) => {
        toast.error(error.response?.data?.error || 'Failed to trigger pipeline');
      }
    }
  );

  const deleteMutation = useMutation(
    () => pipelinesAPI.delete(id),
    {
      onSuccess: () => {
        toast.success('Pipeline deleted successfully');
        // Redirect to pipelines list
        window.location.href = '/pipelines';
      },
      onError: (error) => {
        toast.error(error.response?.data?.error || 'Failed to delete pipeline');
      }
    }
  );

  const handleTrigger = () => {
    triggerMutation.mutate();
  };

  const handleDelete = () => {
    if (window.confirm(`Are you sure you want to delete "${pipeline?.name}"? This action cannot be undone.`)) {
      deleteMutation.mutate();
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'active':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'inactive':
        return <PauseIcon className="h-5 w-5 text-gray-500" />;
      case 'error':
        return <XCircleIcon className="h-5 w-5 text-red-500" />;
      case 'warning':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />;
      default:
        return <ClockIcon className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getRunStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircleIcon className="h-4 w-4 text-red-500" />;
      case 'running':
        return <ClockIcon className="h-4 w-4 text-blue-500" />;
      default:
        return <ClockIcon className="h-4 w-4 text-gray-400" />;
    }
  };

  if (pipelineLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (pipelineError) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <XCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Pipeline Not Found</h2>
          <p className="text-gray-600 mb-4">{pipelineError.message}</p>
          <Link
            to="/pipelines"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Back to Pipelines
          </Link>
        </div>
      </div>
    );
  }

  if (!pipeline) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Pipeline Not Found</h2>
          <Link
            to="/pipelines"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Back to Pipelines
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link
              to="/pipelines"
              className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
            >
              <ArrowLeftIcon className="h-4 w-4 mr-1" />
              Back to Pipelines
            </Link>
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">{pipeline.name}</h1>
              <p className="text-sm text-gray-600">{pipeline.description}</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleTrigger}
              disabled={triggerMutation.isLoading}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
            >
              <PlayIcon className="h-4 w-4 mr-2" />
              {triggerMutation.isLoading ? 'Triggering...' : 'Trigger'}
            </button>
            <button
              onClick={handleDelete}
              disabled={deleteMutation.isLoading}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
            >
              <TrashIcon className="h-4 w-4 mr-2" />
              Delete
            </button>
          </div>
        </div>
      </div>

      {/* Pipeline Status Card */}
      <div className="bg-white shadow rounded-lg p-6 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              {getStatusIcon(pipeline.status)}
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-500">Status</p>
              <p className="text-lg font-semibold text-gray-900">{pipeline.status}</p>
            </div>
          </div>
          
          <div>
            <p className="text-sm font-medium text-gray-500">Type</p>
            <p className="text-lg font-semibold text-gray-900 capitalize">{pipeline.pipeline_type}</p>
          </div>
          
          <div>
            <p className="text-sm font-medium text-gray-500">Uptime</p>
            <p className="text-lg font-semibold text-gray-900">{pipeline.uptime_percentage || 0}%</p>
          </div>
          
          <div>
            <p className="text-sm font-medium text-gray-500">Last Run</p>
            <p className="text-lg font-semibold text-gray-900">
              {pipeline.last_run_at ? new Date(pipeline.last_run_at).toLocaleString() : 'Never'}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            {[
              { id: 'overview', name: 'Overview', icon: EyeIcon },
              { id: 'runs', name: 'Runs', icon: ClockIcon },
              { id: 'metrics', name: 'Metrics', icon: ChartBarIcon },
              { id: 'config', name: 'Configuration', icon: CogIcon }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <tab.icon className="h-4 w-4 inline mr-2" />
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Pipeline Information</h3>
                  <dl className="space-y-3">
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Schedule</dt>
                      <dd className="text-sm text-gray-900">{pipeline.schedule || 'Manual'}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Timeout</dt>
                      <dd className="text-sm text-gray-900">{pipeline.timeout_minutes} minutes</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Retry Attempts</dt>
                      <dd className="text-sm text-gray-900">{pipeline.retry_attempts}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Health Check</dt>
                      <dd className="text-sm text-gray-900">
                        {pipeline.health_check_enabled ? 'Enabled' : 'Disabled'}
                      </dd>
                    </div>
                  </dl>
                </div>
                
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Activity</h3>
                  {runsLoading ? (
                    <div className="animate-pulse space-y-3">
                      {[1, 2, 3].map((i) => (
                        <div key={i} className="h-4 bg-gray-200 rounded"></div>
                      ))}
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {runsData?.slice(0, 5).map((run) => (
                        <div key={run.id} className="flex items-center justify-between">
                          <div className="flex items-center">
                            {getRunStatusIcon(run.status)}
                            <span className="ml-2 text-sm text-gray-900">
                              Run #{run.id}
                            </span>
                          </div>
                          <span className="text-sm text-gray-500">
                            {new Date(run.started_at).toLocaleDateString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Runs Tab */}
          {activeTab === 'runs' && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Pipeline Runs</h3>
              {runsLoading ? (
                <div className="animate-pulse">
                  <div className="h-8 bg-gray-200 rounded mb-4"></div>
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="h-12 bg-gray-200 rounded mb-2"></div>
                  ))}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Run ID
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Started
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Duration
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Records Processed
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {runsData?.map((run) => (
                        <tr key={run.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            #{run.id}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center">
                              {getRunStatusIcon(run.status)}
                              <span className={`ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                run.status === 'success' ? 'bg-green-100 text-green-800' :
                                run.status === 'failed' ? 'bg-red-100 text-red-800' :
                                'bg-blue-100 text-blue-800'
                              }`}>
                                {run.status}
                              </span>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {new Date(run.started_at).toLocaleString()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {run.duration_seconds ? `${run.duration_seconds}s` : '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {run.records_processed || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Metrics Tab */}
          {activeTab === 'metrics' && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Pipeline Metrics</h3>
              {metricsLoading ? (
                <div className="animate-pulse">
                  <div className="h-64 bg-gray-200 rounded"></div>
                </div>
              ) : metricsData ? (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <h4 className="text-md font-medium text-gray-900 mb-4">Success Rate</h4>
                      {metricsData.success_rate && (
                        <Line
                          data={metricsData.success_rate}
                          options={{
                            responsive: true,
                            scales: {
                              y: {
                                beginAtZero: true,
                                max: 100
                              }
                            }
                          }}
                        />
                      )}
                    </div>
                    
                    <div className="bg-gray-50 rounded-lg p-4">
                      <h4 className="text-md font-medium text-gray-900 mb-4">Duration</h4>
                      {metricsData.duration && (
                        <Bar
                          data={metricsData.duration}
                          options={{
                            responsive: true,
                            scales: {
                              y: {
                                beginAtZero: true
                              }
                            }
                          }}
                        />
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500">No metrics available for this pipeline.</p>
              )}
            </div>
          )}

          {/* Configuration Tab */}
          {activeTab === 'config' && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Pipeline Configuration</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <pre className="text-sm text-gray-900 overflow-x-auto">
                  {JSON.stringify(pipeline.config, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PipelineDetail; 