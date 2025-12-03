import { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Video, Play, Clock, LogOut, User as UserIcon, Radio } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const Browse = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  const [content, setContent] = useState([]);
  const [selectedType, setSelectedType] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchContent();
  }, [selectedType]);

  const fetchContent = async () => {
    try {
      const url = selectedType === 'all' ? `${API}/content` : `${API}/content?type=${selectedType}`;
      const response = await axios.get(url);
      setContent(response.data);
    } catch (error) {
      toast.error('Failed to load content');
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
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
            <Button data-testid="browse-btn" onClick={() => navigate('/browse')} variant="ghost" className="text-cyan-400">
              Browse
            </Button>
            <Button data-testid="live-btn" onClick={() => navigate('/live')} variant="ghost" className="text-white hover:text-cyan-400">
              <Radio className="w-4 h-4 mr-2" />
              Live
            </Button>
            {(user?.role === 'streamer' || user?.role === 'admin') && (
              <Button data-testid="streamer-dashboard-btn" onClick={() => navigate('/streamer')} variant="ghost" className="text-white hover:text-cyan-400">
                Dashboard
              </Button>
            )}
            {user?.role === 'admin' && (
              <Button data-testid="admin-dashboard-btn" onClick={() => navigate('/admin')} variant="ghost" className="text-white hover:text-cyan-400">
                Admin
              </Button>
            )}
            <Button data-testid="profile-btn" onClick={() => navigate('/profile')} variant="ghost" className="text-white hover:text-cyan-400">
              <UserIcon className="w-4 h-4 mr-2" />
              Profile
            </Button>
            <Button data-testid="logout-btn" onClick={logout} variant="ghost" className="text-white hover:text-red-400">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </nav>

      <div className="pt-24 px-6 pb-12">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-4">Browse Content</h1>
            <p className="text-gray-400">Discover movies, TV shows, and live sports</p>
          </div>

          {/* Filter Tabs */}
          <div data-testid="filter-tabs" className="flex space-x-4 mb-8">
            <Button
              data-testid="filter-all"
              onClick={() => setSelectedType('all')}
              className={`rounded-full px-6 ${
                selectedType === 'all'
                  ? 'bg-cyan-400 text-[#0A0E27]'
                  : 'bg-white/5 text-white hover:bg-white/10'
              }`}
            >
              All
            </Button>
            <Button
              data-testid="filter-movie"
              onClick={() => setSelectedType('movie')}
              className={`rounded-full px-6 ${
                selectedType === 'movie'
                  ? 'bg-cyan-400 text-[#0A0E27]'
                  : 'bg-white/5 text-white hover:bg-white/10'
              }`}
            >
              Movies
            </Button>
            <Button
              data-testid="filter-tv-show"
              onClick={() => setSelectedType('tv-show')}
              className={`rounded-full px-6 ${
                selectedType === 'tv-show'
                  ? 'bg-cyan-400 text-[#0A0E27]'
                  : 'bg-white/5 text-white hover:bg-white/10'
              }`}
            >
              TV Shows
            </Button>
            <Button
              data-testid="filter-sport"
              onClick={() => setSelectedType('sport')}
              className={`rounded-full px-6 ${
                selectedType === 'sport'
                  ? 'bg-cyan-400 text-[#0A0E27]'
                  : 'bg-white/5 text-white hover:bg-white/10'
              }`}
            >
              Sports
            </Button>
          </div>

          {/* Content Grid */}
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <div className="spinner"></div>
            </div>
          ) : content.length === 0 ? (
            <div data-testid="no-content" className="text-center py-20">
              <Video className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400 text-lg">No content available yet</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {content.map((item) => (
                <div
                  key={item.id}
                  data-testid={`content-card-${item.id}`}
                  className="video-card glass-effect rounded-xl overflow-hidden cursor-pointer group"
                  onClick={() => navigate(`/watch/${item.id}`)}
                >
                  <div className="relative aspect-video bg-gradient-to-br from-cyan-500/20 to-purple-500/20">
                    <img
                      src={item.thumbnail_url}
                      alt={item.title}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/50 transition-colors flex items-center justify-center">
                      <Play className="w-16 h-16 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <div className="absolute top-2 right-2 bg-cyan-400 text-[#0A0E27] px-2 py-1 rounded-full text-xs font-semibold uppercase">
                      {item.type}
                    </div>
                  </div>
                  <div className="p-4">
                    <h3 className="font-semibold text-lg mb-2 line-clamp-1">{item.title}</h3>
                    <p className="text-gray-400 text-sm mb-3 line-clamp-2">{item.description}</p>
                    <div className="flex items-center justify-between text-sm text-gray-500">
                      <div className="flex items-center">
                        <Clock className="w-4 h-4 mr-1" />
                        <span>{formatDuration(item.duration)}</span>
                      </div>
                      <div className="flex items-center">
                        <Play className="w-4 h-4 mr-1" />
                        <span>{item.views.toLocaleString()} views</span>
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

export default Browse;
