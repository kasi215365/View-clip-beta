// AdminDashboard.jsx / SystemHealth.jsx
const BurnRateMonitor = ({ gcp_burn_stats }) => {
  const { active_channels, estimated_hourly_cost, mode } = gcp_burn_stats;

  return (
    <div className={`p-6 border-2 rounded-lg ${active_channels > 0 ? 'border-amber-500 animate-pulse' : 'border-cyan-500'}`}>
      <h3 className="text-xs uppercase tracking-widest text-gray-400">GCP Infrastructure Burn</h3>
      
      <div className="flex items-baseline gap-2 mt-2">
        <span className="text-4xl font-bold font-mono">
          ${estimated_hourly_cost.toFixed(2)}
        </span>
        <span className="text-sm text-gray-500">/ hr</span>
      </div>

      <div className="mt-4 flex justify-between items-center">
        <span className="text-sm font-medium uppercase">
          Status: {active_channels > 0 ? 'ACTIVE STREAMS' : 'IDLE'}
        </span>
        <span className="text-xs font-mono bg-gray-800 px-2 py-1 rounded">
          {active_channels} CHANNELS
        </span>
      </div>
    </div>
  );
};
