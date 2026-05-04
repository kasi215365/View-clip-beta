import { useState, useEffect, useContext, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Radio, DollarSign, Eye, Gift, LogOut, User as UserIcon, Home, Save, Upload, Youtube, Twitch, BarChart3, Users2, Heart, Link2 as LinkIcon } from 'lucide-react';
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
  const [exportStream, setExportStream] = useState(null); 
  const [exportVideoUrl, setExportVideoUrl] = useState(''); 
  const [oauth, setOauth] = useState({ connections: [], available_providers: [] });
  const [newStream, setNewStream] = useState({ title: '', description: '', video_url: '', thumbnail_url: '' });

  // --- Hybrid Streaming State ---
  const [isDirectMode, setIsDirectMode] = useState(true);
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const peerConnection = useRef(null);
  const videoRef = useRef(null);

  useEffect(() => { fetchData(); }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const provider = params.get('oauth');
    const status = params.get('status');
    if (provider && status) {
      if (status === 'connected') toast.success(`${provider.toUpperCase()} connected`);
      else toast.error(`${provider.toUpperCase()} link failed: ${params.get('msg') || status}`);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  const fetchData = async () => {
    try {
      const [streamsRes, earningsRes, totalRes, analyticsRes, oauthRes] = await Promise.all([
        axios.get(`${API}/streams`),
        axios.get(`${API}/earnings`),
        axios.get(`${API}/earnings/total`),
        axios.get(`${API}/streamers/me/analytics`),
        axios.get(`${API}/oauth/connections`).catch(() => ({ data: { connections: [], available_providers: [] } })),
      ]);
      setMyStreams(streamsRes.data.filter((s) => s.streamer_id === user.id));
      setEarnings(earningsRes.data);
      setTotalEarnings(totalRes.data.total_earnings);
      setAnalytics(analyticsRes.data);
      setOauth(oauthRes.data);
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
      setIsBroadcasting(false); // Reset broadcasting state
      if (peerConnection.current) peerConnection.current.close();
      fetchData();
    } catch (e) {
      toast.error('Failed to end stream');
    }
  };

  // --- Direct Broadcast Logic (WHIP) ---
  const startDirectBroadcast = async (inputId) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      if (videoRef.current) videoRef.current.srcObject = stream;
      
      peerConnection.current = new RTCPeerConnection();
      stream.getTracks().forEach(track => peerConnection.current.addTrack(track, stream));

      const offer = await peerConnection.current.createOffer();
      await peerConnection.current.setLocalDescription(offer);

      const response = await fetch(`https://customer-9j4l1hq89yi1muyd.cloudflarestream.com/${inputId}/whip`, {
        method: 'POST',
        body: offer.sdp,
        headers: { 'Content-Type': 'application/sdp' }
      });

      if (!response.ok) throw new Error("Cloudflare WHIP handoff failed");

      const answerSdp = await response.text();
      await peerConnection.current.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: answerSdp }));
      setIsBroadcasting(true);
      toast.success("Live broadcast started from your camera!");
    } catch (err) {
      console.error(err);
      toast.error("Could not start camera broadcast. Check permissions.");
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
      const payload = { platform };
      if (platform === 'youtube' && exportVideoUrl.trim()) {
        payload.target_url = exportVideoUrl.trim();
      }
      const r = await axios.post(`${API}/streams/${exportStream.id}/export`, payload);
      const exp = r.data.export || {};
      let status = '';
      if (exp.uploaded) status = ' — video uploaded 🎬';
      else if (exp.mock) status = ' (mock — connect account to publish for real)';
      toast.success(`Exported to ${platform.toUpperCase()}: ${exp.target_url}${status}`);
      setExportStream(null);
      setExportVideoUrl('');
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Export failed');
    }
  };

  const handleConnectOAuth = async (provider) => {
    try {
      const r = await axios.post(`${API}/oauth/${provider}/start`);
      if (r.data.mock) {
        toast.error(r.data.message || `${provider} not configured`);
        return;
      }
      window.location.href = r.data.authorization_url;
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to start OAuth flow');
    }
  };

  const handleDisconnectOAuth = async (provider) => {
    if (!window.confirm(`Disconnect ${provider.toUpperCase()}?`)) return;
    try {
      await axios.post(`${API}/oauth/${provider}/disconnect`);
      toast.success(`${provider.toUpperCase()} disconnected`);
      fetchData();
    } catch (e) {
      toast.error('Failed to disconnect');
    }
  };

  const oauthStatus = (provider) => {
    const conn = (oauth.connections || []).find((c) => c.provider === provider);
    const avail = (oauth.available_providers || []).find((p) => p.id === provider);
    return { connected: !!conn, displayName: conn?.display_name, configured: avail?.configured };
  };

  if (loading) return <div className="flex items-center justify-center min-h-screen bg-[#05070F]"><div className="spinner"></div></div>;

  return (
    <div className="min-h-screen bg-[#05070F] text-white">
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Logo size="md" />
          <div className="flex items-center space-x-4">
            <Button onClick={() => navigate('/browse')} variant="ghost" className="text-white hover:text-cyan-400"><Home className="w-4 h-4 mr-2" />Browse</Button>
            <Button onClick={() => navigate('/live')} variant="ghost" className="text-white hover:text-cyan-400"><Radio className="w-4 h-4 mr-2" />Live</Button>
            <Button onClick={() => navigate('/streamer')} variant="ghost" className="text-cyan-400">Dashboard</Button>
            <NotificationBell />
            <Button onClick={() => navigate('/profile')} variant="ghost" className="text-white hover:text-cyan-400"><UserIcon className="w-4 h-4 mr-2" />Profile</Button>
            <Button onClick={logout} variant="ghost" className="text-white hover:text-red-400"><LogOut className="w-4 h-4" /></Button>
          </div>
        </div>
      </nav>

      <div className="pt-24 px-6 pb-12">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-4xl font-bold mb-2">Streamer Dashboard</h1>
              <p className="text-gray-400">Manage your streams, earnings, exports.</p>
            </div>
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button className="bg-gradient-to-r from-cyan-400 to-fuchsia-500 hover:opacity-90 px-8 py-6 text-lg rounded-xl text-[#05070F] font-semibold">
                  <Radio className="w-5 h-5 mr-2" />Start Stream
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-[#0A0E27] border-white/10 text-white">
                <DialogHeader><DialogTitle className="text-2xl">Create New Stream</DialogTitle></DialogHeader>
                <form onSubmit={handleCreateStream} className="space-y-4 mt-4">
                  <div>
                    <Label htmlFor="title">Title</Label>
                    <Input id="title" value={newStream.title} onChange={(e) => setNewStream({ ...newStream, title: e.target.value })} required className="bg-white/5 border-white/10 text-white mt-2" />
                  </div>
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Textarea id="description" value={newStream.description} onChange={(e) => setNewStream({ ...newStream, description: e.target.value })} required className="bg-white/5 border-white/10 text-white mt-2" rows={3} />
                  </div>
                  <div>
                    <Label htmlFor="thumbnail-url">Thumbnail URL</Label>
                    <Input id="thumbnail-url" value={newStream.thumbnail_url} onChange={(e) => setNewStream({ ...newStream, thumbnail_url: e.target.value })} required className="bg-white/5 border-white/10 text-white mt-2" />
                  </div>
                  <Button type="submit" className="w-full bg-cyan-400 text-[#05070F] hover:bg-cyan-300 py-6 rounded-xl font-semibold">Go Live</Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          {/* Stats Cards */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <div className="glass-panel rounded-xl p-6">
              <div className="flex items-center justify-between mb-4"><DollarSign className="w-10 h-10 text-green-400" /><span className="bg-green-400/20 px-3 py-1 rounded-full text-green-400 text-sm font-semibold">Earnings</span></div>
              <h3 className="text-3xl font-bold mb-1">${totalEarnings.toFixed(3)}</h3>
              <p className="text-gray-400 text-sm">Total Earnings</p>
            </div>
            <div className="glass-panel rounded-xl p-6">
              <div className="flex items-center justify-between mb-4"><Radio className="w-10 h-10 text-fuchsia-400" /><span className="bg-fuchsia-400/20 px-3 py-1 rounded-full text-fuchsia-400 text-sm font-semibold">Streams</span></div>
              <h3 className="text-3xl font-bold mb-1">{myStreams.length}</h3>
              <p className="text-gray-400 text-sm">Total Streams</p>
            </div>
            <div className="glass-panel rounded-xl p-6">
              <div className="flex items-center justify-between mb-4"><Eye className="w-10 h-10 text-cyan-400" /><span className="bg-cyan-400/20 px-3 py-1 rounded-full text-cyan-400 text-sm font-semibold">Views</span></div>
              <h3 className="text-3xl font-bold mb-1">{myStreams.reduce((s, x) => s + x.views, 0).toLocaleString()}</h3>
              <p className="text-gray-400 text-sm">Total Views</p>
            </div>
          </div>

          {/* Linked Accounts */}
          <div className="glass-panel rounded-xl p-6 mb-8 border border-fuchsia-500/20">
            <div className="flex items-center gap-3 mb-1">
              <LinkIcon className="w-5 h-5 text-fuchsia-400" />
              <h2 className="text-xl font-bold">Linked Export Accounts</h2>
            </div>
            <div className="grid md:grid-cols-2 gap-4 mt-4">
              {['youtube', 'twitch'].map((p) => {
                const s = oauthStatus(p);
                const Icon = p === 'youtube' ? Youtube : Twitch;
                return (
                  <div key={p} className="bg-black/30 border border-white/5 rounded-lg p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Icon className={`w-6 h-6 ${p === 'youtube' ? 'text-red-500' : 'text-purple-400'}`} />
                      <div>
                        <div className="font-semibold capitalize">{p}</div>
                        <div className="text-xs text-gray-400">{s.connected ? `Linked as ${s.displayName}` : 'Not linked'}</div>
                      </div>
                    </div>
                    <Button onClick={() => s.connected ? handleDisconnectOAuth(p) : handleConnectOAuth(p)} className={s.connected ? "bg-red-500/80" : "bg-fuchsia-500"}>
                      {s.connected ? 'Disconnect' : 'Connect'}
                    </Button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Streams List */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold mb-6">My Streams</h2>
            {myStreams.length === 0 ? (
              <div className="glass-panel rounded-xl p-12 text-center">
                <Radio className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400 text-lg mb-4">You haven't created any streams yet</p>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {myStreams.map((stream) => (
                  <div key={stream.id} className="glass-panel rounded-xl overflow-hidden">
                    <div className="relative aspect-video bg-black">
                      <img src={stream.thumbnail_url} alt={stream.title} className="w-full h-full object-cover" />
                      {stream.is_live && <div className="absolute top-2 left-2 bg-red-500 text-white px-3 py-1 rounded-full text-xs font-semibold animate-pulse">LIVE</div>}
                    </div>
                    <div className="p-4">
                      <h3 className="font-semibold text-lg mb-2">{stream.title}</h3>
                      
                      {/* --- MODIFIED INGEST BLOCK START --- */}
                      {stream.is_live && stream.ingest_url && (
                        <div className="bg-black/40 border border-cyan-500/30 rounded p-3 mb-4">
                          <div className="flex gap-2 mb-3 border-b border-white/10 pb-2">
                            <button 
                              onClick={() => setIsDirectMode(true)} 
                              className={`text-[10px] uppercase font-bold px-2 py-1 rounded transition-colors ${isDirectMode ? 'bg-cyan-400 text-black' : 'text-gray-400 hover:text-white'}`}
                            >
                              Direct Mode
                            </button>
                            <button 
                              onClick={() => setIsDirectMode(false)} 
                              className={`text-[10px] uppercase font-bold px-2 py-1 rounded transition-colors ${!isDirectMode ? 'bg-fuchsia-500 text-white' : 'text-gray-400 hover:text-white'}`}
                            >
                              Advanced (Encoder)
                            </button>
                          </div>

                          {isDirectMode ? (
                            <div className="space-y-2">
                              <video ref={videoRef} autoPlay muted playsInline className="w-full aspect-video bg-black rounded border border-white/10" />
                              {!isBroadcasting ? (
                                <Button 
                                  onClick={() => startDirectBroadcast(stream.input_id)} 
                                  className="w-full bg-cyan-400 text-black text-xs font-bold"
                                >
                                  Go Live with Camera
                                </Button>
                              ) : (
                                <div className="text-center text-[10px] text-green-400 font-bold py-2 bg-green-400/10 rounded">● BROADCASTING LIVE</div>
                              )}
                            </div>
                          ) : (
                            <div className="text-xs">
                              <div className="text-fuchsia-400 font-bold uppercase text-[9px] mb-1">RTMP URL</div>
                              <div className="font-mono text-gray-300 break-all bg-black/60 p-2 rounded mb-2 select-all">{stream.ingest_url}</div>
                              <div className="text-fuchsia-400 font-bold uppercase text-[9px] mb-1">Stream Key</div>
                              <div className="font-mono text-white break-all bg-black/60 p-2 rounded select-all">{stream.stream_key}</div>
                            </div>
                          )}
                        </div>
                      )}
                      {/* --- MODIFIED INGEST BLOCK END --- */}

                      <div className="flex gap-2">
                        {stream.is_live && <Button onClick={() => handleEndStream(stream.id)} className="flex-1 bg-red-500">End</Button>}
                        <Button onClick={() => navigate(`/stream/${stream.id}`)} className="flex-1 bg-cyan-400 text-black">View</Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StreamerDashboard;
