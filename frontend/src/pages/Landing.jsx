import { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Play, Video, MessageCircle, Gift, TrendingUp, Users } from 'lucide-react';

const Landing = () => {
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);

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
            {user ? (
              <>
                <Button data-testid="browse-nav-btn" onClick={() => navigate('/browse')} variant="ghost" className="text-white hover:text-cyan-400">
                  Browse
                </Button>
                <Button data-testid="live-nav-btn" onClick={() => navigate('/live')} variant="ghost" className="text-white hover:text-cyan-400">
                  Live
                </Button>
                <Button data-testid="profile-nav-btn" onClick={() => navigate('/profile')} className="bg-cyan-400 text-[#0A0E27] hover:bg-cyan-500">
                  Profile
                </Button>
              </>
            ) : (
              <>
                <Button data-testid="login-btn" onClick={() => navigate('/auth')} variant="ghost" className="text-white hover:text-cyan-400">
                  Login
                </Button>
                <Button data-testid="signup-btn" onClick={() => navigate('/auth')} className="bg-cyan-400 text-[#0A0E27] hover:bg-cyan-500">
                  Sign Up
                </Button>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="relative">
            {/* Gradient Background (Limited to 15% of viewport) */}
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 to-purple-500/10 rounded-3xl blur-3xl" style={{ height: '15vh' }}></div>
            
            <div className="relative z-10 text-center max-w-4xl mx-auto">
              <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold mb-6 leading-tight">
                Watch. Stream. <span className="gradient-text">Connect.</span>
              </h1>
              <p className="text-lg sm:text-xl text-gray-300 mb-8 max-w-2xl mx-auto">
                Your ultimate destination for movies, TV shows, live sports, and interactive live streaming. Join thousands of creators and viewers.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Button data-testid="get-started-btn" onClick={() => navigate(user ? '/browse' : '/auth')} className="bg-cyan-400 text-[#0A0E27] hover:bg-cyan-500 text-lg px-8 py-6 rounded-full">
                  <Play className="w-5 h-5 mr-2" />
                  Get Started
                </Button>
                <Button data-testid="become-streamer-btn" onClick={() => navigate('/auth')} className="bg-gradient-to-r from-purple-600 to-pink-600 hover:opacity-90 text-lg px-8 py-6 rounded-full">
                  Become a Streamer
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-6 bg-[#0D1234]">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-16">Why Choose StreamHub?</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div data-testid="feature-content" className="glass-effect p-8 rounded-2xl hover:bg-white/10 transition-colors">
              <Video className="w-12 h-12 text-cyan-400 mb-4" />
              <h3 className="text-2xl font-semibold mb-3">Premium Content</h3>
              <p className="text-gray-300">Access thousands of movies, TV shows, and live sports events in stunning quality.</p>
            </div>
            <div data-testid="feature-live" className="glass-effect p-8 rounded-2xl hover:bg-white/10 transition-colors">
              <Users className="w-12 h-12 text-purple-400 mb-4" />
              <h3 className="text-2xl font-semibold mb-3">Live Streaming</h3>
              <p className="text-gray-300">Watch and interact with live streamers in real-time. Chat, gift, and be part of the action.</p>
            </div>
            <div data-testid="feature-earnings" className="glass-effect p-8 rounded-2xl hover:bg-white/10 transition-colors">
              <TrendingUp className="w-12 h-12 text-pink-400 mb-4" />
              <h3 className="text-2xl font-semibold mb-3">Earn as a Streamer</h3>
              <p className="text-gray-300">Monetize your content with views and gifts. Build your audience and grow your income.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Features */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-16">Engage Like Never Before</h2>
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <div className="space-y-6">
                <div data-testid="interaction-chat" className="flex items-start space-x-4">
                  <div className="bg-cyan-400/20 p-3 rounded-xl">
                    <MessageCircle className="w-6 h-6 text-cyan-400" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold mb-2">Real-time Chat</h3>
                    <p className="text-gray-300">Connect with streamers and other viewers through live chat during streams.</p>
                  </div>
                </div>
                <div data-testid="interaction-gift" className="flex items-start space-x-4">
                  <div className="bg-purple-400/20 p-3 rounded-xl">
                    <Gift className="w-6 h-6 text-purple-400" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold mb-2">Send Gifts</h3>
                    <p className="text-gray-300">Support your favorite streamers by sending virtual gifts during live streams.</p>
                  </div>
                </div>
                <div data-testid="interaction-join" className="flex items-start space-x-4">
                  <div className="bg-pink-400/20 p-3 rounded-xl">
                    <Play className="w-6 h-6 text-pink-400" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold mb-2">Join Live</h3>
                    <p className="text-gray-300">Jump into live streams instantly and be part of the community.</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="glass-effect p-8 rounded-2xl">
              <div className="aspect-video bg-gradient-to-br from-cyan-500/20 to-purple-500/20 rounded-xl flex items-center justify-center">
                <Play className="w-20 h-20 text-white opacity-50" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-20 px-6 bg-[#0D1234]">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-16">Simple Pricing</h2>
          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            <div data-testid="pricing-viewer" className="glass-effect p-8 rounded-2xl border-2 border-cyan-400/30 hover:border-cyan-400 transition-colors">
              <h3 className="text-2xl font-bold mb-2">Viewer</h3>
              <div className="mb-6">
                <span className="text-5xl font-bold">$7</span>
                <span className="text-gray-400">/month</span>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center">
                  <div className="w-2 h-2 bg-cyan-400 rounded-full mr-3"></div>
                  <span>Unlimited movies & TV shows</span>
                </li>
                <li className="flex items-center">
                  <div className="w-2 h-2 bg-cyan-400 rounded-full mr-3"></div>
                  <span>Live sports streaming</span>
                </li>
                <li className="flex items-center">
                  <div className="w-2 h-2 bg-cyan-400 rounded-full mr-3"></div>
                  <span>Join live streams</span>
                </li>
                <li className="flex items-center">
                  <div className="w-2 h-2 bg-cyan-400 rounded-full mr-3"></div>
                  <span>Chat & send gifts</span>
                </li>
              </ul>
              <Button data-testid="viewer-subscribe-btn" onClick={() => navigate('/auth')} className="w-full bg-cyan-400 text-[#0A0E27] hover:bg-cyan-500 rounded-full py-6">
                Start Watching
              </Button>
            </div>
            <div data-testid="pricing-streamer" className="glass-effect p-8 rounded-2xl border-2 border-purple-400/30 hover:border-purple-400 transition-colors relative overflow-hidden">
              <div className="absolute top-4 right-4 bg-gradient-to-r from-purple-600 to-pink-600 px-4 py-1 rounded-full text-sm font-semibold">
                Popular
              </div>
              <h3 className="text-2xl font-bold mb-2">Streamer</h3>
              <div className="mb-6">
                <span className="text-5xl font-bold">$100</span>
                <span className="text-gray-400">/month</span>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center">
                  <div className="w-2 h-2 bg-purple-400 rounded-full mr-3"></div>
                  <span>All viewer features</span>
                </li>
                <li className="flex items-center">
                  <div className="w-2 h-2 bg-purple-400 rounded-full mr-3"></div>
                  <span>Unlimited live streaming</span>
                </li>
                <li className="flex items-center">
                  <div className="w-2 h-2 bg-purple-400 rounded-full mr-3"></div>
                  <span>Earn $0.03 per 100K views</span>
                </li>
                <li className="flex items-center">
                  <div className="w-2 h-2 bg-purple-400 rounded-full mr-3"></div>
                  <span>Earn $0.002 per gift</span>
                </li>
                <li className="flex items-center">
                  <div className="w-2 h-2 bg-purple-400 rounded-full mr-3"></div>
                  <span>Save & export streams</span>
                </li>
              </ul>
              <Button data-testid="streamer-subscribe-btn" onClick={() => navigate('/auth')} className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:opacity-90 rounded-full py-6">
                Start Streaming
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-white/10">
        <div className="max-w-7xl mx-auto text-center text-gray-400">
          <p>&copy; 2025 StreamHub. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
