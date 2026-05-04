import { useState, useEffect, useContext, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Radio, DollarSign, Eye, Gift, LogOut, User as UserIcon, Home, Save, Upload, Youtube, Twitch, BarChart3, Users2, Heart, Link2 as LinkIcon, StopCircle, Camera } from 'lucide-react';
import Logo from '@/components/Logo';
import NotificationBell from '@/components/NotificationBell';
import axios from 'axios';
import { toast } from 'sonner';

const StreamerDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  
  // Data States
  const [myStreams, setMyStreams] = useState([]);
  const [earnings, setEarnings] = useState([]);
  const [totalEarnings, setTotalEarnings] = useState(0);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [oauth, setOauth] = useState({ connections: [], available_providers: [] });
  
  // UI States
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [exportStream, setExportStream] = useState(null);
  const [exportVideoUrl, setExportVideoUrl] = useState('');
  const [newStream, setNewStream] = useState({ title: '', description: '', thumbnail_url: '' });

  // --- Hybrid Streaming Logic ---
  const [isDirectMode, setIsDirectMode] = useState(true);
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const [localStreamActive, setLocalStreamActive] = useState(false);
  const peerConnection = useRef(null);
  const videoRef = useRef(null);

  const WHIP_URL = "https://customer-9j4l1hq89yi1muyd.cloudflarestream.com/6ef4e44200f89257909749dd7935badck340fafedcee8f68d1a4eac6518df78de/webRTC/publish";
  const RTMP_SERVER = "rtmps://live.cloudflare.com:443/live/";

  useEffect(() => { fetchData(); }, []);

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

  const startDirectBroadcast = async (streamId) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      setLocalStreamActive(true);
      if (videoRef.current) videoRef.current.srcObject = stream;
      
      peerConnection.current = new RTCPeerConnection();
      stream.getTracks().forEach(track => peerConnection.current.addTrack(track, stream));

      const offer = await peerConnection.current.createOffer();
      await peerConnection.current.setLocalDescription(offer);

      const response = await fetch(WHIP_URL, {
        method: 'POST',
        body: offer.sdp,
        headers: { 'Content-Type': 'application/sdp' }
      });

      if (!response.ok) throw new Error("Cloudflare Handshake Failed");
      const answerSdp = await response.text();
      await peerConnection.current.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: answerSdp }));
      
      setIsBroadcasting(true);
      toast.success("Connection Established!");
    } catch (err) {
      toast.error("Camera failed. Check permissions.");
    }
  };

  const handleEndStream = async (streamId) => {
    try {
      if (videoRef.current?.srcObject) {
        videoRef.current.srcObject.getTracks().forEach(track => track.stop());
        videoRef.current.srcObject = null;
      }
      peerConnection.current?.close();
      
      const r = await axios.post(`${API}/streams/${streamId}/end`);
      setIsBroadcasting(false);
      setLocalStreamActive(false);
      toast.success(`Stream ended. Earned $${r.data.earnings.toFixed(3)}`);
      fetchData();
    } catch (e) {
      toast.error('Failed to end stream');
    }
  };

  const handleCreateStream = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/streams`, { ...newStream, video_url: 'cloudflare_auto' });
      toast.success('Stream created');
      setIsDialogOpen(false);
      setNewStream({ title: '', description: '', thumbnail_url: '' });
      fetchData();
    } catch (error) {
      toast.error('Failed to create stream');
    }
  };

  // ... (Keep handleSaveStream, handleExport, handleConnectOAuth, oauthStatus from your original)

  if (loading) return <div className="min-h-screen bg-[#05070F] flex items-center justify-center"><div className="animate-spin rounded-full h-12 w-12 border-t-2 border-cyan-500"></div></div>;

  return (
    <div className="min-h-screen bg-[#05070F] text-white">
      {/* Navigation - Restored to Original */}
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Logo size="md" />
          <div className="flex items-center space-x-4">
            <Button onClick={() => navigate('/browse')} variant="ghost" className="text-white hover:text-cyan-400"><Home className="w-4 h-4 mr-2" />Browse</Button>
            <Button onClick={() => navigate('/live')} variant="ghost" className="text-white hover:text-cyan-400"><Radio className="w-4 h-4 mr-2" />Live</Button>
            <NotificationBell />
            <Button onClick={() => navigate('/profile')} variant="ghost" className="text-white hover:text-cyan-400"><UserIcon className="w-4 h-4 mr-2" />Profile</Button>
            <Button onClick={logout} variant="ghost" className="text-white hover:text-red-400"><LogOut className="w-4 h-4" /></Button>
          </div>
        </div>
      </nav>

      <div className="pt-24 px-6 pb-12">
        <div className="max-w-7xl mx-auto">
          {/* Header & Create Button */}
          <div className="flex flex-col md:flex-row items-center justify-between mb-8 gap-4">
            <div>
              <h1 className="text-4xl font-bold mb-2">Streamer Dashboard</h1>
              <p className="text-gray-400">Manage your enterprise streaming assets and analytics.</p>
            </div>
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button className="bg-gradient-to-r from-cyan-400 to-fuchsia-500 hover:opacity-90 px-8 py-6 text-lg rounded-xl text-[#05070F] font-bold">
                  <Camera className="w-5 h-5 mr-2" />Setup New Stream
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-[#0A0E27] border-white/10 text-white">
                <DialogHeader><DialogTitle className="text-2xl">Stream Details</DialogTitle></DialogHeader>
                <form onSubmit={handleCreateStream} className="space-y-4 mt-4">
                  <div><Label>Title</Label><Input value={newStream.title} onChange={(e) => setNewStream({...newStream, title: e.target.value})} required className="bg-white/5 border-white/10 mt-2" /></div>
                  <div><Label>Description</Label><Textarea value={newStream.description} onChange={(e) => setNewStream({...newStream, description: e.target.value})} required className="bg-white/5 border-white/10 mt-2" /></div>
                  <div><Label>Thumbnail URL</Label><Input value={newStream.thumbnail_url} onChange={(e) => setNewStream({...newStream, thumbnail_url: e.target.value})} className="bg-white/5 border-white/10 mt-2" /></div>
                  <Button type="submit" className="w-full bg-cyan-400 text-black font-bold py-6 rounded-xl">Create Entry</Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          {/* Stats Section - Restored to Original */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <div className="glass-panel rounded-xl p-6 border border-white/5">
              <div className="flex items-center justify-between mb-4"><DollarSign className="w-10 h-10 text-green-400" /><span className="bg-green-400/20 px-3 py-1 rounded-full text-green-400 text-sm font-semibold">Earnings</span></div>
              <h3 className="text-3xl font-bold">${totalEarnings.toFixed(3)}</h3>
              <p className="text-gray-400 text-sm">Total Revenue</p>
            </div>
            <div className="glass-panel rounded-xl p-6 border border-white/5">
              <div className="flex items-center justify-between mb-4"><Radio className="w-10 h-10 text-fuchsia-400" /><span className="bg-fuchsia-400/20 px-3 py-1 rounded-full text-fuchsia-400 text-sm font-semibold">Activity</span></div>
              <h3 className="text-3xl font-bold">{myStreams.length}</h3>
              <p className="text-gray-400 text-sm">Total Streams</p>
            </div>
            <div className="glass-panel rounded-xl p-6 border border-white/5">
              <div className="flex items-center justify-between mb-4"><Eye className="w-10 h-10 text-cyan-400" /><span className="bg-cyan-400/20 px-3 py-1 rounded-full text-cyan-400 text-sm font-semibold">Audience</span></div>
              <h3 className="text-3xl font-bold">{myStreams.reduce((s, x) => s + x.views, 0).toLocaleString()}</h3>
              <p className="text-gray-400 text-sm">Lifetime Views</p>
            </div>
          </div>

          {/* Stream Cards with Hybrid Logic */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            {myStreams.map((stream) => (
              <div key={stream.id} className="glass-panel rounded-2xl overflow-hidden border border-white/10 flex flex-col">
                <div className="relative aspect-video bg-black">
                  <video ref={videoRef} autoPlay muted playsInline className={`w-full h-full object-cover ${(localStreamActive && isDirectMode) ? 'block' : 'hidden'}`} />
                  {!(localStreamActive && isDirectMode) && (
                    <img src={stream.thumbnail_url || 'https://via.placeholder.com/640x360'} className="w-full h-full object-cover opacity-60" />
                  )}
                  {stream.is_live && <div className="absolute top-3 left-3 bg-red-600 text-[10px] font-bold px-2 py-1 rounded animate-pulse">LIVE</div>}
                </div>

                <div className="p-5 flex-1 flex flex-col">
                  <h3 className="text-lg font-bold mb-4 line-clamp-1">{stream.title}</h3>

                  <div className="bg-black/50 rounded-xl p-3 border border-white/5 mb-6">
                    <div className="flex gap-2 mb-4">
                      <button onClick={() => setIsDirectMode(true)} className={`flex-1 py-1 text-[10px] font-bold rounded ${isDirectMode ? 'bg-cyan-500 text-black' : 'text-gray-500'}`}>DIRECT</button>
                      <button onClick={() => setIsDirectMode(false)} className={`flex-1 py-1 text-[10px] font-bold rounded ${!isDirectMode ? 'bg-fuchsia-600 text-white' : 'text-gray-500'}`}>ENCODER</button>
                    </div>

                    {isDirectMode ? (
                      <Button onClick={() => startDirectBroadcast(stream.id)} disabled={isBroadcasting} className="w-full bg-cyan-500 text-black font-bold">
                        {isBroadcasting ? '● BROADCASTING' : 'START CAMERA'}
                      </Button>
                    ) : (
                      <div className="text-[9px] font-mono space-y-2">
                        <div className="p-2 bg-black rounded border border-white/5">
                          <p className="text-fuchsia-400">SERVER: {RTMP_SERVER}</p>
                        </div>
                        <div className="p-2 bg-black rounded border border-white/5">
                          <p className="text-white">KEY: {stream.stream_key || 'Generate in settings'}</p>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="mt-auto flex gap-2">
                    {stream.is_live ? (
                      <Button onClick={() => handleEndStream(stream.id)} className="flex-1 bg-red-600 hover:bg-red-700 font-bold"><StopCircle className="w-4 h-4 mr-2" /> END</Button>
                    ) : (
                      <Button onClick={() => navigate(`/stream/${stream.id}`)} variant="outline" className="flex-1 border-white/10 hover:bg-white/5">VIEW</Button>
                    )}
                    {!stream.is_live && stream.saved && (
                      <Button onClick={() => setExportStream(stream)} className="bg-green-600 hover:bg-green-700 px-3"><Upload className="w-4 h-4" /></Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* ... (Recent Earnings Table - Restored to Original below) */}
          <h2 className="text-2xl font-bold mb-6">Recent Transactions</h2>
          <div className="glass-panel rounded-xl overflow-hidden border border-white/5">
            <table className="w-full text-sm">
              <thead className="bg-white/5 text-gray-400">
                <tr><th className="p-4 text-left">Date</th><th className="p-4 text-left">Source</th><th className="p-4 text-right">Amount</th></tr>
              </thead>
              <tbody>
                {earnings.map((e) => (
                  <tr key={e.id} className="border-t border-white/5 hover:bg-white/5">
                    <td className="p-4">{new Date(e.created_at).toLocaleDateString()}</td>
                    <td className="p-4 capitalize">{e.source}</td>
                    <td className="p-4 text-right text-green-400 font-bold">+${e.amount.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StreamerDashboard;
