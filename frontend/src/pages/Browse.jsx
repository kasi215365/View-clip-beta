import { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Video, Play, Clock, LogOut, User as UserIcon, Radio, Megaphone, Search as SearchIcon, TrendingUp, Trophy } from 'lucide-react';
import Logo from '@/components/Logo';
import NotificationBell from '@/components/NotificationBell';
import { Input } from '@/components/ui/input';
import axios from 'axios';
import { toast } from 'sonner';

const Browse = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  const [content, setContent] = useState([]);
  const [promos, setPromos] = useState([]);
  const [trending, setTrending] = useState({ content: [], live_streams: [] });
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [selectedType, setSelectedType] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchContent();
    fetchPromos();
    fetchTrending();
  }, [selectedType]);

  useEffect(() => {
    if (query.trim().length < 2) { setSearchResults(null); return; }
    const t = setTimeout(async () => {
      try {
        const r = await axios.get(`${API}/search`, { params: { q: query } });
        setSearchResults(r.data);
      } catch (e) { /* noop */ }
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  const fetchTrending = async () => {
    try { const r = await axios.get(`${API}/trending`); setTrending(r.data); } catch (e) { /* noop */ }
  };

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

  const fetchPromos = async () => {
    try {
      const r = await axios.get(`${API}/promos`);
      setPromos(r.data || []);
    } catch (e) { /* noop */ }
  };

  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
  };

  // Inject a promo every 5 content cards
  const feed = [];
  content.forEach((c, i) => {
    feed.push({ kind: 'content', item: c });
    if ((i + 1) % 5 === 0 && promos.length > 0) {
      feed.push({ kind: 'promo', item: promos[(i / 5) % promos.length] });
    }
  });

  return (
    <div className="min-h-screen bg-[#05070F] text-white">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Logo size="md" />
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
            <Button data-testid="leaderboard-nav-btn" onClick={() => navigate('/leaderboard')} variant="ghost" className="text-white hover:text-cyan-400">
              <Trophy className="w-4 h-4 mr-2" />Top 50
            </Button>
            <NotificationBell />
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
            <p className="text-gray-400 mb-6">Discover movies, TV shows, and live sports</p>
            <div className="relative max-w-xl">
              <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input
                data-testid="search-input"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search movies, TV, streams, streamers…"
                className="w-full pl-12 py-4 bg-white/5 border border-white/10 rounded-lg text-white text-base focus:outline-none focus:border-cyan-400/60"
              />
            </div>
          </div>

          {searchResults && (
            <div data-testid="search-results" className="mb-8 glass-panel rounded-xl p-6">
              <h2 className="text-xl font-bold mb-4">Results for "{searchResults.query}"</h2>
              {searchResults.content.length === 0 && searchResults.streams.length === 0 && searchResults.streamers.length === 0 ? (
                <p className="text-gray-500">No results found.</p>
              ) : (
                <div className="space-y-4">
                  {searchResults.content.length > 0 && (
                    <div>
                      <div className="text-xs text-gray-500 uppercase mb-2">Content ({searchResults.content.length})</div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {searchResults.content.map((c) => (
                          <div key={c.id} data-testid={`search-content-${c.id}`} onClick={() => navigate(`/watch/${c.id}`)} className="bg-white/5 hover:bg-white/10 rounded p-2 cursor-pointer">
                            <div className="text-sm font-semibold truncate">{c.title}</div>
                            <div className="text-xs text-gray-500">{c.type}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {searchResults.streams.length > 0 && (
                    <div>
                      <div className="text-xs text-gray-500 uppercase mb-2">Streams ({searchResults.streams.length})</div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {searchResults.streams.map((s) => (
                          <div key={s.id} data-testid={`search-stream-${s.id}`} onClick={() => navigate(`/stream/${s.id}`)} className="bg-white/5 hover:bg-white/10 rounded p-2 cursor-pointer">
                            <div className="text-sm font-semibold truncate">{s.title}</div>
                            <div className="text-xs text-gray-500">by {s.streamer_name}{s.is_live && <span className="ml-2 text-red-400">● LIVE</span>}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {searchResults.streamers.length > 0 && (
                    <div>
                      <div className="text-xs text-gray-500 uppercase mb-2">Streamers ({searchResults.streamers.length})</div>
                      <div className="flex flex-wrap gap-2">
                        {searchResults.streamers.map((u) => (
                          <span key={u.id} data-testid={`search-streamer-${u.id}`} className="bg-cyan-400/10 text-cyan-400 px-3 py-1 rounded-full text-sm">{u.name}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {!searchResults && trending.content.length > 0 && (
            <div data-testid="trending-strip" className="mb-8">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="w-5 h-5 text-fuchsia-400" />
                <h2 className="text-xl font-bold">Trending Now</h2>
              </div>
              <div className="flex gap-4 overflow-x-auto pb-4">
                {trending.content.slice(0, 8).map((c) => (
                  <div key={c.id} data-testid={`trending-${c.id}`} onClick={() => navigate(`/watch/${c.id}`)} className="flex-shrink-0 w-48 glass-panel rounded-lg overflow-hidden cursor-pointer hover:border-fuchsia-400/50">
                    <div className="aspect-video bg-gradient-to-br from-fuchsia-500/20 to-cyan-500/20">
                      <img src={c.thumbnail_url} alt="" className="w-full h-full object-cover" onError={(e) => e.target.style.display = 'none'} />
                    </div>
                    <div className="p-2">
                      <div className="text-sm font-semibold truncate">{c.title}</div>
                      <div className="text-xs text-gray-500">{c.views.toLocaleString()} views</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Filter Tabs */}
          <div data-testid="filter-tabs" className="flex space-x-4 mb-8">
            <Button
              data-testid="filter-all"
              onClick={() => setSelectedType('all')}
              className={`rounded-full px-6 ${selectedType === 'all' ? 'bg-cyan-400 text-[#05070F]' : 'bg-white/5 text-white hover:bg-white/10'}`}
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
              {feed.map((entry, idx) => {
                const item = entry.item;
                if (entry.kind === 'promo') {
                  return (
                    <div key={`promo-${item.id}-${idx}`} data-testid={`promo-card-${item.id}`} className="video-card glass-panel rounded-xl overflow-hidden cursor-pointer group border-2 border-fuchsia-500/40">
                      <div className="relative aspect-video bg-gradient-to-br from-fuchsia-500/20 to-cyan-500/20">
                        <img src={item.thumbnail_url} alt={item.title} className="w-full h-full object-cover" onError={(e) => e.target.style.display = 'none'} />
                        <div className="absolute top-2 left-2 bg-fuchsia-500 text-white px-2 py-1 rounded-full text-xs font-semibold flex items-center"><Megaphone className="w-3 h-3 mr-1" />PROMO</div>
                      </div>
                      <div className="p-4">
                        <h3 className="font-semibold text-lg mb-1 line-clamp-1">{item.title}</h3>
                        <p className="text-gray-400 text-sm line-clamp-2">{item.description}</p>
                      </div>
                    </div>
                  );
                }
                return (
                  <div key={item.id} data-testid={`content-card-${item.id}`} className="video-card glass-panel rounded-xl overflow-hidden cursor-pointer group" onClick={() => navigate(`/watch/${item.id}`)}>
                    <div className="relative aspect-video bg-gradient-to-br from-cyan-500/20 to-fuchsia-500/20">
                      <img src={item.thumbnail_url} alt={item.title} className="w-full h-full object-cover" onError={(e) => { e.target.style.display = 'none'; }} />
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/50 transition-colors flex items-center justify-center">
                        <Play className="w-16 h-16 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                      <div className="absolute top-2 right-2 bg-cyan-400 text-[#05070F] px-2 py-1 rounded-full text-xs font-semibold uppercase">{item.type}</div>
                    </div>
                    <div className="p-4">
                      <h3 className="font-semibold text-lg mb-2 line-clamp-1">{item.title}</h3>
                      <p className="text-gray-400 text-sm mb-3 line-clamp-2">{item.description}</p>
                      <div className="flex items-center justify-between text-sm text-gray-500">
                        <div className="flex items-center"><Clock className="w-4 h-4 mr-1" /><span>{formatDuration(item.duration)}</span></div>
                        <div className="flex items-center"><Play className="w-4 h-4 mr-1" /><span>{item.views.toLocaleString()} views</span></div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Browse;
