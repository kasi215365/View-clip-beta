import { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Video, Upload, LogOut, User as UserIcon, Home, Radio } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const AdminDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  const [content, setContent] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newContent, setNewContent] = useState({
    title: '',
    description: '',
    type: 'movie',
    video_url: '',
    thumbnail_url: '',
    duration: 0
  });

  useEffect(() => {
    fetchContent();
  }, []);

  const fetchContent = async () => {
    try {
      const response = await axios.get(`${API}/content`);
      setContent(response.data);
    } catch (error) {
      toast.error('Failed to load content');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await axios.post(`${API}/content`, newContent);
      toast.success('Content uploaded successfully!');
      setNewContent({
        title: '',
        description: '',
        type: 'movie',
        video_url: '',
        thumbnail_url: '',
        duration: 0
      });
      fetchContent();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload content');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadSampleData = async () => {
    setLoading(true);
    const sampleContent = [
      {
        title: 'Epic Adventure Movie',
        description: 'An incredible journey through uncharted territories with stunning visuals and an engaging storyline.',
        type: 'movie',
        video_url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
        thumbnail_url: 'https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=800',
        duration: 7200
      },
      {
        title: 'Mystery Series S01E01',
        description: 'The first episode of an exciting mystery series that will keep you on the edge of your seat.',
        type: 'tv-show',
        video_url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
        thumbnail_url: 'https://images.unsplash.com/photo-1598899134739-24c46f58b8c0?w=800',
        duration: 3600
      },
      {
        title: 'Championship Finals Live',
        description: 'Watch the most anticipated championship finals with live commentary and expert analysis.',
        type: 'sport',
        video_url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
        thumbnail_url: 'https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=800',
        duration: 5400
      },
      {
        title: 'Sci-Fi Blockbuster',
        description: 'A groundbreaking sci-fi film with cutting-edge special effects and a mind-bending plot.',
        type: 'movie',
        video_url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
        thumbnail_url: 'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800',
        duration: 8100
      },
      {
        title: 'Comedy Show Special',
        description: 'Hilarious stand-up comedy special featuring top comedians from around the world.',
        type: 'tv-show',
        video_url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4',
        thumbnail_url: 'https://images.unsplash.com/photo-1527224857830-43a7acc85260?w=800',
        duration: 2700
      },
      {
        title: 'Soccer World Cup Highlights',
        description: 'Relive the best moments from the World Cup with extended highlights and interviews.',
        type: 'sport',
        video_url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4',
        thumbnail_url: 'https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=800',
        duration: 4500
      }
    ];

    try {
      for (const item of sampleContent) {
        await axios.post(`${API}/content`, item);
      }
      toast.success('Sample content loaded successfully!');
      fetchContent();
    } catch (error) {
      toast.error('Failed to load sample content');
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
            <Button data-testid="live-nav-btn" onClick={() => navigate('/live')} variant="ghost" className="text-white hover:text-cyan-400">
              <Radio className="w-4 h-4 mr-2" />
              Live
            </Button>
            <Button data-testid="streamer-nav-btn" onClick={() => navigate('/streamer')} variant="ghost" className="text-white hover:text-cyan-400">
              Dashboard
            </Button>
            <Button data-testid="admin-nav-btn" onClick={() => navigate('/admin')} variant="ghost" className="text-cyan-400">
              Admin
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
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2">Admin Dashboard</h1>
            <p className="text-gray-400">Upload and manage platform content</p>
          </div>

          <div className="grid lg:grid-cols-2 gap-8">
            {/* Upload Form */}
            <div data-testid="upload-form" className="glass-effect rounded-xl p-8">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold flex items-center">
                  <Upload className="w-6 h-6 mr-3 text-cyan-400" />
                  Upload Content
                </h2>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <Label htmlFor="title">Title</Label>
                  <Input
                    data-testid="content-title-input"
                    id="title"
                    value={newContent.title}
                    onChange={(e) => setNewContent({ ...newContent, title: e.target.value })}
                    required
                    className="bg-white/5 border-white/10 text-white mt-2"
                    placeholder="Content title"
                  />
                </div>

                <div>
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    data-testid="content-description-input"
                    id="description"
                    value={newContent.description}
                    onChange={(e) => setNewContent({ ...newContent, description: e.target.value })}
                    required
                    className="bg-white/5 border-white/10 text-white mt-2"
                    placeholder="Describe the content"
                    rows={3}
                  />
                </div>

                <div>
                  <Label htmlFor="type">Type</Label>
                  <Select
                    value={newContent.type}
                    onValueChange={(value) => setNewContent({ ...newContent, type: value })}
                  >
                    <SelectTrigger data-testid="content-type-select" className="bg-white/5 border-white/10 text-white mt-2">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0D1234] border-white/10 text-white">
                      <SelectItem value="movie">Movie</SelectItem>
                      <SelectItem value="tv-show">TV Show</SelectItem>
                      <SelectItem value="sport">Sport</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="video-url">Video URL</Label>
                  <Input
                    data-testid="content-video-input"
                    id="video-url"
                    value={newContent.video_url}
                    onChange={(e) => setNewContent({ ...newContent, video_url: e.target.value })}
                    required
                    className="bg-white/5 border-white/10 text-white mt-2"
                    placeholder="https://example.com/video.mp4"
                  />
                </div>

                <div>
                  <Label htmlFor="thumbnail-url">Thumbnail URL</Label>
                  <Input
                    data-testid="content-thumbnail-input"
                    id="thumbnail-url"
                    value={newContent.thumbnail_url}
                    onChange={(e) => setNewContent({ ...newContent, thumbnail_url: e.target.value })}
                    required
                    className="bg-white/5 border-white/10 text-white mt-2"
                    placeholder="https://example.com/thumbnail.jpg"
                  />
                </div>

                <div>
                  <Label htmlFor="duration">Duration (seconds)</Label>
                  <Input
                    data-testid="content-duration-input"
                    id="duration"
                    type="number"
                    value={newContent.duration}
                    onChange={(e) => setNewContent({ ...newContent, duration: Number(e.target.value) })}
                    required
                    className="bg-white/5 border-white/10 text-white mt-2"
                    placeholder="7200"
                  />
                </div>

                <Button
                  data-testid="upload-content-btn"
                  type="submit"
                  disabled={loading}
                  className="w-full bg-cyan-400 text-[#0A0E27] hover:bg-cyan-500 py-6 rounded-xl"
                >
                  {loading ? 'Uploading...' : 'Upload Content'}
                </Button>
              </form>

              <div className="mt-6 pt-6 border-t border-white/10">
                <Button
                  data-testid="load-sample-data-btn"
                  onClick={handleLoadSampleData}
                  disabled={loading}
                  className="w-full bg-purple-600 hover:bg-purple-700 py-6 rounded-xl"
                >
                  Load Sample Data
                </Button>
                <p className="text-xs text-gray-500 mt-3 text-center">
                  Quickly populate the platform with sample movies, TV shows, and sports content
                </p>
              </div>
            </div>

            {/* Content List */}
            <div className="glass-effect rounded-xl p-8">
              <h2 className="text-2xl font-bold mb-6">Current Content</h2>
              
              {content.length === 0 ? (
                <div data-testid="no-content-admin" className="text-center py-12">
                  <Video className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-400">No content uploaded yet</p>
                </div>
              ) : (
                <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
                  {content.map((item) => (
                    <div key={item.id} data-testid={`admin-content-${item.id}`} className="bg-white/5 rounded-lg p-4 hover:bg-white/10 transition-colors">
                      <div className="flex items-start space-x-4">
                        <div className="w-24 h-16 rounded-lg bg-gradient-to-br from-cyan-500/20 to-purple-500/20 flex-shrink-0 overflow-hidden">
                          <img
                            src={item.thumbnail_url}
                            alt={item.title}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              e.target.style.display = 'none';
                            }}
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold mb-1 truncate">{item.title}</h3>
                          <p className="text-sm text-gray-400 line-clamp-2 mb-2">{item.description}</p>
                          <div className="flex items-center space-x-4 text-xs text-gray-500">
                            <span className="bg-cyan-400/20 text-cyan-400 px-2 py-1 rounded uppercase font-semibold">
                              {item.type}
                            </span>
                            <span>{item.views} views</span>
                            <span>{Math.floor(item.duration / 60)}m</span>
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
      </div>
    </div>
  );
};

export default AdminDashboard;
