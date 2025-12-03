import { useState, useEffect, useContext } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Video, ArrowLeft, Play, Clock } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const Watch = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchContent();
    recordView();
  }, [id]);

  const fetchContent = async () => {
    try {
      const response = await axios.get(`${API}/content/${id}`);
      setContent(response.data);
    } catch (error) {
      toast.error('Failed to load content');
      navigate('/browse');
    } finally {
      setLoading(false);
    }
  };

  const recordView = async () => {
    try {
      await axios.post(`${API}/content/${id}/view`);
    } catch (error) {
      console.error('Failed to record view');
    }
  };

  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#0A0E27]">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!content) return null;

  return (
    <div className="min-h-screen bg-[#0A0E27] text-white">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <Button data-testid="back-btn" onClick={() => navigate('/browse')} variant="ghost" className="text-white hover:text-cyan-400">
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div className="flex items-center space-x-2">
              <Video className="w-8 h-8 text-cyan-400" />
              <h1 className="text-2xl font-bold">StreamHub</h1>
            </div>
          </div>
        </div>
      </nav>

      <div className="pt-24 px-6 pb-12">
        <div className="max-w-6xl mx-auto">
          {/* Video Player */}
          <div data-testid="video-player" className="aspect-video bg-black rounded-xl overflow-hidden mb-8 relative">
            <video
              src={content.video_url}
              controls
              autoPlay
              className="w-full h-full"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            >
              Your browser does not support the video tag.
            </video>
            {!content.video_url && (
              <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-cyan-500/20 to-purple-500/20">
                <Play className="w-20 h-20 text-white opacity-50" />
              </div>
            )}
          </div>

          {/* Content Info */}
          <div data-testid="content-info" className="glass-effect rounded-xl p-8">
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="bg-cyan-400 text-[#0A0E27] px-3 py-1 rounded-full text-sm font-semibold uppercase inline-block mb-3">
                  {content.type}
                </div>
                <h1 className="text-3xl font-bold mb-2">{content.title}</h1>
              </div>
            </div>

            <div className="flex items-center space-x-6 text-gray-400 mb-6">
              <div className="flex items-center">
                <Clock className="w-5 h-5 mr-2" />
                <span>{formatDuration(content.duration)}</span>
              </div>
              <div className="flex items-center">
                <Play className="w-5 h-5 mr-2" />
                <span>{content.views.toLocaleString()} views</span>
              </div>
            </div>

            <div>
              <h2 className="text-xl font-semibold mb-3">Description</h2>
              <p className="text-gray-300 leading-relaxed">{content.description}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Watch;
