import { useState, useEffect, useContext, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Radio, DollarSign, Eye, Gift, LogOut, User as UserIcon, Home, Save, Youtube, Twitch, Link2 as LinkIcon } from 'lucide-react';
import Logo from '@/components/Logo';
import NotificationBell from '@/components/NotificationBell';
import axios from 'axios';
import { toast } from 'sonner';

const StreamerDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  const [myStreams, setMyStreams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [oauth, setOauth] = useState({ connections: [], available_providers: [] });
  const [newStream, setNewStream] = useState({ title: '', description: '', thumbnail_url: '' });

  // --- Hybrid Streaming State ---
  const [isDirectMode, setIsDirectMode] = useState(true);
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const peerConnection = useRef(null);
  const videoRef = useRef(null);

  // Hard-coded Production URLs for Viewclip
  const WHIP_URL = "https://customer-9j4l1hq89yi1muyd.cloudflarestream.com/6ef4e44200f89257909749dd7935badck340fafedcee8f68d1a4eac6518df78de/webRTC/publish";
  const SRT_URL = "srt://live.cloudflare.com:778?passphrase=0df478722a79e36e72e60e10e60ba187k340fafedcee8f68d1a4eac6518df78de&streamid=340fafedcee8f68d1a4eac6518df78de";
  const RTMP_SERVER = "rtmps://live.cloudflare.com:443/live/";

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [streamsRes, oauthRes] = await Promise.all([
        axios.get(`${API}/streams`),
        axios.get(`${API}/oauth/connections`).catch(() => ({ data: { connections: [] } })),
      ]);
      setMyStreams(streamsRes.data.filter((s) => s.streamer_id === user.id));
      setOauth(oauthRes.data);
    } catch (e) {
      toast.error('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const handleEndStream = async (streamId) => {
    try {
      await axios.post(`${API}/streams/${streamId}/end`);
      setIsBroadcasting(false);
      if (peerConnection.current) {
        peerConnection.current.getTracks().forEach(track => track.stop());
        peerConnection.current.close();
      }
      toast.success('Stream ended');
      fetchData();
    } catch (e) {
      toast.error('Failed to end stream');
    }
  };

  // --- Direct Broadcast Logic (WHIP) ---
  const startDirectBroadcast = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
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

      if (!response.ok) throw new Error("Broadcast Handshake Failed");

      const answerSdp = await response.text();
      await peerConnection.current.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: answerSdp }));
      setIsBroadcasting(true);
      toast.success("You are now LIVE on Viewclip!");
    } catch (err) {
      toast.error("Camera access failed or Broadcast URL rejected.");
    }
  };

  if (loading) return <div className="flex items-center justify-center min-h-screen bg-[#05070F]"><div className="spinner"></div></div>;

  return (
    <div className="min-h-screen bg-[#05070F] text-white">
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Logo size="md" />
          <div className="flex items-center space-x-4">
            <Button onClick={() => navigate('/browse')} variant="ghost" className="text-white hover:text-cyan-400"><Home className="w-4 h-4 mr-2" />Browse</Button>
            <Button onClick={logout} variant="ghost" className="text-white hover:text-red-400"><LogOut className="w-4 h-4" /></Button>
          </div>
        </div>
      </nav>

      <div className="pt-24 px-6 pb-12">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-4xl font-bold mb-8">Streamer Dashboard</h1>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {myStreams.map((stream) => (
              <div key={stream.id} className="glass-panel rounded-xl overflow-hidden border border-white/5">
                <div className="relative aspect-video">
                  <img src={stream.thumbnail_url} alt="Stream Thumb" className="w-full h-full object-cover" />
                  {stream.is_live && <div className="absolute top-2 left-2 bg-red-500 text-white px-3 py-1 rounded-full text-[10px] font-bold animate-pulse text-uppercase">Live</div>}
                </div>
                
                <div className="p-4">
                  <h3 className="font-bold mb-3">{stream.title}</h3>
                  
                  {/* Mode Selector */}
                  <div className="bg-black/40 border border-white/10 rounded p-3 mb-4">
                    <div className="flex gap-2 mb-4">
                      <button 
                        onClick={() => setIsDirectMode(true)} 
                        className={`flex-1 text-[10px] py-1 rounded font-bold uppercase transition-all ${isDirectMode ? 'bg-cyan-400 text-black' : 'text-gray-500'}`}
                      >
                        Direct Live
                      </button>
                      <button 
                        onClick={() => setIsDirectMode(false)} 
                        className={`flex-1 text-[10px] py-1 rounded font-bold uppercase transition-all ${!isDirectMode ? 'bg-fuchsia-500 text-white' : 'text-gray-500'}`}
                      >
                        Advanced (OBS)
                      </button>
                    </div>

                    {isDirectMode ? (
                      <div className="space-y-3">
                        <video ref={videoRef} autoPlay muted playsInline className="w-full aspect-video bg-black rounded border border-white/10" />
                        {!isBroadcasting ? (
                          <Button onClick={startDirectBroadcast} className="w-full bg-cyan-400 text-black text-xs font-bold">START CAMERA</Button>
                        ) : (
                          <div className="text-center text-[10px] text-green-400 font-bold border border-green-400/30 py-2 rounded">● BROADCASTING</div>
                        )}
                      </div>
                    ) : (
                      <div className="space-y-3 text-[10px]">
                        <div>
                          <p className="text-fuchsia-400 uppercase font-bold mb-1">RTMP Server</p>
                          <div className="bg-black p-2 rounded border border-white/5 font-mono select-all text-gray-300 break-all">{RTMP_SERVER}</div>
                        </div>
                        <div>
                          <p className="text-fuchsia-400 uppercase font-bold mb-1">Stream Key</p>
                          <div className="bg-black p-2 rounded border border-white/5 font-mono select-all text-white break-all">{stream.stream_key}</div>
                        </div>
                        <div>
                          <p className="text-fuchsia-400 uppercase font-bold mb-1">SRT URL (Low Latency)</p>
                          <div className="bg-black p-2 rounded border border-white/5 font-mono select-all text-cyan-300 break-all">{SRT_URL}</div>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    {stream.is_live && <Button onClick={() => handleEndStream(stream.id)} className="flex-1 bg-red-500/20 text-red-500 border border-red-500/50 hover:bg-red-500 hover:text-white">End</Button>}
                    <Button onClick={() => navigate(`/stream/${stream.id}`)} className="flex-1 bg-white/5 hover:bg-white/10">View Link</Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StreamerDashboard;
