import BurnRateMonitor from '@/components/ui/BurnRateMonitor';
import EmergencyKillSwitch from '@/components/ui/EmergencyKillSwitch';

import { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Upload, LogOut, User as UserIcon, Home, Radio, Shield, Settings as SettingsIcon, Banknote, AlertTriangle, Megaphone, Users2, BarChart3, Trash2, Copy, Download, RefreshCcw, KeyRound } from 'lucide-react';
import Logo from '@/components/Logo';
import NotificationBell from '@/components/NotificationBell';
import axios from 'axios';
import { toast } from 'sonner';

const AdminDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [settings, setSettings] = useState(null);
  const [promos, setPromos] = useState([]);
  const [payouts, setPayouts] = useState([]);
  const [content, setContent] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newContent, setNewContent] = useState({ title: '', description: '', type: 'movie', video_url: '', thumbnail_url: '', duration: 0 });
  const [newPromo, setNewPromo] = useState({ title: '', description: '', thumbnail_url: '', video_url: '' });

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    try {
      const [s, u, st, p, pay, c] = await Promise.all([
        axios.get(`${API}/admin/stats`),
        axios.get(`${API}/admin/users`),
        axios.get(`${API}/admin/settings`),
        axios.get(`${API}/promos`),
        axios.get(`${API}/admin/payouts`),
        axios.get(`${API}/content`),
      ]);
      setStats(s.data);
      setUsers(u.data.users);
      setSettings(st.data);
      setPromos(p.data);
      setPayouts(pay.data.payouts);
      setContent(c.data);
    } catch (e) {
      toast.error('Failed to load admin data');
    }
  };

  const handleSettingChange = (field, value) => {
    setSettings((s) => ({ ...s, [field]: value }));
  };

  const saveSettings = async () => {
    try {
      const res = await axios.post(`${API}/admin/settings`, {
        viewer_sub_price: Number(settings.viewer_sub_price),
        streamer_sub_price: Number(settings.streamer_sub_price),
        earnings_per_view: Number(settings.earnings_per_view),
        view_threshold_minutes: Number(settings.view_threshold_minutes),
        gift_base_rate: Number(settings.gift_base_rate),
        budget_alert_percent: Number(settings.budget_alert_percent),
        maintenance_mode: !!settings.maintenance_mode,
      });
      setSettings(res.data);
      toast.success('Settings saved');
    } catch (e) {
      toast.error('Failed to save settings');
    }
  };

  const triggerPayouts = async () => {
    if (!window.confirm('Process payouts for all streamers now?')) return;
    try {
      const r = await axios.post(`${API}/admin/payouts/trigger`);
      toast.success(`Paid ${r.data.streamers_paid} streamers · $${r.data.total_paid}`);
      fetchAll();
    } catch (e) {
      toast.error('Payout failed');
    }
  };

  const handleContentSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/content`, { ...newContent, is_promo: false });
      toast.success('Content uploaded');
      setNewContent({ title: '', description: '', type: 'movie', video_url: '', thumbnail_url: '', duration: 0 });
      fetchAll();
    } catch (e) { toast.error('Upload failed'); } finally { setLoading(false); }
  };

  const handlePromoSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/promos`, newPromo);
      toast.success('Promo created');
      setNewPromo({ title: '', description: '', thumbnail_url: '', video_url: '' });
      fetchAll();
    } catch (e) { toast.error('Promo create failed'); }
  };

  const deletePromo = async (id) => {
    try { await axios.delete(`${API}/promos/${id}`); toast.success('Promo deleted'); fetchAll(); }
    catch (e) { toast.error('Delete failed'); }
  };

  const handleSample = async () => {
    setLoading(true);
    const samples = [
      { title: 'Epic Adventure', description: 'Breathtaking journey.', type: 'movie', video_url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4', thumbnail_url: 'https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=800', duration: 7200 },
      { title: 'Mystery Series S01E01', description: 'Edge of your seat.', type: 'tv-show', video_url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4', thumbnail_url: 'https://images.unsplash.com/photo-1598899134739-24c46f58b8c0?w=800', duration: 3600 },
      { title: 'Championship Finals', description: 'Live sports action.', type: 'sport', video_url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4', thumbnail_url: 'https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=800', duration: 5400 },
    ];
    try { for (const s of samples) await axios.post(`${API}/content`, { ...s, is_promo: false }); toast.success('Sample data loaded'); fetchAll(); }
    catch (e) { toast.error('Failed to load sample data'); } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-[#05070F] text-white">
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-3"><Logo size="md" /><span className="hidden md:flex text-xs bg-fuchsia-500/20 text-fuchsia-300 px-2 py-1 rounded">COMMAND CENTER</span></div>
          <div className="flex items-center space-x-4">
            <Button data-testid="browse-nav-btn" onClick={() => navigate('/browse')} variant="ghost" className="text-white hover:text-cyan-400"><Home className="w-4 h-4 mr-2" />Browse</Button>
            <Button data-testid="live-nav-btn" onClick={() => navigate('/live')} variant="ghost" className="text-white hover:text-cyan-400"><Radio className="w-4 h-4 mr-2" />Live</Button>
            <Button data-testid="admin-nav-btn" onClick={() => navigate('/admin')} variant="ghost" className="text-cyan-400">Admin</Button>
            <NotificationBell />
            <Button data-testid="profile-nav-btn" onClick={() => navigate('/profile')} variant="ghost" className="text-white hover:text-cyan-400"><UserIcon className="w-4 h-4 mr-2" />Profile</Button>
            <Button data-testid="logout-nav-btn" onClick={logout} variant="ghost" className="text-white hover:text-red-400"><LogOut className="w-4 h-4" /></Button>
          </div>
        </div>
      </nav>

      <div className="pt-24 px-6 pb-12">
        <div className="max-w-7xl mx-auto">
          <div className="mb-6 flex items-center gap-3">
            <Shield className="w-8 h-8 text-fuchsia-400" />
            <h1 className="text-4xl font-bold">Admin Command Center</h1>
          </div>

          {/* Top-line stats */}
          {stats && (
            <div data-testid="admin-stats" className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <StatCard label="Users" value={stats.users.total} sub={`${stats.users.streamers} streamers`} icon={<Users2 className="w-6 h-6" />} color="cyan" />
              <StatCard label="Active Subs" value={stats.users.active_subscriptions} icon={<Banknote className="w-6 h-6" />} color="green" />
              <StatCard label="Live Streams" value={stats.streams.live_now} sub={`${stats.streams.total} total`} icon={<Radio className="w-6 h-6" />} color="red" />
              <StatCard label="Revenue" value={`$${stats.financials.total_revenue.toFixed(2)}`} sub={`Owed: $${stats.financials.total_payouts_owed.toFixed(2)}`} icon={<BarChart3 className="w-6 h-6" />} color="fuchsia" />
            </div>
          )}

          <Tabs defaultValue="settings" className="w-full">
            <TabsList className="grid w-full grid-cols-6 bg-white/5 mb-6">
              <TabsTrigger data-testid="tab-settings" value="settings"><SettingsIcon className="w-4 h-4 mr-2" />Settings</TabsTrigger>
              <TabsTrigger data-testid="tab-content" value="content"><Upload className="w-4 h-4 mr-2" />Content</TabsTrigger>
              <TabsTrigger data-testid="tab-promos" value="promos"><Megaphone className="w-4 h-4 mr-2" />Promos</TabsTrigger>
              <TabsTrigger data-testid="tab-users" value="users"><Users2 className="w-4 h-4 mr-2" />Users</TabsTrigger>
              <TabsTrigger data-testid="tab-payouts" value="payouts"><Banknote className="w-4 h-4 mr-2" />Payouts</TabsTrigger>
              <TabsTrigger data-testid="tab-system" value="system"><Shield className="w-4 h-4 mr-2" />System</TabsTrigger>
            </TabsList>

            {/* SETTINGS */}
            <TabsContent value="settings">
              {settings && (
                <div className="grid lg:grid-cols-2 gap-6">
                  <div className="glass-panel rounded-xl p-6">
                    <h3 className="text-xl font-bold mb-4">Platform Rates</h3>
                    <SettingRow label="Viewer Subscription ($/mo)" testid="setting-viewer-sub">
                      <Input type="number" step="0.01" value={settings.viewer_sub_price} onChange={(e) => handleSettingChange('viewer_sub_price', e.target.value)} className="bg-white/5 border-white/10" />
                    </SettingRow>
                    <SettingRow label="Streamer Subscription ($/mo)" testid="setting-streamer-sub">
                      <Input type="number" step="0.01" value={settings.streamer_sub_price} onChange={(e) => handleSettingChange('streamer_sub_price', e.target.value)} className="bg-white/5 border-white/10" />
                    </SettingRow>
                    <SettingRow label="Earnings per qualified view ($)" testid="setting-earnings-view">
                      <Input type="number" step="0.0001" value={settings.earnings_per_view} onChange={(e) => handleSettingChange('earnings_per_view', e.target.value)} className="bg-white/5 border-white/10" />
                    </SettingRow>
                    <SettingRow label="View threshold (minutes)" testid="setting-threshold">
                      <Input type="number" value={settings.view_threshold_minutes} onChange={(e) => handleSettingChange('view_threshold_minutes', e.target.value)} className="bg-white/5 border-white/10" />
                    </SettingRow>
                    <SettingRow label="Gift base rate ($)" testid="setting-gift-base">
                      <Input type="number" step="0.0001" value={settings.gift_base_rate} onChange={(e) => handleSettingChange('gift_base_rate', e.target.value)} className="bg-white/5 border-white/10" />
                    </SettingRow>
                  </div>

                  <div className="glass-panel rounded-xl p-6">
                    <h3 className="text-xl font-bold mb-4 flex items-center"><AlertTriangle className="w-5 h-5 mr-2 text-yellow-400" />Budget Alert & System</h3>
                    <div className="mb-4">
                      <Label>Bandwidth/Budget Alert Threshold ({settings.budget_alert_percent}%)</Label>
                      <input data-testid="setting-budget-percent" type="range" min="10" max="100" value={settings.budget_alert_percent}
                        onChange={(e) => handleSettingChange('budget_alert_percent', Number(e.target.value))}
                        className="w-full mt-2 accent-fuchsia-500" />
                      <p className="text-xs text-gray-400 mt-1">Cap bandwidth if cloud bill hits this % of budget.</p>
                    </div>
                    <SettingRow label="Maintenance Mode" testid="setting-maintenance">
                      <label className="inline-flex items-center cursor-pointer">
                        <input type="checkbox" checked={!!settings.maintenance_mode} onChange={(e) => handleSettingChange('maintenance_mode', e.target.checked)} className="sr-only peer" />
                        <div className="relative w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:start-0.5 after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-fuchsia-500"></div>
                      </label>
                    </SettingRow>
                    <Button data-testid="save-settings-btn" onClick={saveSettings} className="w-full mt-4 bg-cyan-400 text-[#05070F] hover:bg-cyan-300 font-semibold">Save Settings</Button>
                  </div>
                </div>
              )}
            </TabsContent>

            {/* CONTENT */}
            <TabsContent value="content">
              <div className="grid lg:grid-cols-2 gap-6">
                <div className="glass-panel rounded-xl p-6">
                  <h3 className="text-xl font-bold mb-4">Upload Content</h3>
                  <form onSubmit={handleContentSubmit} className="space-y-3">
                    <Input data-testid="content-title-input" placeholder="Title" value={newContent.title} onChange={(e) => setNewContent({ ...newContent, title: e.target.value })} required className="bg-white/5 border-white/10" />
                    <Textarea data-testid="content-description-input" placeholder="Description" value={newContent.description} onChange={(e) => setNewContent({ ...newContent, description: e.target.value })} required className="bg-white/5 border-white/10" />
                    <Select value={newContent.type} onValueChange={(v) => setNewContent({ ...newContent, type: v })}>
                      <SelectTrigger data-testid="content-type-select" className="bg-white/5 border-white/10"><SelectValue /></SelectTrigger>
                      <SelectContent className="bg-[#0A0E27] border-white/10"><SelectItem value="movie">Movie</SelectItem><SelectItem value="tv-show">TV Show</SelectItem><SelectItem value="sport">Sport</SelectItem></SelectContent>
                    </Select>
                    <Input data-testid="content-video-input" placeholder="Video URL" value={newContent.video_url} onChange={(e) => setNewContent({ ...newContent, video_url: e.target.value })} required className="bg-white/5 border-white/10" />
                    <Input data-testid="content-thumbnail-input" placeholder="Thumbnail URL" value={newContent.thumbnail_url} onChange={(e) => setNewContent({ ...newContent, thumbnail_url: e.target.value })} required className="bg-white/5 border-white/10" />
                    <Input data-testid="content-duration-input" type="number" placeholder="Duration (sec)" value={newContent.duration} onChange={(e) => setNewContent({ ...newContent, duration: Number(e.target.value) })} required className="bg-white/5 border-white/10" />
                    <Button data-testid="upload-content-btn" type="submit" disabled={loading} className="w-full bg-cyan-400 text-[#05070F] hover:bg-cyan-300 font-semibold">{loading ? 'Uploading…' : 'Upload'}</Button>
                    <Button data-testid="load-sample-data-btn" type="button" onClick={handleSample} disabled={loading} className="w-full bg-fuchsia-500 hover:bg-fuchsia-600">Load Sample Data</Button>
                  </form>
                </div>
                <div className="glass-panel rounded-xl p-6">
                  <h3 className="text-xl font-bold mb-4">Library ({content.length})</h3>
                  <div className="space-y-2 max-h-[500px] overflow-y-auto">
                    {content.map((c) => (
                      <div key={c.id} data-testid={`admin-content-${c.id}`} className="bg-white/5 rounded p-3 flex items-center gap-3">
                        <img src={c.thumbnail_url} alt="" className="w-20 h-12 object-cover rounded" onError={(e) => e.target.style.display = 'none'} />
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold truncate">{c.title}</div>
                          <div className="text-xs text-gray-400">{c.type} · {c.views} views</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* PROMOS */}
            <TabsContent value="promos">
              <div className="grid lg:grid-cols-2 gap-6">
                <div className="glass-panel rounded-xl p-6">
                  <h3 className="text-xl font-bold mb-4 flex items-center"><Megaphone className="w-5 h-5 mr-2 text-fuchsia-400" />Self-Promotion Engine</h3>
                  <p className="text-gray-400 text-sm mb-4">Promos are injected into the Browse feed to establish View/Clip brand identity.</p>
                  <form onSubmit={handlePromoSubmit} className="space-y-3">
                    <Input data-testid="promo-title-input" placeholder="Promo Title" value={newPromo.title} onChange={(e) => setNewPromo({ ...newPromo, title: e.target.value })} required className="bg-white/5 border-white/10" />
                    <Textarea data-testid="promo-description-input" placeholder="Description" value={newPromo.description} onChange={(e) => setNewPromo({ ...newPromo, description: e.target.value })} required className="bg-white/5 border-white/10" />
                    <Input data-testid="promo-thumbnail-input" placeholder="Thumbnail URL" value={newPromo.thumbnail_url} onChange={(e) => setNewPromo({ ...newPromo, thumbnail_url: e.target.value })} required className="bg-white/5 border-white/10" />
                    <Input data-testid="promo-video-input" placeholder="Video URL" value={newPromo.video_url} onChange={(e) => setNewPromo({ ...newPromo, video_url: e.target.value })} required className="bg-white/5 border-white/10" />
                    <Button data-testid="create-promo-btn" type="submit" className="w-full bg-fuchsia-500 hover:bg-fuchsia-600">Create Promo</Button>
                  </form>
                </div>
                <div className="glass-panel rounded-xl p-6">
                  <h3 className="text-xl font-bold mb-4">Active Promos ({promos.length})</h3>
                  <div className="space-y-2">
                    {promos.map((p) => (
                      <div key={p.id} data-testid={`promo-${p.id}`} className="bg-white/5 rounded p-3 flex items-center gap-3">
                        <img src={p.thumbnail_url} alt="" className="w-20 h-12 object-cover rounded" onError={(e) => e.target.style.display = 'none'} />
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold truncate">{p.title}</div>
                          <div className="text-xs text-gray-400 truncate">{p.description}</div>
                        </div>
                        <Button data-testid={`delete-promo-${p.id}`} onClick={() => deletePromo(p.id)} size="sm" className="bg-red-500/20 hover:bg-red-500/40 text-red-300"><Trash2 className="w-3 h-3" /></Button>
                      </div>
                    ))}
                    {promos.length === 0 && <p className="text-gray-500 text-sm">No promos yet</p>}
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* USERS */}
            <TabsContent value="users">
              <div className="glass-panel rounded-xl p-6">
                <h3 className="text-xl font-bold mb-4">Users ({users.length})</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-white/5"><tr><th className="text-left p-3">Name</th><th className="text-left p-3">Email</th><th className="text-left p-3">Role</th><th className="text-left p-3">Sub</th><th className="text-left p-3">Joined</th></tr></thead>
                    <tbody>
                      {users.map((u) => (
                        <tr key={u.id} data-testid={`admin-user-${u.id}`} className="border-t border-white/5">
                          <td className="p-3">{u.name}</td><td className="p-3 text-gray-400">{u.email}</td>
                          <td className="p-3"><span className="capitalize bg-white/5 px-2 py-1 rounded text-xs">{u.role}</span></td>
                          <td className="p-3">{u.subscription_status === 'active' ? <span className="text-green-400">active</span> : <span className="text-gray-500">inactive</span>}</td>
                          <td className="p-3 text-gray-400">{new Date(u.created_at).toLocaleDateString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </TabsContent>

            {/* PAYOUTS */}
            <TabsContent value="payouts">
              <div className="glass-panel rounded-xl p-6 mb-6 flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-bold mb-1">Streamer Payouts</h3>
                  <p className="text-gray-400 text-sm">Batch-process earnings to Connect accounts.</p>
                </div>
                <Button data-testid="trigger-payouts-btn" onClick={triggerPayouts} className="bg-green-500 hover:bg-green-600">Process Payouts</Button>
              </div>
              <div className="glass-panel rounded-xl p-6">
                <h3 className="text-lg font-bold mb-4">Payout History ({payouts.length})</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-white/5"><tr><th className="text-left p-3">Date</th><th className="text-left p-3">Streamer ID</th><th className="text-right p-3">Earnings Count</th><th className="text-right p-3">Amount</th><th className="text-left p-3">Status</th></tr></thead>
                    <tbody>
                      {payouts.map((p) => (
                        <tr key={p.id} data-testid={`payout-${p.id}`} className="border-t border-white/5">
                          <td className="p-3 text-gray-400">{new Date(p.processed_at).toLocaleString()}</td>
                          <td className="p-3 text-xs font-mono text-gray-400">{p.streamer_id.slice(0, 8)}…</td>
                          <td className="p-3 text-right">{p.earnings_count}</td>
                          <td className="p-3 text-right text-green-400 font-semibold">${p.amount.toFixed(3)}</td>
                          <td className="p-3"><span className="text-xs bg-green-500/20 text-green-300 px-2 py-1 rounded">{p.status}</span></td>
                        </tr>
                      ))}
                      {payouts.length === 0 && <tr><td colSpan="5" className="p-8 text-center text-gray-500">No payouts processed yet.</td></tr>}
                    </tbody>
                  </table>
                </div>
              </div>
            </TabsContent>

            {/* SYSTEM — L3 firewall, 3-DB health, hot-swap providers, deploy */}
            <TabsContent value="system">
              <SystemPanel />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ label, value, sub, icon, color }) => {
  const colors = {
    cyan: 'text-cyan-400 bg-cyan-400/10',
    green: 'text-green-400 bg-green-400/10',
    red: 'text-red-400 bg-red-400/10',
    fuchsia: 'text-fuchsia-400 bg-fuchsia-400/10',
  };
  return (
    <div className="glass-panel rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <div className={`${colors[color]} p-2 rounded-lg`}>{icon}</div>
      </div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-gray-400 text-sm">{label}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  );
};

const SettingRow = ({ label, children, testid }) => (
  <div data-testid={testid} className="mb-3">
    <Label className="text-sm text-gray-300">{label}</Label>
    <div className="mt-1">{children}</div>
  </div>
);

const SystemPanel = () => {
  const [health, setHealth] = useState(null);
  const [providers, setProviders] = useState(null);
  const [events, setEvents] = useState([]);
  const [audit, setAudit] = useState([]);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    try {
      const [h, p, e, a] = await Promise.all([
        axios.get(`${API}/admin/system/health`),
        axios.get(`${API}/admin/streaming/providers`),
        axios.get(`${API}/admin/system/events`),
        axios.get(`${API}/admin/audit`),
      ]);
      setHealth(h.data);
      setProviders(p.data);
      setEvents(e.data.events || []);
      setAudit(a.data.audit || []);
    } catch (err) { /* noop */ }
  };

  useEffect(() => {
    refresh();
    const iv = setInterval(refresh, 15000);
    return () => clearInterval(iv);
  }, []);

  const action = async (label, url) => {
    setBusy(true);
    try {
      const r = await axios.post(url);
      toast.success(r.data.message || label);
      refresh();
    } catch (e) { toast.error('Action failed'); }
    setBusy(false);
  };

  const switchProvider = async (id) => {
    try {
      const r = await axios.post(`${API}/admin/streaming/providers/switch`, { provider_id: id });
      toast.success(r.data.message);
      refresh();
    } catch (e) { toast.error('Switch failed'); }
  };

  return (
    <div className="space-y-6">
      {/* 1. THE BURN MONITOR */}
      {health && health.integrations?.gcp_burn_stats && (
        <div className="grid grid-cols-1 gap-6">
           <BurnRateMonitor gcp_burn_stats={health.integrations.gcp_burn_stats} />
        </div>
      )}

      {/* Health grid */}
      {health && (
        <div data-testid="system-health" className="grid lg:grid-cols-2 gap-6">
          <div className="glass-panel rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold flex items-center"><Shield className="w-5 h-5 mr-2 text-green-400" />System Health</h3>
              <span className="text-xs text-gray-500">v{health.version} · {health.uptime_human}</span>
            </div>
            <div className="space-y-2">
              {health.layers.map((l) => (
                <div key={l.layer} data-testid={`layer-${l.layer}`} className="flex items-center justify-between bg-white/5 rounded px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${l.status === 'ok' ? 'bg-green-400' : 'bg-red-400'}`}></span>
                    <span className="capitalize">{l.layer} DB</span>
                  </div>
                  <span className="text-xs text-gray-400">{l.latency_ms ?? '-'} ms</span>
                </div>
              ))}
            </div>
          </div>
          <div className="glass-panel rounded-xl p-6">
            <h3 className="text-lg font-bold mb-3">Encryption</h3>
            <div className="bg-white/5 rounded p-3 text-sm">
              <div className="text-xs text-gray-400 mb-1">Algorithm</div>
              <div className="font-mono text-green-400 mb-2">{health.encryption.algorithm}</div>
              <div className="text-xs text-gray-400 mb-1">Vault Key</div>
              <div className="font-mono text-xs">{health.encryption.vault_key_configured ? '✓ Loaded' : '✗ Missing'}</div>
            </div>
          </div>
        </div>
      )}

      {/* Streaming providers hot-swap */}
      {providers && (
        <div data-testid="streaming-providers" className="glass-panel rounded-xl p-6">
          <h3 className="text-lg font-bold mb-3">Cloud Streaming Provider (hot-swap)</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {providers.providers.map((p) => (
              <button key={p.id} onClick={() => switchProvider(p.id)}
                className={`rounded-xl p-4 text-left transition-all border-2 ${providers.current === p.id ? 'border-green-400 bg-green-400/10' : 'border-white/10 hover:border-cyan-400/40'}`}>
                <div className="font-semibold">{p.name}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* System actions */}
      <div data-testid="system-actions" className="glass-panel rounded-xl p-6">
        <h3 className="text-lg font-bold mb-4">System Actions</h3>
        <div className="grid md:grid-cols-3 gap-3">
          <Button disabled={busy} onClick={() => action('Reload', `${API}/admin/system/reload-settings`)} className="bg-cyan-400 text-[#05070F] py-6">Reload Settings</Button>
          <Button disabled={busy} onClick={() => action('Deploy', `${API}/admin/system/deploy-update`)} className="bg-fuchsia-500 py-6">Deploy Update</Button>
          <Button disabled={busy} onClick={() => action('Rotate', `${API}/admin/system/rotate-keys`)} className="bg-amber-500 text-[#05070F] py-6">Rotate Keys</Button>
        </div>

        {/* EMERGENCY KILL SWITCH */}
        <div className="mt-8 pt-8 border-t border-white/10">
          <EmergencyKillSwitch />
        </div>
      </div>

      {/* Events + Audit */}
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="glass-panel rounded-xl p-6">
          <h3 className="text-lg font-bold mb-3">System Events</h3>
          <div className="space-y-1 max-h-80 overflow-y-auto">
            {events.slice(0, 20).map((e) => (
              <div key={e.id} className="text-sm bg-white/5 rounded px-3 py-2">
                <div className="flex justify-between"><span className="font-mono text-cyan-400">{e.type}</span></div>
              </div>
            ))}
          </div>
        </div>
        <div className="glass-panel rounded-xl p-6">
          <h3 className="text-lg font-bold mb-3">Audit Log</h3>
          <div className="space-y-1 max-h-80 overflow-y-auto">
            {audit.map((a) => (
              <div key={a.id} className="text-sm bg-white/5 rounded px-3 py-2">{a.action}</div>
            ))}
          </div>
        </div>
      </div>

      <TwoFactorCard />
    </div>
  );
};

const TwoFactorCard = () => {
  const [status, setStatus] = useState(null);
  const [setupData, setSetupData] = useState(null);
  const [code, setCode] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState(null);

  const refresh = async () => {
    try { const r = await axios.get(`${API}/admin/auth/2fa/status`); setStatus(r.data); }
    catch (e) { /* noop */ }
  };
  useEffect(() => { refresh(); }, []);

  const startSetup = async () => {
    try { const r = await axios.post(`${API}/admin/auth/2fa/setup`); setSetupData(r.data); }
    catch (e) { toast.error('Setup failed'); }
  };

  const enable = async () => {
    try {
      const r = await axios.post(`${API}/admin/auth/2fa/enable`, { code });
      toast.success('2FA enabled');
      setRecoveryCodes(r.data.recovery_codes || []);
      setSetupData(null);
      refresh();
    } catch (e) { toast.error('Invalid code'); }
  };

  if (!status) return null;

  if (recoveryCodes) {
    return (
      <div className="glass-panel rounded-xl p-6 border border-amber-500/40">
        <h3 className="text-lg font-bold mb-2 text-amber-300">Save recovery codes</h3>
        <div className="grid grid-cols-2 gap-2 font-mono text-sm bg-black/40 p-4">
          {recoveryCodes.map((c, i) => <div key={i}>{c}</div>)}
        </div>
        <Button onClick={() => setRecoveryCodes(null)} className="mt-4 bg-green-500">Saved them</Button>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-xl p-6 border border-fuchsia-500/20">
      <h3 className="text-lg font-bold mb-2 flex items-center gap-2">
        <Shield className="w-5 h-5 text-fuchsia-400" />
        Two-Factor Authentication
      </h3>
      {status.enabled ? (
        <div className="text-green-400">✓ 2FA is active</div>
      ) : setupData ? (
        <div className="space-y-4">
          <img src={setupData.qr_code_png_base64} alt="QR" className="w-32 h-32 bg-white p-2" />
          <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="000000" />
          <Button onClick={enable} className="bg-green-500">Confirm Enable</Button>
        </div>
      ) : (
        <Button onClick={startSetup} className="bg-fuchsia-500">Set up 2FA</Button>
      )}
    </div>
  );
};

export default AdminDashboard;
