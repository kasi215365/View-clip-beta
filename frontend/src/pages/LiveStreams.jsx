import { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Video, Radio, Users, Eye, LogOut, User as UserIcon, Home } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const LiveStreams = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  const [streams, setStreams] = useState([]);
  const [filter, setFilter] = useState('live');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStreams();
  }, [filter]);

  const fetchStreams = async () => {
    try {
      const url = filter === 'all' 
        ? `${API}/streams` 
        : `${API}/streams?is_live=${filter === 'live'}`;
      const response = await axios.get(url);
      setStreams(response.data);
    } catch (error) {
      toast.error('Failed to load streams');
    } finally {
      setLoading(false);
    }
  };

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
            <Button data-testid="live-nav-btn" onClick={() => navigate('/live')} variant="ghost" className="text-cyan-400">
              <Radio className="w-4 h-4 mr-2" />
              Live
            </Button>
            {(user?.role === 'streamer' || user?.role === 'admin') && (
              <Button data-testid="streamer-nav-btn" onClick={() => navigate('/streamer')} variant="ghost" className="text-white hover:text-cyan-400">
                Dashboard
              </Button>
            )}
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
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-4 flex items-center">
              <Radio className="w-10 h-10 mr-3 text-cyan-400 live-pulse" />
              Live Streams
            </h1>
            <p className="text-gray-400">Watch and interact with live streamers</p>
          </div>

          {/* Filter Tabs */}
          <div data-testid="stream-filter-tabs" className="flex space-x-4 mb-8">
            <Button
              data-testid="filter-live-btn"
              onClick={() => setFilter('live')}
              className={`rounded-full px-6 ${
                filter === 'live'
                  ? 'bg-red-500 text-white'
                  : 'bg-white/5 text-white hover:bg-white/10'
              }`}
            >
              <Radio className="w-4 h-4 mr-2" />
              Live Now
            </Button>
            <Button
              data-testid="filter-past-btn"
              onClick={() => setFilter('past')}
              className={`rounded-full px-6 ${
                filter === 'past'
                  ? 'bg-cyan-400 text-[#0A0E27]'
                  : 'bg-white/5 text-white hover:bg-white/10'
              }`}
            >
              Past Streams
            </Button>
            <Button
              data-testid="filter-all-btn"
              onClick={() => setFilter('all')}
              className={`rounded-full px-6 ${
                filter === 'all'
                  ? 'bg-cyan-400 text-[#0A0E27]'
                  : 'bg-white/5 text-white hover:bg-white/10'
              }`}
            >
              All
            </Button>
          </div>

          {/* Streams Grid */}
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <div className="spinner"></div>
            </div>
          ) : streams.length === 0 ? (
            <div data-testid="no-streams" className="text-center py-20">
              <Radio className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400 text-lg">No streams available</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {streams.map((stream) => (
                <div
                  key={stream.id}
                  data-testid={`stream-card-${stream.id}`}
                  className="video-card glass-effect rounded-xl overflow-hidden cursor-pointer group"
                  onClick={() => navigate(`/stream/${stream.id}`)}
                >
                  <div className="relative aspect-video bg-gradient-to-br from-purple-500/20 to-pink-500/20">
                    <img
                      src={stream.thumbnail_url}
                      alt={stream.title}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/50 transition-colors flex items-center justify-center">
                      <Radio className="w-16 h-16 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    {stream.is_live && (
                      <div className="absolute top-2 left-2 bg-red-500 text-white px-3 py-1 rounded-full text-xs font-semibold flex items-center live-pulse">
                        <span className="w-2 h-2 bg-white rounded-full mr-2 animate-pulse"></span>
                        LIVE
                      </div>
                    )}
                    {stream.saved && (
                      <div className="absolute top-2 right-2 bg-purple-500 text-white px-2 py-1 rounded-full text-xs font-semibold">
                        SAVED
                      </div>
                    )}
                    {stream.is_live && (
                      <div className="absolute bottom-2 right-2 bg-black/70 px-2 py-1 rounded-full text-xs flex items-center">
                        <Eye className="w-3 h-3 mr-1" />
                        {stream.viewers_count}
                      </div>
                    )}
                  </div>
                  <div className="p-4">
                    <h3 className="font-semibold text-lg mb-2 line-clamp-1">{stream.title}</h3>
                    <p className="text-gray-400 text-sm mb-3 line-clamp-2">{stream.description}</p>
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center text-cyan-400">
                        <Users className="w-4 h-4 mr-1" />
                        <span>{stream.streamer_name}</span>
                      </div>
                      <div className="text-gray-500">
                        {stream.views.toLocaleString()} views
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LiveStreams;
