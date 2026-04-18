import { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Radio, DollarSign, Eye, Gift, LogOut, User as UserIcon, Home, Save, Upload, Youtube, Twitch, BarChart3, Users2, Heart } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Logo from '@/components/Logo';
import NotificationBell from '@/components/NotificationBell';
import axios from 'axios';
import { toast } from 'sonner';

const StreamerDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  const [myStreams, setMyStreams] = useState([]);
  const [earnings, setEarnings] = useState([]);
  const [totalEarnings, setTotalEarnings] = useState(0);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [exportStream, setExportStream] = useState(null); // stream object for export modal
  const [newStream, setNewStream] = useState({ title: '', description: '', video_url: '', thumbnail_url: '' });

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [streamsRes, earningsRes, totalRes, analyticsRes] = await Promise.all([
        axios.get(`${API}/streams`),
        axios.get(`${API}/earnings`),
        axios.get(`${API}/earnings/total`),
        axios.get(`${API}/streamers/me/analytics`),
      ]);
      setMyStreams(streamsRes.data.filter((s) => s.streamer_id === user.id));
      setEarnings(earningsRes.data);
      setTotalEarnings(totalRes.data.total_earnings);
      setAnalytics(analyticsRes.data);
    } catch (e) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateStream = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/streams`, newStream);
      toast.success('Stream created — go live!');
      setIsDialogOpen(false);
      setNewStream({ title: '', description: '', video_url: '', thumbnail_url: '' });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create stream');
    }
  };

  const handleEndStream = async (streamId) => {
    try {
      const r = await axios.post(`${API}/streams/${streamId}/end`);
      toast.success(`Stream ended. Earned $${r.data.earnings.toFixed(3)} (${r.data.qualified_views} qualified views)`);
      fetchData();
    } catch (e) {
      toast.error('Failed to end stream');
    }
  };

  const handleSaveStream = async (streamId) => {
    try {
      await axios.post(`${API}/streams/${streamId}/save`);
      toast.success('Stream saved — ready to export');
      fetchData();
    } catch (e) {
      toast.error('Failed to save stream');
    }
  };

  const handleExport = async (platform) => {
    try {
      const r = await axios.post(`${API}/streams/${exportStream.id}/export`, { platform });
      toast.success(`Exported to ${platform.toUpperCase()}: ${r.data.export.target_url}`);
      setExportStream(null);
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Export failed');
    }
  };

  if (loading) return <div className="flex items-center justify-center min-h-screen bg-[#05070F]"><div className="spinner"></div></div>;

  return (
    <div className="min-h-screen bg-[#05070F] text-white">
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Logo size="md" />
          <div className="flex items-center space-x-4">
            <Button data-testid="browse-nav-btn" onClick={() => navigate('/browse')} variant="ghost" className="text-white hover:text-cyan-400"><Home className="w-4 h-4 mr-2" />Browse</Button>
            <Button data-testid="live-nav-btn" onClick={() => navigate('/live')} variant="ghost" className="text-white hover:text-cyan-400"><Radio className="w-4 h-4 mr-2" />Live</Button>
            <Button data-testid="dashboard-nav-btn" onClick={() => navigate('/streamer')} variant="ghost" className="text-cyan-400">Dashboard</Button>
            <NotificationBell />
            <Button data-testid="profile-nav-btn" onClick={() => navigate('/profile')} variant="ghost" className="text-white hover:text-cyan-400"><UserIcon className="w-4 h-4 mr-2" />Profile</Button>
            <Button data-testid="logout-nav-btn" onClick={logout} variant="ghost" className="text-white hover:text-red-400"><LogOut className="w-4 h-4" /></Button>
          </div>
        </div>
      </nav>

      <div className="pt-24 px-6 pb-12">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-4xl font-bold mb-2">Streamer Dashboard</h1>
              <p className="text-gray-400">Manage your streams, earnings, exports.</p>
              {user?.connect_account_status !== 'active' && (
                <p className="text-yellow-400 text-sm mt-2">⚠ Connect a payout account in Profile to receive earnings.</p>
              )}
            </div>
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button data-testid="start-stream-btn" className="bg-gradient-to-r from-cyan-400 to-fuchsia-500 hover:opacity-90 px-8 py-6 text-lg rounded-xl text-[#05070F] font-semibold">
                  <Radio className="w-5 h-5 mr-2" />Start Stream
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-[#0A0E27] border-white/10 text-white">
                <DialogHeader><DialogTitle className="text-2xl">Create New Stream</DialogTitle></DialogHeader>
                <form onSubmit={handleCreateStream} className="space-y-4 mt-4">
                  <div>
                    <Label htmlFor="title">Title</Label>
                    <Input data-testid="stream-title-input" id="title" value={newStream.title} onChange={(e) => setNewStream({ ...newStream, title: e.target.value })} required className="bg-white/5 border-white/10 text-white mt-2" />
                  </div>
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Textarea data-testid="stream-description-input" id="description" value={newStream.description} onChange={(e) => setNewStream({ ...newStream, description: e.target.value })} required className="bg-white/5 border-white/10 text-white mt-2" rows={3} />
                  </div>
                  <div>
                    <Label htmlFor="video-url">Video URL</Label>
                    <Input data-testid="stream-video-input" id="video-url" value={newStream.video_url} onChange={(e) => setNewStream({ ...newStream, video_url: e.target.value })} required className="bg-white/5 border-white/10 text-white mt-2" />
                  </div>
                  <div>
                    <Label htmlFor="thumbnail-url">Thumbnail URL</Label>
                    <Input data-testid="stream-thumbnail-input" id="thumbnail-url" value={newStream.thumbnail_url} onChange={(e) => setNewStream({ ...newStream, thumbnail_url: e.target.value })} required className="bg-white/5 border-white/10 text-white mt-2" />
                  </div>
                  <Button data-testid="create-stream-submit-btn" type="submit" className="w-full bg-cyan-400 text-[#05070F] hover:bg-cyan-300 py-6 rounded-xl font-semibold">Go Live</Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          {/* Stats */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <div data-testid="total-earnings-card" className="glass-panel rounded-xl p-6">
              <div className="flex items-center justify-between mb-4"><DollarSign className="w-10 h-10 text-green-400" /><span className="bg-green-400/20 px-3 py-1 rounded-full text-green-400 text-sm font-semibold">Earnings</span></div>
              <h3 className="text-3xl font-bold mb-1">${totalEarnings.toFixed(3)}</h3>
              <p className="text-gray-400 text-sm">Total Earnings</p>
            </div>
            <div data-testid="total-streams-card" className="glass-panel rounded-xl p-6">
              <div className="flex items-center justify-between mb-4"><Radio className="w-10 h-10 text-fuchsia-400" /><span className="bg-fuchsia-400/20 px-3 py-1 rounded-full text-fuchsia-400 text-sm font-semibold">Streams</span></div>
              <h3 className="text-3xl font-bold mb-1">{myStreams.length}</h3>
              <p className="text-gray-400 text-sm">Total Streams</p>
            </div>
            <div data-testid="total-views-card" className="glass-panel rounded-xl p-6">
              <div className="flex items-center justify-between mb-4"><Eye className="w-10 h-10 text-cyan-400" /><span className="bg-cyan-400/20 px-3 py-1 rounded-full text-cyan-400 text-sm font-semibold">Views</span></div>
              <h3 className="text-3xl font-bold mb-1">{myStreams.reduce((s, x) => s + x.views, 0).toLocaleString()}</h3>
              <p className="text-gray-400 text-sm">{myStreams.reduce((s, x) => s + (x.qualified_views || 0), 0).toLocaleString()} qualified</p>
            </div>
          </div>

          {/* Analytics */}
          {analytics && (
            <div data-testid="analytics-section" className="mb-8">
              <div className="flex items-center gap-3 mb-6">
                <BarChart3 className="w-6 h-6 text-fuchsia-400" />
                <h2 className="text-2xl font-bold">Analytics</h2>
                <span className="text-sm text-gray-500">Last 30 days</span>
              </div>
              <div className="grid lg:grid-cols-3 gap-6">
                <div data-testid="analytics-followers" className="glass-panel rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-3"><Heart className="w-5 h-5 text-fuchsia-400" /><span className="text-sm text-gray-400">Followers</span></div>
                  <div className="text-3xl font-bold">{analytics.followers}</div>
                </div>
                <div data-testid="analytics-earnings-views" className="glass-panel rounded-xl p-5">
                  <div className="text-sm text-gray-400 mb-3">Views earnings</div>
                  <div className="text-3xl font-bold text-cyan-400">${(analytics.by_source?.views?.total || 0).toFixed(3)}</div>
                  <div className="text-xs text-gray-500 mt-1">{analytics.by_source?.views?.count || 0} stream ends</div>
                </div>
                <div data-testid="analytics-earnings-gifts" className="glass-panel rounded-xl p-5">
                  <div className="text-sm text-gray-400 mb-3">Gift earnings</div>
                  <div className="text-3xl font-bold text-fuchsia-400">${(analytics.by_source?.gifts?.total || 0).toFixed(3)}</div>
                  <div className="text-xs text-gray-500 mt-1">{analytics.by_source?.gifts?.count || 0} gifts</div>
                </div>
              </div>

              <div className="grid lg:grid-cols-2 gap-6 mt-6">
                <div data-testid="analytics-top-gifters" className="glass-panel rounded-xl p-6">
                  <h3 className="text-lg font-bold mb-4 flex items-center gap-2"><Users2 className="w-5 h-5 text-cyan-400" />Top Gifters</h3>
                  {analytics.top_gifters.length === 0 ? (
                    <p className="text-gray-500 text-sm">No gifts received yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {analytics.top_gifters.map((g, i) => (
                        <div key={g.sender_id} data-testid={`top-gifter-${i}`} className="flex justify-between items-center bg-white/5 rounded px-3 py-2">
                          <div className="flex items-center gap-3">
                            <span className="text-gray-500 text-sm w-6">#{i + 1}</span>
                            <span className="font-semibold">{g.name}</span>
                          </div>
                          <div className="text-right">
                            <div className="text-fuchsia-400 font-bold">${g.total_value.toFixed(3)}</div>
                            <div className="text-xs text-gray-500">{g.count} gifts</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div data-testid="analytics-gift-tiers" className="glass-panel rounded-xl p-6">
                  <h3 className="text-lg font-bold mb-4 flex items-center gap-2"><Gift className="w-5 h-5 text-fuchsia-400" />Gift Tier Breakdown</h3>
                  {analytics.gift_tiers.length === 0 ? (
                    <p className="text-gray-500 text-sm">No gifts received yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {analytics.gift_tiers.map((t) => (
                        <div key={t.tier_id} data-testid={`tier-row-${t.tier_id}`} className="flex justify-between items-center bg-white/5 rounded px-3 py-2">
                          <div className="flex items-center gap-3">
                            <span className="text-2xl">{t.emoji}</span>
                            <div>
                              <div className="font-semibold">{t.name}</div>
                              <div className="text-xs text-gray-500">{t.count} units</div>
                            </div>
                          </div>
                          <div className="text-fuchsia-400 font-bold">${t.value.toFixed(3)}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {analytics.time_series.length > 0 && (
                <div data-testid="analytics-timeseries" className="glass-panel rounded-xl p-6 mt-6">
                  <h3 className="text-lg font-bold mb-4">Earnings (daily)</h3>
                  <div className="flex items-end gap-1 h-40">
                    {analytics.time_series.map((pt) => {
                      const max = Math.max(...analytics.time_series.map((p) => p.amount)) || 1;
                      const height = Math.max(4, (pt.amount / max) * 100);
                      return (
                        <div key={pt.date} className="flex-1 group relative flex flex-col items-center">
                          <div className="w-full bg-gradient-to-t from-cyan-500 to-fuchsia-500 rounded-t" style={{ height: `${height}%` }}></div>
                          <div className="absolute -top-8 opacity-0 group-hover:opacity-100 text-xs bg-black px-2 py-1 rounded whitespace-nowrap">
                            {pt.date}: ${pt.amount.toFixed(3)}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Streams */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold mb-6">My Streams</h2>
            {myStreams.length === 0 ? (
              <div data-testid="no-streams-message" className="glass-panel rounded-xl p-12 text-center">
                <Radio className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400 text-lg mb-4">You haven't created any streams yet</p>
                <Button onClick={() => setIsDialogOpen(true)} className="bg-cyan-400 text-[#05070F] hover:bg-cyan-300">Start Your First Stream</Button>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {myStreams.map((stream) => (
                  <div key={stream.id} data-testid={`my-stream-${stream.id}`} className="glass-panel rounded-xl overflow-hidden">
                    <div className="relative aspect-video bg-gradient-to-br from-purple-500/20 to-pink-500/20">
                      <img src={stream.thumbnail_url} alt={stream.title} className="w-full h-full object-cover" onError={(e) => { e.target.style.display = 'none'; }} />
                      {stream.is_live && <div className="absolute top-2 left-2 bg-red-500 text-white px-3 py-1 rounded-full text-xs font-semibold flex items-center live-pulse"><span className="w-2 h-2 bg-white rounded-full mr-2 animate-pulse"></span>LIVE</div>}
                      {stream.saved && <div className="absolute top-2 right-2 bg-green-500 text-white px-2 py-1 rounded-full text-xs font-semibold flex items-center"><Save className="w-3 h-3 mr-1" />SAVED</div>}
                    </div>
                    <div className="p-4">
                      <h3 className="font-semibold text-lg mb-2 line-clamp-1">{stream.title}</h3>
                      <div className="flex items-center justify-between text-sm text-gray-400 mb-4">
                        <div className="flex items-center"><Eye className="w-4 h-4 mr-1" />{stream.views} views</div>
                        {stream.is_live && <div>{stream.viewers_count} watching</div>}
                      </div>
                      {stream.is_live && stream.ingest_url && (
                        <div className="bg-black/40 border border-green-500/30 rounded p-2 mb-2 text-xs">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-green-400 font-semibold uppercase">RTMP Ingest</span>
                            <span className="text-[10px] text-gray-500 uppercase">{stream.live_mode || 'mock'}</span>
                          </div>
                          <div className="font-mono text-gray-300 break-all">{stream.ingest_url}</div>
                          {stream.stream_key && <div className="mt-1 text-gray-400">key: <span className="font-mono">{stream.stream_key}</span></div>}
                        </div>
                      )}
                      {stream.exports && stream.exports.length > 0 && (
                        <div className="text-xs text-gray-500 mb-2">Exported to: {stream.exports.map((x) => x.platform).join(', ')}</div>
                      )}
                      <div className="flex flex-wrap gap-2">
                        {stream.is_live && (
                          <Button data-testid={`end-stream-btn-${stream.id}`} onClick={() => handleEndStream(stream.id)} className="flex-1 bg-red-500 hover:bg-red-600 text-white rounded-lg">End</Button>
                        )}
                        {!stream.is_live && !stream.saved && (
                          <Button data-testid={`save-stream-btn-${stream.id}`} onClick={() => handleSaveStream(stream.id)} className="flex-1 bg-fuchsia-500 hover:bg-fuchsia-600 text-white rounded-lg"><Save className="w-4 h-4 mr-1" />Save</Button>
                        )}
                        {!stream.is_live && stream.saved && (
                          <Button data-testid={`export-stream-btn-${stream.id}`} onClick={() => setExportStream(stream)} className="flex-1 bg-green-500 hover:bg-green-600 text-white rounded-lg"><Upload className="w-4 h-4 mr-1" />Export</Button>
                        )}
                        <Button data-testid={`view-stream-btn-${stream.id}`} onClick={() => navigate(`/stream/${stream.id}`)} className="flex-1 bg-cyan-400 text-[#05070F] hover:bg-cyan-300 rounded-lg">View</Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Earnings table */}
          <div>
            <h2 className="text-2xl font-bold mb-6">Recent Earnings</h2>
            {earnings.length === 0 ? (
              <div data-testid="no-earnings-message" className="glass-panel rounded-xl p-8 text-center">
                <DollarSign className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400">No earnings yet.</p>
              </div>
            ) : (
              <div className="glass-panel rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-white/5">
                      <tr>
                        <th className="text-left p-4">Date</th>
                        <th className="text-left p-4">Source</th>
                        <th className="text-left p-4">Description</th>
                        <th className="text-right p-4">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {earnings.slice(0, 15).map((e) => (
                        <tr key={e.id} data-testid={`earning-${e.id}`} className="border-t border-white/5 hover:bg-white/5">
                          <td className="p-4 text-sm text-gray-400">{new Date(e.created_at).toLocaleDateString()}</td>
                          <td className="p-4"><div className="flex items-center">{e.source === 'views' ? <Eye className="w-4 h-4 mr-2 text-cyan-400" /> : <Gift className="w-4 h-4 mr-2 text-fuchsia-400" />}<span className="capitalize">{e.source}</span></div></td>
                          <td className="p-4 text-sm text-gray-400">{e.description}</td>
                          <td className="p-4 text-right font-semibold text-green-400">+${e.amount.toFixed(3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Export Modal */}
      <Dialog open={!!exportStream} onOpenChange={(o) => !o && setExportStream(null)}>
        <DialogContent className="bg-[#0A0E27] border-white/10 text-white">
          <DialogHeader><DialogTitle className="text-2xl">Export Stream</DialogTitle></DialogHeader>
          <p className="text-gray-400 mb-4">Distribute "{exportStream?.title}" to other platforms.</p>
          <div className="grid grid-cols-2 gap-3">
            <Button data-testid="export-youtube-btn" onClick={() => handleExport('youtube')} className="bg-red-600 hover:bg-red-700 py-6"><Youtube className="w-5 h-5 mr-2" />YouTube</Button>
            <Button data-testid="export-twitch-btn" onClick={() => handleExport('twitch')} className="bg-purple-600 hover:bg-purple-700 py-6"><Twitch className="w-5 h-5 mr-2" />Twitch</Button>
            <Button data-testid="export-x-btn" onClick={() => handleExport('x')} className="bg-black hover:bg-zinc-800 py-6 border border-white/20">𝕏 Post</Button>
            <Button data-testid="export-custom-btn" onClick={() => handleExport('custom')} className="bg-white/10 hover:bg-white/20 py-6"><Upload className="w-5 h-5 mr-2" />Custom URL</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default StreamerDashboard;
