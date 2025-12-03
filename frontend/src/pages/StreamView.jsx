import { useState, useEffect, useContext, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Video, ArrowLeft, Radio, Users, Send, Gift as GiftIcon } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const StreamView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const [stream, setStream] = useState(null);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [giftAmount, setGiftAmount] = useState(1);
  const [loading, setLoading] = useState(true);
  const [hasJoined, setHasJoined] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    fetchStream();
    fetchComments();
    const interval = setInterval(fetchComments, 5000); // Poll comments every 5s
    return () => clearInterval(interval);
  }, [id]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [comments]);

  const fetchStream = async () => {
    try {
      const response = await axios.get(`${API}/streams/${id}`);
      setStream(response.data);
    } catch (error) {
      toast.error('Failed to load stream');
      navigate('/live');
    } finally {
      setLoading(false);
    }
  };

  const fetchComments = async () => {
    try {
      const response = await axios.get(`${API}/comments/${id}`);
      setComments(response.data.reverse());
    } catch (error) {
      console.error('Failed to fetch comments');
    }
  };

  const handleJoinStream = async () => {
    try {
      await axios.post(`${API}/streams/${id}/join`);
      setHasJoined(true);
      toast.success('Joined stream!');
      fetchStream();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to join stream');
    }
  };

  const handleSendComment = async (e) => {
    e.preventDefault();
    if (!newComment.trim()) return;

    try {
      await axios.post(`${API}/comments`, {
        stream_id: id,
        text: newComment
      });
      setNewComment('');
      fetchComments();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send comment');
    }
  };

  const handleSendGift = async () => {
    if (giftAmount < 1) {
      toast.error('Gift amount must be at least 1');
      return;
    }

    try {
      await axios.post(`${API}/gifts`, {
        stream_id: id,
        amount: giftAmount
      });
      toast.success(`Sent gift of $${giftAmount}!`);
      setGiftAmount(1);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send gift');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#0A0E27]">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!stream) return null;

  return (
    <div className="min-h-screen bg-[#0A0E27] text-white">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <Button data-testid="back-to-live-btn" onClick={() => navigate('/live')} variant="ghost" className="text-white hover:text-cyan-400">
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div className="flex items-center space-x-2">
              <Video className="w-8 h-8 text-cyan-400" />
              <h1 className="text-2xl font-bold">StreamHub</h1>
            </div>
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
            {/* Video Player and Info */}
            <div className="lg:col-span-2">
              {/* Video Player */}
              <div data-testid="stream-player" className="aspect-video bg-black rounded-xl overflow-hidden mb-6 relative">
                <video
                  src={stream.video_url}
                  controls
                  autoPlay
                  className="w-full h-full"
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                >
                  Your browser does not support the video tag.
                </video>
                {!stream.video_url && (
                  <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-purple-500/20 to-pink-500/20">
                    <Radio className="w-20 h-20 text-white opacity-50" />
                  </div>
                )}
              </div>

              {/* Stream Info */}
              <div data-testid="stream-info" className="glass-effect rounded-xl p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h1 className="text-2xl font-bold mb-2">{stream.title}</h1>
                    <p className="text-cyan-400 flex items-center">
                      <Users className="w-4 h-4 mr-2" />
                      {stream.streamer_name}
                    </p>
                  </div>
                  <div className="text-right">
                    {stream.is_live && (
                      <div className="text-gray-400 text-sm mb-1 flex items-center justify-end">
                        <Users className="w-4 h-4 mr-1" />
                        {stream.viewers_count} watching
                      </div>
                    )}
                    <div className="text-gray-400 text-sm">
                      {stream.views.toLocaleString()} total views
                    </div>
                  </div>
                </div>
                <p className="text-gray-300">{stream.description}</p>
              </div>

              {/* Join Button */}
              {stream.is_live && !hasJoined && (
                <div className="mt-6">
                  <Button
                    data-testid="join-stream-btn"
                    onClick={handleJoinStream}
                    className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:opacity-90 py-6 text-lg rounded-xl"
                  >
                    Join Live Stream
                  </Button>
                </div>
              )}
            </div>

            {/* Chat and Gifts */}
            <div className="lg:col-span-1">
              {/* Gifts Section */}
              <div data-testid="gift-section" className="glass-effect rounded-xl p-6 mb-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                  <GiftIcon className="w-5 h-5 mr-2 text-pink-400" />
                  Send a Gift
                </h3>
                <div className="flex items-center space-x-3">
                  <Input
                    data-testid="gift-amount-input"
                    type="number"
                    min="1"
                    value={giftAmount}
                    onChange={(e) => setGiftAmount(Number(e.target.value))}
                    className="bg-white/5 border-white/10 text-white"
                    placeholder="Amount"
                  />
                  <Button
                    data-testid="send-gift-btn"
                    onClick={handleSendGift}
                    className="bg-gradient-to-r from-purple-600 to-pink-600 hover:opacity-90 whitespace-nowrap"
                  >
                    Send ${giftAmount}
                  </Button>
                </div>
                <p className="text-xs text-gray-500 mt-3">
                  Streamer earns $0.002 per gift
                </p>
              </div>

              {/* Chat Section */}
              <div data-testid="chat-section" className="glass-effect rounded-xl p-6 h-[500px] flex flex-col">
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                  <Send className="w-5 h-5 mr-2 text-cyan-400" />
                  Live Chat
                </h3>

                {/* Messages */}
                <ScrollArea className="flex-1 mb-4 pr-4" ref={scrollRef}>
                  <div className="space-y-3">
                    {comments.length === 0 ? (
                      <p className="text-gray-500 text-sm text-center py-8">No messages yet. Be the first to comment!</p>
                    ) : (
                      comments.map((comment) => (
                        <div key={comment.id} data-testid={`comment-${comment.id}`} className="chat-message bg-white/5 rounded-lg p-3">
                          <div className="flex items-start space-x-2">
                            <div className="w-8 h-8 bg-gradient-to-br from-cyan-400 to-purple-400 rounded-full flex items-center justify-center text-sm font-semibold">
                              {comment.user_name.charAt(0).toUpperCase()}
                            </div>
                            <div className="flex-1">
                              <div className="font-semibold text-sm text-cyan-400">{comment.user_name}</div>
                              <div className="text-sm text-gray-300">{comment.text}</div>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </ScrollArea>

                {/* Comment Input */}
                <form onSubmit={handleSendComment} className="flex space-x-2">
                  <Input
                    data-testid="comment-input"
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder="Type a message..."
                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500"
                  />
                  <Button data-testid="send-comment-btn" type="submit" className="bg-cyan-400 text-[#0A0E27] hover:bg-cyan-500">
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
