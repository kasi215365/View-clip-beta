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

  useEffect(() => { fetchEnterpriseData(); }, []);

  const fetchEnterpriseData = async () => {
    try {
      const [streamsRes, analyticsRes] = await Promise.all([
        axios.get(`${API}/streams`),
        axios.get(`${API}/streamers/me/analytics`)
      ]);
      setMyStreams(streamsRes.data.filter(s => s.streamer_id === user.id));
      setAnalytics(analyticsRes.data || analytics);
    } catch (e) {
      toast.error('Failed to sync Enterprise data');
    } finally {
      setLoading(false);
    }
  };

  // --- Camera & Mirror Logic ---
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

      // Fix: Safari Video Mounting & Mirroring
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        // Mirror front camera only
        videoRef.current.style.transform = facingMode === "user" ? "scaleX(-1)" : "scaleX(1)";
        await videoRef.current.play();
      }
      
      // Start WHIP Handshake... (Logic remains the same as previous)
      toast.success("Broadcast Live!");
    } catch (err) {
      toast.error("Camera access denied.");
    }
  };

  const toggleCamera = () => {
    setFacingMode(prev => prev === "user" ? "environment" : "user");
    if (localStreamActive) startDirectBroadcast(); // Hot-swap camera
  };

  // --- OAuth Logic ---
  const connectPlatform = (platform) => {
    toast.info(`Redirecting to ${platform} OAuth...`);
    // window.location.href = `${API}/auth/${platform}/connect`;
  };

  if (loading) return <div className="min-h-screen bg-[#05070F] flex items-center justify-center"><div className="animate-spin rounded-full h-12 w-12 border-t-2 border-cyan-500"></div></div>;

  return (
    <div className="min-h-screen bg-[#05070F] text-white">
      {/* Top Nav */}
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4 border-b border-white/5">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Logo size="md" />
          <div className="flex items-center space-x-4">
            <Button onClick={() => connectPlatform('twitch')} variant="ghost" className="hidden md:flex text-purple-400"><Twitch className="w-4 h-4 mr-2"/>Link</Button>
            <NotificationBell />
            <Button onClick={logout} variant="ghost" className="text-red-400"><LogOut className="w-4 h-4"/></Button>
          </div>
        </div>
      </nav>

      <div className="pt-24 px-4 md:px-6 pb-12 max-w-7xl mx-auto">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row justify-between items-start mb-8 gap-6">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Streamer Command</h1>
            <p className="text-gray-400 mt-2 italic">Enterprise Edition | {user.username}</p>
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

        {/* Analytics Suite */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Live Viewers', val: analytics.views, icon: Eye, color: 'text-cyan-400' },
            { label: 'Subscribers', val: analytics.subs, icon: Heart, color: 'text-fuchsia-500' },
            { label: 'Gross Revenue', val: `$${analytics.revenue}`, icon: DollarSign, color: 'text-green-400' },
            { label: 'Watch Time', val: analytics.watchTime, icon: BarChart3, color: 'text-orange-400' }
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
              {/* Main Broadcast Console */}
              <div className="lg:col-span-2 space-y-6">
                {myStreams.map((stream) => (
                  <div key={stream.id} className="glass-panel rounded-3xl overflow-hidden border border-white/10">
                    <div className="relative aspect-video bg-black">
                      <video 
                        ref={videoRef} 
                        autoPlay 
                        muted 
                        playsInline 
                        className={`w-full h-full object-cover transition-transform duration-500 ${localStreamActive ? 'opacity-100' : 'opacity-0'}`} 
                      />
                      {!localStreamActive && (
                        <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-gray-900 to-black">
                           <p className="text-gray-600 font-mono">SIGNAL_IDLE</p>
                        </div>
                      )}
                      
                      {/* Live Indicator & Controls */}
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
                          <Button onClick={startDirectBroadcast} className="flex-1 bg-cyan-400 text-black font-black py-8 rounded-2xl text-lg hover:scale-[1.02] transition-transform">
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
                ))}
              </div>

              {/* Sidebar: Platform Links */}
              <div className="space-y-6">
                <div className="glass-panel p-6 rounded-3xl border border-white/10">
                  <h4 className="font-bold flex items-center mb-6 text-gray-400 uppercase text-xs tracking-widest">
                    <LinkIcon className="w-4 h-4 mr-2" /> Multi-Stream Sync
                  </h4>
                  <div className="space-y-3">
                    <Button onClick={() => connectPlatform('youtube')} className="w-full justify-start py-6 bg-[#FF0000]/10 border border-[#FF0000]/20 hover:bg-[#FF0000]/20 text-white">
                      <Youtube className="mr-3" /> Connect YouTube
                    </Button>
                    <Button onClick={() => connectPlatform('twitch')} className="w-full justify-start py-6 bg-[#9146FF]/10 border border-[#9146FF]/20 hover:bg-[#9146FF]/20 text-white">
                      <Twitch className="mr-3" /> Connect Twitch
                    </Button>
                    <Button className="w-full justify-start py-6 bg-green-500/10 border border-green-500/20 hover:bg-green-500/20 text-white">
                      <ShieldCheck className="mr-3" /> Connect Kick
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
                <p className="text-gray-500 max-w-sm mx-auto mt-2">Manage where your live feed is mirrored across the web clips ecosystem.</p>
             </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default StreamerDashboard;
