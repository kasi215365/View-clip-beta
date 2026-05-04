import { useState, useEffect, useContext, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Radio, DollarSign, Eye, Gift, LogOut, User as UserIcon, Home, Save, 
  Upload, Youtube, Twitch, BarChart3, Users2, Heart, Link2 as LinkIcon, 
  StopCircle, Camera, RefreshCw, Download, Share2, ShieldCheck, Zap
} from 'lucide-react';
import Logo from '@/components/Logo';
import NotificationBell from '@/components/NotificationBell';
import axios from 'axios';
import { toast } from 'sonner';

const StreamerDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  
  // --- Core State ---
  const [myStreams, setMyStreams] = useState([]);
  const [analytics, setAnalytics] = useState({ views: 0, subs: 0, revenue: 0, watchTime: '0h' });
  const [loading, setLoading] = useState(true);
  
  // --- Broadcast & Camera State ---
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const [localStreamActive, setLocalStreamActive] = useState(false);
  const [facingMode, setFacingMode] = useState("user"); 
  const peerConnection = useRef(null);
  const videoRef = useRef(null);
  const currentStream = useRef(null);

  const WHIP_URL = "https://customer-9j4l1hq89yi1muyd.cloudflarestream.com/6ef4e44200f89257909749dd7935badck340fafedcee8f68d1a4eac6518df78de/webRTC/publish";

  useEffect(() => { fetchDashboardData(); }, []);

  const fetchDashboardData = async () => {
    try {
      const [streamsRes, analyticsRes] = await Promise.all([
        axios.get(`${API}/streams`),
        axios.get(`${API}/streamers/me/analytics`)
      ]);
      setMyStreams(streamsRes.data.filter(s => s.streamer_id === user.id));
      if (analyticsRes.data) setAnalytics(analyticsRes.data);
    } catch (e) {
      console.error('Data sync error', e);
    } finally {
      setLoading(false);
    }
  };

  const startDirectBroadcast = async () => {
    try {
      if (currentStream.current) {
        currentStream.current.getTracks().forEach(t => t.stop());
      }

      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: facingMode }, 
        audio: true 
      });
      
      currentStream.current = stream;
      setLocalStreamActive(true);
      setIsBroadcasting(true);

      // Safari Video Mounting & Mirroring Fix
      setTimeout(async () => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.style.transform = facingMode === "user" ? "scaleX(-1)" : "scaleX(1)";
          try {
            await videoRef.current.play();
          } catch (e) {
            console.error("Autoplay prevented", e);
          }
        }
      }, 200);
      
      peerConnection.current = new RTCPeerConnection();
      stream.getTracks().forEach(track => peerConnection.current.addTrack(track, stream));

      const offer = await peerConnection.current.createOffer();
      await peerConnection.current.setLocalDescription(offer);

      const response = await fetch(WHIP_URL, {
        method: 'POST',
        body: offer.sdp,
        headers: { 'Content-Type': 'application/sdp' }
      });

      if (!response.ok) throw new Error("Handshake Failed");
      const answerSdp = await response.text();
      await peerConnection.current.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: answerSdp }));
      
      toast.success("Broadcast Live!");
    } catch (err) {
      toast.error("Camera access failed.");
      setLocalStreamActive(false);
      setIsBroadcasting(false);
    }
  };

  const toggleCamera = () => {
    setFacingMode(prev => prev === "user" ? "environment" : "user");
    if (localStreamActive) startDirectBroadcast();
  };

  const connectPlatform = (platform) => {
    toast.info(`Connecting to ${platform}...`);
  };

  if (loading) return <div className="min-h-screen bg-[#05070F] flex items-center justify-center"><div className="animate-spin rounded-full h-12 w-12 border-t-2 border-cyan-500"></div></div>;

  return (
    <div className="min-h-screen bg-[#05070F] text-white">
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4 border-b border-white/5">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Logo size="md" />
          <div className="flex items-center space-x-4">
            <NotificationBell />
            <Button onClick={logout} variant="ghost" className="text-red-400"><LogOut className="w-4 h-4"/></Button>
          </div>
        </div>
      </nav>

      <div className="pt-24 px-4 md:px-6 pb-12 max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row justify-between items-start mb-8 gap-6">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Streamer Command</h1>
            <p className="text-gray-400 mt-1 uppercase text-[10px] tracking-widest font-bold">{user.username}</p>
          </div>
          <div className="flex gap-3 w-full md:w-auto">
            <Dialog>
              <DialogTrigger asChild>
                <Button className="flex-1 bg-white text-black font-bold hover:bg-gray-200"><Download className="w-4 h-4 mr-2"/>Export Data</Button>
              </DialogTrigger>
              <DialogContent className="bg-[#0A0E27] border-white/10 text-white">
                <DialogHeader><DialogTitle>Financial Export</DialogTitle></DialogHeader>
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <Button variant="outline" className="h-24 flex flex-col gap-2"><BarChart3/>CSV Report</Button>
                  <Button variant="outline" className="h-24 flex flex-col gap-2"><DollarSign/>Tax Ledger</Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Live Viewers', val: analytics.views || 0, icon: Eye, color: 'text-cyan-400' },
            { label: 'Subscribers', val: analytics.subs || 0, icon: Heart, color: 'text-fuchsia-500' },
            { label: 'Gross Revenue', val: `$${analytics.revenue || 0}`, icon: DollarSign, color: 'text-green-400' },
            { label: 'Watch Time', val: analytics.watchTime || '0h', icon: BarChart3, color: 'text-orange-400' }
          ].map((stat, i) => (
            <div key={i} className="glass-panel p-4 rounded-2xl border border-white/5">
              <div className="flex justify-between items-start mb-2">
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
                <span className="text-[10px] text-green-500 font-bold">+12%</span>
              </div>
              <p className="text-2xl font-bold">{stat.val}</p>
              <p className="text-xs text-gray-500 uppercase tracking-widest">{stat.label}</p>
            </div>
          ))}
        </div>

        <Tabs defaultValue="live" className="space-y-6">
          <TabsList className="bg-white/5 border border-white/10 p-1">
            <TabsTrigger value="live">Broadcast</TabsTrigger>
            <TabsTrigger value="platforms">Platform Sync</TabsTrigger>
            <TabsTrigger value="settings">Advanced</TabsTrigger>
          </TabsList>

          <TabsContent value="live">
            <div className="grid lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                {myStreams.length > 0 ? myStreams.map((stream) => (
                  <div key={stream.id} className="glass-panel rounded-3xl overflow-hidden border border-white/10">
                    <div className="relative aspect-video bg-black">
                      <video 
                        ref={videoRef} 
                        autoPlay 
                        muted 
                        playsInline 
                        className={`w-full h-full object-cover transition-opacity duration-500 ${localStreamActive ? 'opacity-100' : 'opacity-0'}`} 
                      />
                      {!localStreamActive && (
                        <div className="absolute inset-0 flex items-center justify-center bg-[#070912]">
                           <p className="text-gray-700 font-mono text-sm tracking-tighter">SIGNAL_IDLE</p>
                        </div>
                      )}
                      
                      <div className="absolute top-4 left-4 flex gap-2">
                         {isBroadcasting && <div className="bg-red-600 px-3 py-1 rounded text-[10px] font-black animate-pulse uppercase">Live</div>}
                         <div className="bg-black/60 px-3 py-1 rounded text-[10px] font-bold backdrop-blur-md uppercase tracking-tighter border border-white/10">{facingMode === 'user' ? 'Front Cam' : 'Back Cam'}</div>
                      </div>

                      {localStreamActive && (
                        <Button onClick={toggleCamera} className="absolute bottom-4 right-4 bg-white/10 hover:bg-white/20 backdrop-blur-xl rounded-full p-4 h-14 w-14 border border-white/20">
                          <RefreshCw className="w-6 h-6 text-cyan-400" />
                        </Button>
                      )}
                    </div>

                    <div className="p-6">
                      <h3 className="text-2xl font-bold mb-4">{stream.title}</h3>
                      <div className="flex gap-4">
                        {!isBroadcasting ? (
                          <Button onClick={startDirectBroadcast} className="flex-1 bg-cyan-400 text-black font-black py-8 rounded-2xl text-lg hover:scale-[1.01] transition-transform">
                            <Zap className="w-6 h-6 mr-2" /> INITIALIZE BROADCAST
                          </Button>
                        ) : (
                          <Button onClick={() => setIsBroadcasting(false)} className="flex-1 bg-red-600 text-white font-black py-8 rounded-2xl text-lg">
                            <StopCircle className="w-6 h-6 mr-2" /> CEASE SIGNAL
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                )) : (
                  <div className="glass-panel p-20 text-center rounded-3xl border border-dashed border-white/10">
                    <p className="text-gray-500">No active stream configurations found.</p>
                    <Button onClick={() => navigate('/browse')} className="mt-4" variant="link">Create one in Browse</Button>
                  </div>
                )}
              </div>

              <div className="space-y-6">
                <div className="glass-panel p-6 rounded-3xl border border-white/10">
                  <h4 className="font-bold flex items-center mb-6 text-gray-400 uppercase text-xs tracking-widest">
                    <LinkIcon className="w-4 h-4 mr-2" /> Multi-Stream Sync
                  </h4>
                  <div className="space-y-3">
                    <Button onClick={() => connectPlatform('youtube')} className="w-full justify-start py-6 bg-red-500/5 border border-red-500/10 hover:bg-red-500/10 text-white">
                      <Youtube className="mr-3 w-5 h-5 text-red-500" /> Connect YouTube
                    </Button>
                    <Button onClick={() => connectPlatform('twitch')} className="w-full justify-start py-6 bg-purple-500/5 border border-purple-500/10 hover:bg-purple-500/10 text-white">
                      <Twitch className="mr-3 w-5 h-5 text-purple-500" /> Connect Twitch
                    </Button>
                    <Button className="w-full justify-start py-6 bg-green-500/5 border border-green-500/10 hover:bg-green-500/10 text-white">
                      <ShieldCheck className="mr-3 w-5 h-5 text-green-500" /> Connect Kick
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>
          
          <TabsContent value="platforms">
             <div className="glass-panel p-12 rounded-3xl text-center border border-white/5">
                <Share2 className="w-12 h-12 mx-auto mb-4 text-cyan-400 opacity-50" />
                <h3 className="text-xl font-bold">Syndication Controls</h3>
                <p className="text-gray-500 max-w-sm mx-auto mt-2">Manage your live feed mirroring across external platforms.</p>
             </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default StreamerDashboard;
