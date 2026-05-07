import { useState, useEffect, useContext, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  DollarSign, Eye, LogOut, Youtube, Twitch, BarChart3, Heart, 
  Link2 as LinkIcon, RefreshCw, Download, Share2, 
  Zap, History, PlayCircle, Settings
} from 'lucide-react';
import Logo from '@/components/Logo';
import NotificationBell from '@/components/NotificationBell';
import axios from 'axios';
import { toast } from 'sonner';

const StreamerDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  
  // --- Core State ---
  const [pastStreams, setPastStreams] = useState([]);
  const [analytics, setAnalytics] = useState({ views: 0, subs: 0, revenue: 0, watchTime: '0h' });
  const [loading, setLoading] = useState(true);
  
  // --- Path Switch State ---
  const [useEncoder, setUseEncoder] = useState(false);
  
  // --- Broadcast & Camera State ---
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const [localStreamActive, setLocalStreamActive] = useState(false);
  const [facingMode, setFacingMode] = useState("user"); 
  const videoRef = useRef(null);
  const currentStream = useRef(null);
  const peerConnection = useRef(null);

  const WHIP_URL = "https://customer-9j4l1hq89yi1muyd.cloudflarestream.com/6ef4e44200f89257909749dd7935badck340fafedcee8f68d1a4eac6518df78de/webRTC/publish";

  useEffect(() => { fetchDashboardData(); }, []);

  const fetchDashboardData = async () => {
    try {
      const [streamsRes, analyticsRes] = await Promise.all([
        axios.get(`${API}/streams`),
        axios.get(`${API}/streamers/me/analytics`)
      ]);
      setPastStreams(streamsRes.data.filter(s => s.streamer_id === user.id));
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

      setTimeout(async () => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.style.transform = facingMode === "user" ? "scaleX(-1)" : "scaleX(1)";
          await videoRef.current.play();
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
      
      toast.success("Broadcast Signal Established");
    } catch (err) {
      toast.error("Camera access failed.");
      setLocalStreamActive(false);
      setIsBroadcasting(false);
    }
  };

  // --- OPTIMIZED: The Immediate Responsiveness Cease Function ---
  const ceaseBroadcastSignal = () => {
      // 1. IMMEDIATE UI RESET: Flips visual state instantly for the user.
      setIsBroadcasting(false);
      setLocalStreamActive(false);

      console.log("VIEWCLIP_COMMAND [PHI]: Broadcast signal terminated by user. Beginning immediate teardown.");
      toast.info("Stream Ceased Immediately.");

      // 2. EXPLICIT HARDWARE SHUTDOWN: Forces tracks to stop.
      if (currentStream.current) {
          currentStream.current.getTracks().forEach(track => {
              if (track.readyState === 'live') {
                  track.stop();
              }
          });
          currentStream.current = null;
      }

      // 3. VIDEO ELEMENT RESET: Prevents visual lag/freezing in Safari.
      if (videoRef.current) {
          videoRef.current.srcObject = null;
          if (!videoRef.current.paused) {
              videoRef.current.pause();
          }
      }

      // 4. PEER CONNECTION TEARDOWN: Clean up the WebRTC session.
      if (peerConnection.current) {
          peerConnection.current.close();
          peerConnection.current = null;
      }
  };
  // ------------------------------------------------------------

  const toggleCamera = () => {
    setFacingMode(prev => prev === "user" ? "environment" : "user");
    if (localStreamActive) startDirectBroadcast();
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
          <Dialog>
            <DialogTrigger asChild>
              <Button className="w-full md:w-auto bg-white text-black font-bold hover:bg-gray-200"><Download className="w-4 h-4 mr-2"/>Export Data</Button>
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
              <p className="text-xs text-gray-500 uppercase tracking-widest text-[9px]">{stat.label}</p>
            </div>
          ))}
        </div>

        <Tabs defaultValue="live" className="space-y-6">
          <TabsList className="bg-white/5 border border-white/10 p-1">
            <TabsTrigger value="live">Broadcast</TabsTrigger>
            <TabsTrigger value="content">Saved Content</TabsTrigger>
            <TabsTrigger value="platforms">Platform Sync</TabsTrigger>
          </TabsList>

          <TabsContent value="live">
            <div className="grid lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                
                {/* Path Switcher */}
                <div className="flex bg-white/5 p-1 rounded-xl border border-white/10 w-fit">
                  <Button 
                    variant={!useEncoder ? "secondary" : "ghost"} 
                    size="sm" 
                    onClick={() => setUseEncoder(false)}
                    className="text-[10px] font-bold uppercase tracking-widest px-4 h-8"
                  >
                    Direct Path
                  </Button>
                  <Button 
                    variant={useEncoder ? "secondary" : "ghost"} 
                    size="sm" 
                    onClick={() => setUseEncoder(true)}
                    className="text-[10px] font-bold uppercase tracking-widest px-4 h-8"
                  >
                    Encoder Path
                  </Button>
                </div>

                <div className="glass-panel rounded-3xl overflow-hidden border border-white/10 bg-black/20">
                  {!useEncoder ? (
                    <>
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
                             <p className="text-gray-700 font-mono text-sm tracking-tighter italic">SIGNAL_IDLE</p>
                          </div>
                        )}
                        <div className="absolute top-4 left-4 flex gap-2">
                           {isBroadcasting && <div className="bg-red-600 px-3 py-1 rounded text-[10px] font-black animate-pulse uppercase">Live</div>}
                           <div className="bg-black/60 px-3 py-1 rounded text-[10px] font-bold backdrop-blur-md uppercase tracking-tighter border border-white/10">
                            {facingMode === 'user' ? 'Front Cam' : 'Back Cam'}
                           </div>
                        </div>
                        {localStreamActive && (
                          <Button onClick={toggleCamera} className="absolute bottom-4 right-4 bg-white/10 hover:bg-white/20 backdrop-blur-xl rounded-full p-4 h-14 w-14 border border-white/20">
                            <RefreshCw className="w-6 h-6 text-cyan-400" />
                          </Button>
                        )}
                      </div>
                      <div className="p-6">
                        <div className="flex justify-between items-center mb-4">
                          <h3 className="text-2xl font-bold">Live Stream Engine</h3>
                          <div className="flex items-center text-[10px] text-gray-500 uppercase tracking-widest">
                            <Zap className="w-3 h-3 mr-1 text-cyan-400"/> WebRTC Path
                          </div>
                        </div>
                        {/* UPDATED BUTTON HANDLER: 
                          If broadcasting, call the optimized ceaseBroadcastSignal function 
                          for immediate responsiveness.
                        */}
                        <Button 
                          onClick={isBroadcasting ? ceaseBroadcastSignal : startDirectBroadcast} 
                          className={`w-full font-black py-8 rounded-2xl text-lg uppercase transition-all ${isBroadcasting ? 'bg-red-600 text-white' : 'bg-cyan-400 text-black hover:brightness-110'}`}
                        >
                          {isBroadcasting ? "Cease Signal" : "Initialize Direct Broadcast"}
                        </Button>
                      </div>
                    </>
                  ) : (
                    <div className="p-8 space-y-6 min-h-[400px] flex flex-col justify-center">
                      <div className="flex items-center justify-between">
                         <h3 className="text-xl font-bold italic uppercase tracking-tighter">Encoder Configuration</h3>
                         <Settings className="text-cyan-400 w-5 h-5 animate-spin-slow" />
                      </div>
                      <p className="text-xs text-gray-400 leading-relaxed">Broadcast via OBS, Prism, or vMix using these secure RTMP credentials.</p>
                      
                      <div className="space-y-4">
                        <div className="space-y-2">
                          <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">RTMP Server URL</label>
                          <div className="flex gap-2">
                            <input readOnly value="rtmps://live.cloudflare.com:443/live/" className="flex-1 bg-white/5 border border-white/10 rounded-lg p-3 text-xs font-mono" />
                            <Button variant="outline" size="sm" onClick={() => {navigator.clipboard.writeText("rtmps://live.cloudflare.com:443/live/"); toast.success("Copied URL");}}><Download className="w-4 h-4"/></Button>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Stream Key</label>
                          <div className="flex gap-2">
                            <input readOnly type="password" value="6ef4e44200f89257909749dd7935badc" className="flex-1 bg-white/5 border border-white/10 rounded-lg p-3 text-xs font-mono" />
                            <Button variant="outline" size="sm" onClick={() => {navigator.clipboard.writeText("6ef4e44200f89257909749dd7935badc"); toast.success("Copied Key");}}><Download className="w-4 h-4"/></Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-6">
                <div className="glass-panel p-6 rounded-3xl border border-white/10">
                  <h4 className="font-bold flex items-center mb-6 text-gray-400 uppercase text-[10px] tracking-widest">
                    <LinkIcon className="w-4 h-4 mr-2" /> Multi-Stream Sync
                  </h4>
                  <div className="space-y-3">
                    <Button onClick={() => toast.info("OAuth Ready")} className="w-full justify-start py-6 bg-red-500/5 border border-red-500/10 hover:bg-red-500/10 text-white">
                      <Youtube className="mr-3 w-5 h-5 text-red-500" /> Connect YouTube
                    </Button>
                    <Button onClick={() => toast.info("OAuth Ready")} className="w-full justify-start py-6 bg-purple-500/5 border border-purple-500/10 hover:bg-purple-500/10 text-white">
                      <Twitch className="mr-3 w-5 h-5 text-purple-500" /> Connect Twitch
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>
          
          <TabsContent value="content">
             <div className="grid gap-4">
                {pastStreams.length > 0 ? pastStreams.map(stream => (
                  <div key={stream.id} className="glass-panel p-4 rounded-2xl flex items-center justify-between border border-white/5">
                    <div className="flex items-center gap-4">
                       <div className="w-16 h-10 bg-white/5 rounded-md flex items-center justify-center">
                          <History className="text-gray-600 w-5 h-5" />
                       </div>
                       <div>
                          <h4 className="font-bold">{stream.title}</h4>
                          <p className="text-[10px] text-gray-500 uppercase">{new Date(stream.created_at).toLocaleDateString()}</p>
                       </div>
                    </div>
                    <Button variant="ghost" className="text-cyan-400"><PlayCircle className="w-5 h-5 mr-2" /> View Clip</Button>
                  </div>
                )) : (
                  <div className="text-center py-20 opacity-30">
                    <History className="w-12 h-12 mx-auto mb-4" />
                    <p>No saved broadcasts yet.</p>
                  </div>
                )}
             </div>
          </TabsContent>

          <TabsContent value="platforms">
             <div className="glass-panel p-12 rounded-3xl text-center border border-white/5">
                <Share2 className="w-12 h-12 mx-auto mb-4 text-cyan-400 opacity-50" />
                <h3 className="text-xl font-bold">Syndication Controls</h3>
                <p className="text-gray-500 max-w-sm mx-auto mt-2">Distribution management for the Philadelphia creator network.</p>
             </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default StreamerDashboard;
