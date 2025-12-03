import { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Video, Radio, DollarSign, Eye, Gift, TrendingUp, LogOut, User as UserIcon, Home, Save } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const StreamerDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  const [myStreams, setMyStreams] = useState([]);
  const [earnings, setEarnings] = useState([]);
  const [totalEarnings, setTotalEarnings] = useState(0);
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newStream, setNewStream] = useState({
    title: '',
    description: '',
    video_url: '',
    thumbnail_url: ''
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [streamsRes, earningsRes, totalRes] = await Promise.all([
        axios.get(`${API}/streams`),
        axios.get(`${API}/earnings`),
        axios.get(`${API}/earnings/total`)
      ]);

      const userStreams = streamsRes.data.filter(s => s.streamer_id === user.id);
      setMyStreams(userStreams);
      setEarnings(earningsRes.data);
      setTotalEarnings(totalRes.data.total_earnings);
    } catch (error) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateStream = async (e) => {
    e.preventDefault();

    try {
      await axios.post(`${API}/streams`, newStream);
      toast.success('Stream created! Go live now!');
      setIsDialogOpen(false);
      setNewStream({ title: '', description: '', video_url: '', thumbnail_url: '' });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create stream');
    }
  };

  const handleEndStream = async (streamId) => {
    try {
      const response = await axios.post(`${API}/streams/${streamId}/end`);
      toast.success(`Stream ended! Earned $${response.data.earnings.toFixed(2)}`);
      fetchData();
    } catch (error) {
      toast.error('Failed to end stream');
    }
  };

  const handleSaveStream = async (streamId) => {
    try {
      await axios.post(`${API}/streams/${streamId}/save`);
      toast.success('Stream saved! You can now export it.');
      fetchData();
    } catch (error) {
      toast.error('Failed to save stream');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#0A0E27]">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0E27] text-white">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <Video className="w-8 h-8 text-cyan-400" />
            <h1 className="text-2xl font-bold">StreamHub</h1>
          </div>
          <div className="flex items-center space-x-4">
            <Button data-testid="browse-nav-btn" onClick={() => navigate('/browse')} variant="ghost" className="text-white hover:text-cyan-400">
              <Home className="w-4 h-4 mr-2" />
              Browse
            </Button>
            <Button data-testid="live-nav-btn" onClick={() => navigate('/live')} variant="ghost" className="text-white hover:text-cyan-400">
              <Radio className="w-4 h-4 mr-2" />
              Live
            </Button>
            <Button data-testid="dashboard-nav-btn" onClick={() => navigate('/streamer')} variant="ghost" className="text-cyan-400">
              Dashboard
            </Button>
            <Button data-testid="profile-nav-btn" onClick={() => navigate('/profile')} variant="ghost" className="text-white hover:text-cyan-400">
              <UserIcon className="w-4 h-4 mr-2" />
              Profile
            </Button>
            <Button data-testid="logout-nav-btn" onClick={logout} variant="ghost" className="text-white hover:text-red-400">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </nav>

      <div className="pt-24 px-6 pb-12">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-4xl font-bold mb-2">Streamer Dashboard</h1>
              <p className="text-gray-400">Manage your streams and track your earnings</p>
            </div>
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button data-testid="start-stream-btn" className="bg-gradient-to-r from-purple-600 to-pink-600 hover:opacity-90 px-8 py-6 text-lg rounded-xl">
                  <Radio className="w-5 h-5 mr-2" />
                  Start New Stream
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-[#0D1234] border-white/10 text-white">
                <DialogHeader>
                  <DialogTitle className="text-2xl">Create New Stream</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleCreateStream} className="space-y-4 mt-4">
                  <div>
                    <Label htmlFor="title">Title</Label>
                    <Input
                      data-testid="stream-title-input"
                      id="title"
                      value={newStream.title}
                      onChange={(e) => setNewStream({ ...newStream, title: e.target.value })}
                      required
                      className="bg-white/5 border-white/10 text-white mt-2"
                      placeholder="My Awesome Stream"
                    />
                  </div>
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      data-testid="stream-description-input"
                      id="description"
                      value={newStream.description}
                      onChange={(e) => setNewStream({ ...newStream, description: e.target.value })}
                      required
                      className="bg-white/5 border-white/10 text-white mt-2"
                      placeholder="Tell viewers what your stream is about"
                      rows={3}
                    />
                  </div>
                  <div>
                    <Label htmlFor="video-url">Video URL</Label>
                    <Input
                      data-testid="stream-video-input"
                      id="video-url"
                      value={newStream.video_url}
                      onChange={(e) => setNewStream({ ...newStream, video_url: e.target.value })}
                      required
                      className="bg-white/5 border-white/10 text-white mt-2"
                      placeholder="https://example.com/video.mp4"
                    />
                  </div>
                  <div>
                    <Label htmlFor="thumbnail-url">Thumbnail URL</Label>
                    <Input
                      data-testid="stream-thumbnail-input"
                      id="thumbnail-url"
                      value={newStream.thumbnail_url}
                      onChange={(e) => setNewStream({ ...newStream, thumbnail_url: e.target.value })}
                      required
                      className="bg-white/5 border-white/10 text-white mt-2"
                      placeholder="https://example.com/thumbnail.jpg"
                    />
                  </div>
                  <Button data-testid="create-stream-submit-btn" type="submit" className="w-full bg-cyan-400 text-[#0A0E27] hover:bg-cyan-500 py-6 rounded-xl">
                    Go Live
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          {/* Stats Cards */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <div data-testid="total-earnings-card" className="glass-effect rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <DollarSign className="w-10 h-10 text-green-400" />
                <div className="bg-green-400/20 px-3 py-1 rounded-full text-green-400 text-sm font-semibold">
                  Total
                </div>
              </div>
              <h3 className="text-3xl font-bold mb-1">${totalEarnings.toFixed(2)}</h3>
              <p className="text-gray-400 text-sm">Total Earnings</p>
            </div>
            <div data-testid="total-streams-card" className="glass-effect rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <Radio className="w-10 h-10 text-purple-400" />
                <div className="bg-purple-400/20 px-3 py-1 rounded-full text-purple-400 text-sm font-semibold">
                  Streams
                </div>
              </div>
              <h3 className="text-3xl font-bold mb-1">{myStreams.length}</h3>
              <p className="text-gray-400 text-sm">Total Streams</p>
            </div>
            <div data-testid="total-views-card" className="glass-effect rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <Eye className="w-10 h-10 text-cyan-400" />
                <div className="bg-cyan-400/20 px-3 py-1 rounded-full text-cyan-400 text-sm font-semibold">
                  Views
                </div>
              </div>
              <h3 className="text-3xl font-bold mb-1">
                {myStreams.reduce((sum, s) => sum + s.views, 0).toLocaleString()}
              </h3>
              <p className="text-gray-400 text-sm">Total Views</p>
            </div>
          </div>

          {/* My Streams */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold mb-6">My Streams</h2>
            {myStreams.length === 0 ? (
              <div data-testid="no-streams-message" className="glass-effect rounded-xl p-12 text-center">
                <Radio className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400 text-lg mb-4">You haven't created any streams yet</p>
                <Button onClick={() => setIsDialogOpen(true)} className="bg-cyan-400 text-[#0A0E27] hover:bg-cyan-500">
                  Start Your First Stream
                </Button>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {myStreams.map((stream) => (
                  <div key={stream.id} data-testid={`my-stream-${stream.id}`} className="glass-effect rounded-xl overflow-hidden">
                    <div className="relative aspect-video bg-gradient-to-br from-purple-500/20 to-pink-500/20">
                      <img
                        src={stream.thumbnail_url}
                        alt={stream.title}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          e.target.style.display = 'none';
                        }}
                      />
                      {stream.is_live && (
                        <div className="absolute top-2 left-2 bg-red-500 text-white px-3 py-1 rounded-full text-xs font-semibold flex items-center live-pulse">
                          <span className="w-2 h-2 bg-white rounded-full mr-2 animate-pulse"></span>
                          LIVE
                        </div>
                      )}
                      {stream.saved && (
                        <div className="absolute top-2 right-2 bg-green-500 text-white px-2 py-1 rounded-full text-xs font-semibold flex items-center">
                          <Save className="w-3 h-3 mr-1" />
                          SAVED
                        </div>
                      )}
                    </div>
                    <div className="p-4">
                      <h3 className="font-semibold text-lg mb-2 line-clamp-1">{stream.title}</h3>
                      <div className="flex items-center justify-between text-sm text-gray-400 mb-4">
                        <div className="flex items-center">
                          <Eye className="w-4 h-4 mr-1" />
                          {stream.views} views
                        </div>
                        {stream.is_live && (
                          <div>
                            {stream.viewers_count} watching
                          </div>
                        )}
                      </div>
                      <div className="flex space-x-2">
                        {stream.is_live && (
                          <Button
                            data-testid={`end-stream-btn-${stream.id}`}
                            onClick={() => handleEndStream(stream.id)}
                            className="flex-1 bg-red-500 hover:bg-red-600 text-white rounded-lg"
                          >
                            End Stream
                          </Button>
                        )}
                        {!stream.is_live && !stream.saved && (
                          <Button
                            data-testid={`save-stream-btn-${stream.id}`}
                            onClick={() => handleSaveStream(stream.id)}
                            className="flex-1 bg-purple-600 hover:bg-purple-700 text-white rounded-lg"
                          >
                            <Save className="w-4 h-4 mr-2" />
                            Save
                          </Button>
                        )}
                        <Button
                          data-testid={`view-stream-btn-${stream.id}`}
                          onClick={() => navigate(`/stream/${stream.id}`)}
                          className="flex-1 bg-cyan-400 text-[#0A0E27] hover:bg-cyan-500 rounded-lg"
                        >
                          View
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Earnings */}
          <div>
            <h2 className="text-2xl font-bold mb-6">Recent Earnings</h2>
            {earnings.length === 0 ? (
              <div data-testid="no-earnings-message" className="glass-effect rounded-xl p-8 text-center">
                <DollarSign className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400">No earnings yet. Start streaming to earn!</p>
              </div>
            ) : (
              <div className="glass-effect rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-white/5">
                      <tr>
                        <th className="text-left p-4 font-semibold">Date</th>
                        <th className="text-left p-4 font-semibold">Source</th>
                        <th className="text-left p-4 font-semibold">Description</th>
                        <th className="text-right p-4 font-semibold">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {earnings.slice(0, 10).map((earning) => (
                        <tr key={earning.id} data-testid={`earning-${earning.id}`} className="border-t border-white/5 hover:bg-white/5">
                          <td className="p-4 text-sm text-gray-400">
                            {new Date(earning.created_at).toLocaleDateString()}
                          </td>
                          <td className="p-4">
                            <div className="flex items-center">
                              {earning.source === 'views' ? (
                                <Eye className="w-4 h-4 mr-2 text-cyan-400" />
                              ) : (
                                <Gift className="w-4 h-4 mr-2 text-pink-400" />
                              )}
                              <span className="capitalize">{earning.source}</span>
                            </div>
                          </td>
                          <td className="p-4 text-sm text-gray-400">{earning.description}</td>
                          <td className="p-4 text-right font-semibold text-green-400">
                            +${earning.amount.toFixed(3)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StreamerDashboard;
