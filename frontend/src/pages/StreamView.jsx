import { useState, useEffect, useContext, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ArrowLeft, Radio, Users, Send, Wallet } from 'lucide-react';
import Logo from '@/components/Logo';
import axios from 'axios';
import { toast } from 'sonner';

const StreamView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const [stream, setStream] = useState(null);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [tiers, setTiers] = useState([]);
  const [wallet, setWallet] = useState({});
  const [loading, setLoading] = useState(true);
  const [hasJoined, setHasJoined] = useState(false);
  const [qualified, setQualified] = useState(false);
  const [followStatus, setFollowStatus] = useState({ following: false, followers_count: 0 });
  const [watchMinutes, setWatchMinutes] = useState(0);
  const scrollRef = useRef(null);
  const heartbeatRef = useRef(null);

  useEffect(() => {
    (async () => {
      await Promise.all([fetchStream(), fetchComments(), fetchTiersAndWallet()]);
      setLoading(false);
    })();
    const interval = setInterval(fetchComments, 5000);
    return () => {
      clearInterval(interval);
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
    };
  }, [id]);

  useEffect(() => {
    if (stream?.streamer_id) {
      axios.get(`${API}/streamers/${stream.streamer_id}/follow-status`)
        .then((r) => setFollowStatus(r.data))
        .catch(() => {});
    }
  }, [stream?.streamer_id]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [comments]);

  const fetchStream = async () => {
    try {
      const res = await axios.get(`${API}/streams/${id}`);
      setStream(res.data);
    } catch (e) {
      toast.error('Failed to load stream');
      navigate('/live');
    }
  };

  const fetchComments = async () => {
    try {
      const res = await axios.get(`${API}/comments/${id}`);
      setComments(res.data.reverse());
    } catch (e) { /* noop */ }
  };

  const fetchTiersAndWallet = async () => {
    try {
      const [t, w] = await Promise.all([
        axios.get(`${API}/gifts/tiers`),
        axios.get(`${API}/gifts/wallet`),
      ]);
      setTiers(t.data.tiers || []);
      setWallet(w.data.wallet || {});
    } catch (e) { /* noop */ }
  };

  const handleJoinStream = async () => {
    try {
      await axios.post(`${API}/streams/${id}/join`);
      setHasJoined(true);
      toast.success('Joined stream');
      fetchStream();
      // Start server-side heartbeat every 60s — server accumulates watch minutes
      // and auto-qualifies the view when threshold (30min) is reached.
      heartbeatRef.current = setInterval(async () => {
        try {
          const r = await axios.post(`${API}/streams/${id}/heartbeat`);
          setWatchMinutes(r.data.minutes || 0);
          if (r.data.qualified && !qualified) {
            setQualified(true);
            toast.success('Watch time qualified — streamer earns $0.005 on your view');
          }
        } catch (e) { /* noop */ }
      }, 60 * 1000);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to join stream');
    }
  };

  const toggleFollow = async () => {
    if (!stream?.streamer_id) return;
    try {
      const endpoint = followStatus.following ? 'unfollow' : 'follow';
      const r = await axios.post(`${API}/streamers/${stream.streamer_id}/${endpoint}`);
      setFollowStatus({ following: r.data.following, followers_count: followStatus.followers_count + (r.data.following ? 1 : -1) });
      toast.success(r.data.following ? `Following ${stream.streamer_name}` : `Unfollowed`);
    } catch (e) { toast.error('Failed'); }
  };

  const handleSendComment = async (e) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    try {
      await axios.post(`${API}/comments`, { stream_id: id, text: newComment });
      setNewComment('');
      fetchComments();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send comment');
    }
  };

  const handleSendGift = async (tierId) => {
    const tier = tiers.find((t) => t.id === tierId);
    const balance = wallet[tierId] || 0;
    if (balance < 1) {
      toast.error(`No ${tier?.emoji} ${tier?.name} units. Buy a bundle from Profile.`);
      return;
    }
    try {
      const res = await axios.post(`${API}/gifts/send`, { stream_id: id, tier_id: tierId, quantity: 1 });
      setWallet((w) => ({ ...w, [tierId]: (w[tierId] || 0) - 1 }));
      toast.success(`Sent ${tier.emoji} ${tier.name}! Streamer earned $${res.data.streamer_earned.toFixed(3)}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send gift');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen bg-[#05070F]"><div className="spinner"></div></div>;
  }
  if (!stream) return null;

  return (
    <div className="min-h-screen bg-[#05070F] text-white">
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <Button data-testid="back-to-live-btn" onClick={() => navigate('/live')} variant="ghost" className="text-white hover:text-cyan-400">
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <Logo size="md" />
          </div>
          {stream.is_live && (
            <div className="bg-red-500 px-4 py-2 rounded-full flex items-center live-pulse">
              <span className="w-2 h-2 bg-white rounded-full mr-2 animate-pulse"></span>
              <span className="font-semibold">LIVE</span>
            </div>
          )}
        </div>
      </nav>

      <div className="pt-24 px-6 pb-12">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <div data-testid="stream-player" className="aspect-video bg-black rounded-xl overflow-hidden mb-6 relative">
                <video src={stream.video_url} controls autoPlay className="w-full h-full"
                  onError={(e) => { e.target.style.display = 'none'; }}>
                  Your browser does not support the video tag.
                </video>
                {!stream.video_url && (
                  <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-purple-500/20 to-pink-500/20">
                    <Radio className="w-20 h-20 text-white opacity-50" />
                  </div>
                )}
              </div>

              <div data-testid="stream-info" className="glass-panel rounded-xl p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h1 className="text-2xl font-bold mb-2">{stream.title}</h1>
                    <div className="flex items-center gap-3">
                      <p className="text-cyan-400 flex items-center"><Users className="w-4 h-4 mr-2" />{stream.streamer_name}</p>
                      <span className="text-xs text-gray-500">{followStatus.followers_count} followers</span>
                      {user?.id !== stream.streamer_id && (
                        <Button data-testid="follow-btn" onClick={toggleFollow} size="sm"
                          className={followStatus.following ? 'bg-white/10 hover:bg-white/20 text-white' : 'bg-fuchsia-500 hover:bg-fuchsia-600 text-white'}>
                          {followStatus.following ? 'Following' : '+ Follow'}
                        </Button>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    {stream.is_live && (
                      <div className="text-gray-400 text-sm mb-1 flex items-center justify-end">
                        <Users className="w-4 h-4 mr-1" />{stream.viewers_count} watching
                      </div>
                    )}
                    <div className="text-gray-400 text-sm">{stream.views.toLocaleString()} views</div>
                    {hasJoined && !qualified && <div className="text-cyan-400 text-xs mt-1">Watch: {watchMinutes} min</div>}
                    {qualified && <div className="text-green-400 text-xs mt-1">✓ Your view qualified</div>}
                  </div>
                </div>
                <p className="text-gray-300">{stream.description}</p>
              </div>

              {stream.is_live && !hasJoined && (
                <div className="mt-6">
                  <Button data-testid="join-stream-btn" onClick={handleJoinStream}
                    className="w-full bg-gradient-to-r from-cyan-400 to-fuchsia-500 hover:opacity-90 py-6 text-lg rounded-xl text-[#05070F] font-semibold">
                    Join Live Stream
                  </Button>
                </div>
              )}
            </div>

            <div className="lg:col-span-1">
              {/* Gift tiers grid */}
              <div data-testid="gift-section" className="glass-panel rounded-xl p-6 mb-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center justify-between">
                  <span className="flex items-center"><Wallet className="w-5 h-5 mr-2 text-fuchsia-400" />Send a Gift</span>
                  <Button size="sm" onClick={() => navigate('/profile')} className="bg-white/10 hover:bg-white/20 text-xs">Top up</Button>
                </h3>
                <div className="grid grid-cols-4 gap-2">
                  {tiers.map((t) => {
                    const bal = wallet[t.id] || 0;
                    return (
                      <button key={t.id} data-testid={`send-gift-${t.id}`} onClick={() => handleSendGift(t.id)}
                        disabled={bal < 1}
                        className={`p-3 rounded-lg border transition-all text-center ${bal > 0 ? 'border-fuchsia-500/40 hover:border-fuchsia-400 hover:bg-fuchsia-500/10' : 'border-white/10 opacity-50 cursor-not-allowed'}`}>
                        <div className="text-2xl">{t.emoji}</div>
                        <div className="text-[10px] text-gray-400 mt-1">{t.name}</div>
                        <div className="text-xs font-bold text-cyan-400">{bal}</div>
                      </button>
                    );
                  })}
                </div>
                <p className="text-[11px] text-gray-500 mt-3 text-center">Tap a gift to send 1 unit. Streamer earns from $0.002 / gift up to $3.000 / gift based on tier.</p>
              </div>

              {/* Chat */}
              <div data-testid="chat-section" className="glass-panel rounded-xl p-6 h-[500px] flex flex-col">
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                  <Send className="w-5 h-5 mr-2 text-cyan-400" />Live Chat
                </h3>
                <ScrollArea className="flex-1 mb-4 pr-4" ref={scrollRef}>
                  <div className="space-y-3">
                    {comments.length === 0 ? (
                      <p className="text-gray-500 text-sm text-center py-8">No messages yet.</p>
                    ) : comments.map((c) => (
                      <div key={c.id} data-testid={`comment-${c.id}`} className="chat-message bg-white/5 rounded-lg p-3">
                        <div className="flex items-start space-x-2">
                          <div className="w-8 h-8 bg-gradient-to-br from-cyan-400 to-fuchsia-400 rounded-full flex items-center justify-center text-sm font-semibold text-[#05070F]">
                            {c.user_name.charAt(0).toUpperCase()}
                          </div>
                          <div className="flex-1">
                            <div className="font-semibold text-sm text-cyan-400">{c.user_name}</div>
                            <div className="text-sm text-gray-300">{c.text}</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
                <form onSubmit={handleSendComment} className="flex space-x-2">
                  <Input data-testid="comment-input" value={newComment} onChange={(e) => setNewComment(e.target.value)}
                    placeholder="Type a message..." className="bg-white/5 border-white/10 text-white placeholder:text-gray-500" />
                  <Button data-testid="send-comment-btn" type="submit" className="bg-cyan-400 text-[#05070F] hover:bg-cyan-300">
                    <Send className="w-4 h-4" />
                  </Button>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StreamView;
