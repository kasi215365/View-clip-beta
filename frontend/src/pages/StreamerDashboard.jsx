import { useState, useEffect, useContext, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Home, LogOut, Video, Settings, ExternalLink, StopCircle } from 'lucide-react';
import Logo from '@/components/Logo';
import axios from 'axios';
import { toast } from 'sonner';

const StreamerDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  const [myStreams, setMyStreams] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // --- Hybrid Streaming State ---
  const [isDirectMode, setIsDirectMode] = useState(true);
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const peerConnection = useRef(null);
  const videoRef = useRef(null);

  // Hard-coded Cloudflare IDs/URLs
  const WHIP_URL = "https://customer-9j4l1hq89yi1muyd.cloudflarestream.com/6ef4e44200f89257909749dd7935badck340fafedcee8f68d1a4eac6518df78de/webRTC/publish";
  const RTMP_SERVER = "rtmps://live.cloudflare.com:443/live/";
  const SRT_URL = "srt://live.cloudflare.com:778?passphrase=0df478722a79e36e72e60e10e60ba187k340fafedcee8f68d1a4eac6518df78de&streamid=340fafedcee8f68d1a4eac6518df78de";

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const res = await axios.get(`${API}/streams`);
      // Filter streams belonging to the logged-in user
      setMyStreams(res.data.filter((s) => s.streamer_id === user.id));
    } catch (e) {
      toast.error('Failed to load streams');
    } finally {
      setLoading(false);
    }
  };

  const handleEndStream = async (streamId) => {
    try {
      await axios.post(`${API}/streams/${streamId}/end`);
      setIsBroadcasting(false);
      
      // Stop local camera tracks if they are running
      if (peerConnection.current) {
        const tracks = videoRef.current?.srcObject?.getTracks();
        tracks?.forEach(track => track.stop());
        peerConnection.current.close();
      }
      
      toast.success('Stream ended successfully');
      fetchData(); // Refresh list to update "Live" status
    } catch (e) {
      toast.error('Failed to end stream');
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

      if (!response.ok) throw new Error("Broadcast handshake failed");

      const answerSdp = await response.text();
      await peerConnection.current.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: answerSdp }));
      
      setIsBroadcasting(true);
      toast.success("You are now LIVE!");
    } catch (err) {
      toast.error("Camera access failed or Cloudflare rejected the connection.");
    }
  };

  if (loading) return <div className="min-h-screen bg-[#05070F] flex items-center justify-center"><div className="animate-spin rounded-full h-12 w-12 border-t-2 border-cyan-500"></div></div>;

  return (
    <div className="min-h-screen bg-[#05070F] text-white">
      <nav className="fixed top-0 w-full z-50 bg-[#05070F]/90 backdrop-blur-sm border-b border-white/5 px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Logo size="md" />
          <div className="flex items-center space-x-4">
            <Button onClick={() => navigate('/browse')} variant="ghost" className="text-white hover:text-cyan-400">
              <Home className="w-4 h-4 mr-2" /> Browse
            </Button>
            <Button onClick={logout} variant="ghost" className="text-red-400 hover:bg-red-400/10">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </nav>

      <div className="pt-24 px-6 pb-12">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-4xl font-bold">Streamer Dashboard</h1>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {myStreams.map((stream) => (
              <div key={stream.id} className="bg-[#0D0F1A] rounded-2xl border border-white/10 overflow-hidden flex flex-col">
                {/* Thumbnail / Video Preview */}
                <div className="relative aspect-video bg-black">
                  {isBroadcasting && isDirectMode ? (
                    <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover" />
                  ) : (
                    <img 
                      src={stream.thumbnail_url || 'https://via.placeholder.com/640x360?text=Viewclip+Stream'} 
                      className="w-full h-full object-cover" 
                      alt="Thumbnail" 
                    />
                  )}
                  {stream.is_live && (
                    <div className="absolute top-3 left-3 bg-red-500 text-[10px] font-bold px-2 py-1 rounded animate-pulse">LIVE</div>
                  )}
                </div>

                <div className="p-5 flex-1 flex flex-col">
                  <h3 className="text-xl font-bold mb-4 truncate">{stream.title}</h3>

                  {/* Broadcast Controls Section */}
                  <div className="bg-black/40 rounded-xl p-3 border border-white/5 mb-6">
                    <div className="flex gap-2 mb-4">
                      <button 
                        onClick={() => setIsDirectMode(true)}
                        className={`flex-1 py-1.5 text-[10px] font-bold rounded uppercase transition-all ${isDirectMode ? 'bg-cyan-500 text-black' : 'text-gray-500'}`}
                      >
                        Direct Live
                      </button>
                      <button 
                        onClick={() => setIsDirectMode(false)}
                        className={`flex-1 py-1.5 text-[10px] font-bold rounded uppercase transition-all ${!isDirectMode ? 'bg-fuchsia-600 text-white' : 'text-gray-500'}`}
                      >
                        Advanced (OBS)
                      </button>
                    </div>

                    {isDirectMode ? (
                      <Button onClick={startDirectBroadcast} className={`w-full ${isBroadcasting ? 'bg-green-600' : 'bg-cyan-500'} text-black font-bold h-10`}>
                        {isBroadcasting ? '● BROADCASTING' : 'START CAMERA'}
                      </Button>
                    ) : (
                      <div className="space-y-2 text-[9px] font-mono">
                        <div className="p-2 bg-black rounded border border-white/10">
                          <p className="text-fuchsia-400 font-bold mb-1">RTMP SERVER</p>
                          <p className="text-gray-400 break-all">{RTMP_SERVER}</p>
                        </div>
                        <div className="p-2 bg-black rounded border border-white/10">
                          <p className="text-fuchsia-400 font-bold mb-1">STREAM KEY</p>
                          <p className="text-white select-all">{stream.stream_key}</p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Primary Action Buttons (RESTORED) */}
                  <div className="mt-auto grid grid-cols-2 gap-3">
                    {stream.is_live && (
                      <Button 
                        onClick={() => handleEndStream(stream.id)} 
                        className="bg-red-500/20 text-red-500 border border-red-500/50 hover:bg-red-500 hover:text-white"
                      >
                        <StopCircle className="w-4 h-4 mr-2" /> End
                      </Button>
                    )}
                    <Button 
                      onClick={() => navigate(`/stream/${stream.id}`)} 
                      variant="outline" 
                      className="bg-white/5 border-white/10 hover:bg-white/10 flex-1"
                    >
                      <ExternalLink className="w-4 h-4 mr-2" /> View
                    </Button>
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
