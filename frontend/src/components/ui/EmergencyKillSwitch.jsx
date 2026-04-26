// EmergencyControls.jsx
const EmergencyKillSwitch = () => {
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [isTerminating, setIsTerminating] = useState(false);

  const handleEmergencyKill = async () => {
    setIsTerminating(true);
    try {
      const response = await api.post('/admin/system/emergency-kill-streams');
      alert(`Shutdown Successful: ${response.data.terminated_count} streams terminated.`);
      window.location.reload(); // Refresh to show $0 burn
    } catch (err) {
      alert("CRITICAL ERROR: Failed to reach the kill switch.");
    } finally {
      setIsTerminating(false);
    }
  };

  return (
    <div className="bg-red-900/20 border border-red-500/50 p-6 rounded-lg mt-8">
      <h2 className="text-red-500 font-bold uppercase tracking-tighter text-xl">Protocol: Omega</h2>
      <p className="text-sm text-red-300/70 mb-4">Immediate termination of all GCP Livestreaming infrastructure.</p>
      
      {!isUnlocked ? (
        <button 
          onClick={() => setIsUnlocked(true)}
          className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-6 rounded uppercase text-sm"
        >
          Unlock Kill Switch
        </button>
      ) : (
        <div className="flex gap-4">
          <button 
            disabled={isTerminating}
            onClick={handleEmergencyKill}
            className="bg-red-600 hover:bg-red-500 text-white font-black py-4 px-8 rounded flex-1 animate-bounce"
          >
            {isTerminating ? "EXECUTING..." : "CONFIRM: TERMINATE ALL"}
          </button>
          <button 
            onClick={() => setIsUnlocked(false)}
            className="text-gray-400 underline text-xs"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
};
