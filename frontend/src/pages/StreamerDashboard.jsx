import { useState, useEffect, useContext, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Home, LogOut, Video, Settings, Cast } from 'lucide-react';
import Logo from '@/components/Logo';
import axios from 'axios';
import { toast } from 'sonner';

const StreamerDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  const [myStreams, setMyStreams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isDirectMode, setIsDirectMode] = useState(true);
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const peerConnection = useRef(null);
  const videoRef = useRef(null);

  // Hard-coded Production URLs
  const WHIP_URL = "https://customer-9j4l1hq89yi1muyd.cloudflarestream.com/6ef4e44200f89257909749dd7935badck340fafedcee8f68d1a4eac6518df78de/webRTC/publish";
  const RTMP_SERVER = "rtmps://live.cloudflare.com:443/live/";
  const SRT_URL = "srt://live.cloudflare.com:778?passphrase=0df478722a79e36e72e60e10e60ba187k340fafedcee8f68d1a4eac6518df78de&streamid=340fafedcee8f68d1a4eac6518df78de";

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const res = await axios.get(`${API}/streams`);
      setMyStreams(res.data.filter((s) => s.streamer_id === user.id));
    } catch (e) {
      toast.error('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

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

      if (!response.ok) throw new Error("Broadcast Failed");
      const answerSdp = await response.text();
      await peerConnection.current.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: answerSdp }));
      setIsBroadcasting(true);
      toast.success("LIVE!");
    } catch (err) {
      toast.error("Handshake failed. Check camera permissions.");
    }
  };

  if (loading) return <div className="min-h-screen bg-[#05070F] flex items-center justify-center"><div className="animate-spin rounded-full h-8 w-8 border-t-2 border-cyan-500"></div></div>;

  return (
    <div className="min-h-screen bg-[#05070F] text-white font-sans">
      <nav className="fixed top-0 w-full z-50 bg-[#05070F]/80 backdrop-blur-md border-b border-white/5 px-4 py-3">
        <div className="max-w-5xl mx-auto flex justify-between items-center">
          <Logo size="sm" />
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" onClick={() => navigate('/browse')}><Home className="w-4 h-4" /></Button>
            <Button size="sm" variant="ghost" className="text-red-400" onClick={logout}><LogOut className="w-4 h-4" /></Button>
          </div>
        </div>
      </nav>

      <main className="pt-20 px-4 max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold mb-6 tracking-tight">Streamer Dashboard</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {myStreams.map((stream) => (
            <div key={stream.id} className="bg-[#0A0C14] border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
              {/* Fixed Video/Thumb Area */}
              <div className="relative aspect-video bg-black flex items-center justify-center">
                {isBroadcasting && isDirectMode ? (
                  <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover" />
                ) : (
                  <img 
                    src={stream.thumbnail_url || 'https://via.placeholder.com/640x360?text=Viewclip+Stream'} 
                    alt="Preview" 
                    className="w-full h-full object-cover opacity-60"
                  />
                )}
                {stream.is_live && <div className="absolute top-3 left-3 bg-red-600 px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider">Live</div>}
              </div>

              <div className="p-4">
                <div className="flex justify-between items-start mb-4">
                  <h2 className="text-lg font-semibold truncate">{stream.title || 'Untitled Stream'}</h2>
                  <Button variant="ghost" size="sm" onClick={() => navigate(`/stream/${stream.id}`)} className="text-cyan-400 h-7 text-[10px]">VIEW LINK</Button>
                </div>

                {/* Stream Mode Toggle - Minimalist */}
                <div className="bg-white/5 rounded-xl p-3 border border-white/5">
                  <div className="flex p-1 bg-black/40 rounded-lg mb-3">
                    <button 
                      onClick={() => setIsDirectMode(true)}
                      className={`flex-1 py-1.5 text-[10px] font-bold rounded-md transition-all ${isDirectMode ? 'bg-cyan-500 text-black shadow-lg shadow-cyan-500/20' : 'text-gray-400 hover:text-white'}`}
                    >
                      DIRECT LIVE
                    </button>
                    <button 
                      onClick={() => setIsDirectMode(false)}
                      className={`flex-1 py-1.5 text-[10px] font-bold rounded-md transition-all ${!isDirectMode ? 'bg-fuchsia-600 text-white shadow-lg shadow-fuchsia-500/20' : 'text-gray-400 hover:text-white'}`}
                    >
                      ADVANCED (OBS)
                    </button>
                  </div>

                  {isDirectMode ? (
                    <Button 
                      onClick={startDirectBroadcast} 
                      className={`w-full h-10 font-bold transition-all ${isBroadcasting ? 'bg-green-500/20 text-green-500 border border-green-500/50' : 'bg-cyan-500 text-black hover:bg-cyan-400'}`}
                    >
                      {isBroadcasting ? '● BROADCASTING' : 'START CAMERA'}
                    </Button>
                  ) : (
                    <div className="space-y-2 text-[10px] font-mono bg-black/60 p-2 rounded-lg border border-white/5">
                      <div className="flex justify-between items-center">
                        <span className="text-fuchsia-400 font-bold">STREAM KEY</span>
                        <span className="text-white select-all">{stream.stream_key}</span>
                      </div>
                      <div className="flex flex-col gap-1 border-t border-white/5 pt-1">
                        <span className="text-gray-500">RTMP SERVER</span>
                        <span className="text-gray-400 break-all text-[9px]">{RTMP_SERVER}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
};

export default StreamerDashboard;
