import { useState, useEffect, useContext, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Radio, DollarSign, Eye, Gift, LogOut, User as UserIcon, Home, Save, Upload, Youtube, Twitch, BarChart3, Users2, Heart, Link2 as LinkIcon, StopCircle, Camera, RefreshCw } from 'lucide-react';
import Logo from '@/components/Logo';
import NotificationBell from '@/components/NotificationBell';
import axios from 'axios';
import { toast } from 'sonner';

const StreamerDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  
  // Data & UI States
  const [myStreams, setMyStreams] = useState([]);
  const [earnings, setEarnings] = useState([]);
  const [totalEarnings, setTotalEarnings] = useState(0);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newStream, setNewStream] = useState({ title: '', description: '', thumbnail_url: '' });

  // --- Hybrid Streaming & Camera States ---
  const [isDirectMode, setIsDirectMode] = useState(true);
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const [localStreamActive, setLocalStreamActive] = useState(false);
  const [facingMode, setFacingMode] = useState("user"); // "user" = front, "environment" = back
  const peerConnection = useRef(null);
  const videoRef = useRef(null);
  const currentStream = useRef(null);

  const WHIP_URL = "https://customer-9j4l1hq89yi1muyd.cloudflarestream.com/6ef4e44200f89257909749dd7935badck340fafedcee8f68d1a4eac6518df78de/webRTC/publish";
  const RTMP_SERVER = "rtmps://live.cloudflare.com:443/live/";

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

  const startDirectBroadcast = async () => {
    try {
      // 1. Get Camera with current facingMode
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 1280, height: 720, facingMode: facingMode }, 
        audio: true 
      });
      
      currentStream.current = stream;
      setLocalStreamActive(true);
      setIsBroadcasting(true);

      // 2. Immediate Video Binding Fix (Prevents Black Screen)
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(e => console.error("Playback error", e));
        }
      }, 150);
      
      // 3. WebRTC Handshake
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
      
      toast.success("Broadcast Live!");
    } catch (err) {
      toast.error("Camera access failed. Check Safari permissions.");
      setLocalStreamActive(false);
      setIsBroadcasting(false);
    }
  };

  const toggleCamera = async () => {
    const newMode = facingMode === "user" ? "environment" : "user";
    setFacingMode(newMode);
    
    if (localStreamActive) {
      // Stop current tracks
      currentStream.current.getTracks().forEach(track => track.stop());
      // Restart with new mode
      startDirectBroadcast();
      toast.info(`Switched to ${newMode === "user" ? "Front" : "Back"} camera`);
    }
  };

  const handleEndStream = async (streamId) => {
    try {
      if (currentStream.current) {
        currentStream.current.getTracks().forEach(track => track.stop());
      }
      peerConnection.current?.close();
      
      await axios.post(`${API}/streams/${streamId}/end`);
      setIsBroadcasting(false);
      setLocalStreamActive(false);
      toast.success(`Stream ended.`);
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
      fetchData();
    } catch (error) { toast.error('Creation failed'); }
  };

  if (loading) return <div className="min-h-screen bg-[#05070F] flex items-center justify-center"><div className="animate-spin rounded-full h-12 w-12 border-t-2 border-cyan-500"></div></div>;

  return (
    <div className="min-h-screen bg-[#05070F] text-white">
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Logo size="md" />
          <div className="flex items-center space-x-4">
            <Button onClick={() => navigate('/browse')} variant="ghost"><Home className="w-4 h-4 mr-2" />Browse</Button>
            <NotificationBell />
            <Button onClick={logout} variant="ghost" className="text-red-400"><LogOut className="w-4 h-4" /></Button>
          </div>
        </div>
      </nav>

      <div className="pt-24 px-6 pb-12">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
            <h1 className="text-4xl font-bold">Streamer Dashboard</h1>
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button className="bg-gradient-to-r from-cyan-400 to-fuchsia-500 text-black font-bold px-8 py-6 rounded-xl">
                  <Camera className="w-5 h-5 mr-2" />New Stream
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-[#0A0E27] border-white/10 text-white">
                <DialogHeader><DialogTitle>Create Stream</DialogTitle></DialogHeader>
                <form onSubmit={handleCreateStream} className="space-y-4 mt-4">
                  <Input placeholder="Title" value={newStream.title} onChange={(e) => setNewStream({...newStream, title: e.target.value})} className="bg-white/5 border-white/10" />
                  <Textarea placeholder="Description" value={newStream.description} onChange={(e) => setNewStream({...newStream, description: e.target.value})} className="bg-white/5 border-white/10" />
                  <Button type="submit" className="w-full bg-cyan-400 text-black font-bold py-6">Go Live</Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            {myStreams.map((stream) => (
              <div key={stream.id} className="glass-panel rounded-2xl overflow-hidden border border-white/10 flex flex-col">
                <div className="relative aspect-video bg-black">
                  <video ref={videoRef} autoPlay muted playsInline className={`w-full h-full object-cover ${localStreamActive ? 'block' : 'hidden'}`} />
                  {!localStreamActive && <img src={stream.thumbnail_url || 'https://via.placeholder.com/640x360'} className="w-full h-full object-cover opacity-50" />}
                  
                  {/* Camera Flip Button */}
                  {localStreamActive && (
                    <Button onClick={toggleCamera} className="absolute top-2 right-2 bg-black/50 hover:bg-black/80 rounded-full p-2 h-10 w-10 border border-white/20">
                      <RefreshCw className="w-5 h-5" />
                    </Button>
                  )}
                  {stream.is_live && <div className="absolute top-3 left-3 bg-red-600 text-[10px] font-bold px-2 py-1 rounded animate-pulse shadow-lg">LIVE</div>}
                </div>

                <div className="p-5 flex-1 flex flex-col">
                  <h3 className="text-lg font-bold mb-4 line-clamp-1">{stream.title}</h3>
                  <div className="bg-black/50 rounded-xl p-3 border border-white/5 mb-6">
                    <div className="flex gap-2 mb-4">
                      <button onClick={() => setIsDirectMode(true)} className={`flex-1 py-1 text-[10px] font-bold rounded ${isDirectMode ? 'bg-cyan-500 text-black' : 'text-gray-500'}`}>DIRECT</button>
                      <button onClick={() => setIsDirectMode(false)} className={`flex-1 py-1 text-[10px] font-bold rounded ${!isDirectMode ? 'bg-fuchsia-600 text-white' : 'text-gray-500'}`}>ENCODER</button>
                    </div>

                    {isDirectMode ? (
                      <Button onClick={startDirectBroadcast} disabled={isBroadcasting} className="w-full bg-cyan-500 text-black font-bold h-12">
                        {isBroadcasting ? '● BROADCASTING' : 'START CAMERA'}
                      </Button>
                    ) : (
                      <div className="text-[9px] font-mono space-y-2 py-2">
                        <div className="p-2 bg-black rounded border border-white/5 text-fuchsia-400 truncate">URL: {RTMP_SERVER}</div>
                        <div className="p-2 bg-black rounded border border-white/5 text-white truncate">KEY: {stream.stream_key}</div>
                      </div>
                    )}
                  </div>

                  <div className="mt-auto flex gap-2">
                    {isBroadcasting || stream.is_live ? (
                      <Button onClick={() => handleEndStream(stream.id)} className="flex-1 bg-red-600 hover:bg-red-700 font-bold"><StopCircle className="w-4 h-4 mr-2" /> END LIVE</Button>
                    ) : (
                      <Button onClick={() => navigate(`/stream/${stream.id}`)} variant="outline" className="flex-1 border-white/10">VIEW</Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <h2 className="text-2xl font-bold mb-6">Recent Transactions</h2>
          <div className="glass-panel rounded-xl overflow-hidden border border-white/5">
            <table className="w-full text-sm">
              <thead className="bg-white/5 text-gray-400">
                <tr><th className="p-4 text-left">Date</th><th className="p-4 text-left">Source</th><th className="p-4 text-right">Amount</th></tr>
              </thead>
              <tbody>
                {earnings.slice(0, 5).map((e) => (
                  <tr key={e.id} className="border-t border-white/5 hover:bg-white/5">
                    <td className="p-4 text-gray-400">{new Date(e.created_at).toLocaleDateString()}</td>
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
