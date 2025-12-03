import { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Video, User as UserIcon, CreditCard, CheckCircle, XCircle, LogOut, Home, Radio } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const Profile = () => {
  const navigate = useNavigate();
  const { user, logout, fetchUser } = useContext(AuthContext);
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState('viewer');

  useEffect(() => {
    fetchSubscription();
  }, []);

  const fetchSubscription = async () => {
    try {
      const response = await axios.get(`${API}/subscriptions/status`);
      if (response.data.has_subscription) {
        setSubscription(response.data.subscription);
      }
    } catch (error) {
      console.error('Failed to fetch subscription');
    }
  };

  const handleSubscribe = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/subscriptions/subscribe`, { type: selectedPlan });
      toast.success(`Successfully subscribed to ${selectedPlan} plan!`);
      setIsDialogOpen(false);
      fetchSubscription();
      await fetchUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to subscribe');
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
            {(user?.role === 'streamer' || user?.role === 'admin') && (
              <Button data-testid="streamer-nav-btn" onClick={() => navigate('/streamer')} variant="ghost" className="text-white hover:text-cyan-400">
                Dashboard
              </Button>
            )}
            {user?.role === 'admin' && (
              <Button data-testid="admin-nav-btn" onClick={() => navigate('/admin')} variant="ghost" className="text-white hover:text-cyan-400">
                Admin
              </Button>
            )}
            <Button data-testid="profile-nav-btn" onClick={() => navigate('/profile')} variant="ghost" className="text-cyan-400">
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
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2">Profile</h1>
            <p className="text-gray-400">Manage your account and subscription</p>
          </div>

          {/* Profile Card */}
          <div data-testid="profile-card" className="glass-effect rounded-xl p-8 mb-8">
            <div className="flex items-center space-x-6 mb-6">
              <div className="w-20 h-20 bg-gradient-to-br from-cyan-400 to-purple-400 rounded-full flex items-center justify-center text-3xl font-bold">
                {user?.name?.charAt(0).toUpperCase()}
              </div>
              <div>
                <h2 className="text-2xl font-bold">{user?.name}</h2>
                <p className="text-gray-400">{user?.email}</p>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-white/5 rounded-lg p-4">
                <p className="text-gray-400 text-sm mb-1">Account Type</p>
                <p className="text-lg font-semibold capitalize">{user?.role}</p>
              </div>
              <div className="bg-white/5 rounded-lg p-4">
                <p className="text-gray-400 text-sm mb-1">Member Since</p>
                <p className="text-lg font-semibold">
                  {new Date(user?.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>

          {/* Subscription Status */}
          <div data-testid="subscription-card" className="glass-effect rounded-xl p-8 mb-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold flex items-center">
                <CreditCard className="w-6 h-6 mr-3 text-cyan-400" />
                Subscription
              </h2>
              {user?.subscription_status === 'active' ? (
                <div className="flex items-center text-green-400">
                  <CheckCircle className="w-5 h-5 mr-2" />
                  <span className="font-semibold">Active</span>
                </div>
              ) : (
                <div className="flex items-center text-red-400">
                  <XCircle className="w-5 h-5 mr-2" />
                  <span className="font-semibold">Inactive</span>
                </div>
              )}
            </div>

            {user?.subscription_status === 'active' && subscription ? (
              <div className="space-y-4">
                <div className="bg-white/5 rounded-lg p-4">
                  <div className="grid md:grid-cols-3 gap-4">
                    <div>
                      <p className="text-gray-400 text-sm mb-1">Plan Type</p>
                      <p className="text-lg font-semibold capitalize">{subscription.type}</p>
                    </div>
                    <div>
                      <p className="text-gray-400 text-sm mb-1">Amount</p>
                      <p className="text-lg font-semibold">${subscription.amount}/month</p>
                    </div>
                    <div>
                      <p className="text-gray-400 text-sm mb-1">Expires</p>
                      <p className="text-lg font-semibold">
                        {new Date(subscription.expires_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </div>
                <p className="text-sm text-gray-400">
                  Your subscription will automatically renew on {new Date(subscription.expires_at).toLocaleDateString()}.
                </p>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-400 mb-6">You don't have an active subscription</p>
                <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                  <DialogTrigger asChild>
                    <Button data-testid="subscribe-btn" className="bg-gradient-to-r from-purple-600 to-pink-600 hover:opacity-90 px-8 py-6 rounded-xl">
                      Subscribe Now
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="bg-[#0D1234] border-white/10 text-white max-w-2xl">
                    <DialogHeader>
                      <DialogTitle className="text-2xl">Choose Your Plan</DialogTitle>
                    </DialogHeader>
                    <div className="grid md:grid-cols-2 gap-6 mt-6">
                      <div
                        data-testid="viewer-plan-card"
                        onClick={() => setSelectedPlan('viewer')}
                        className={`glass-effect rounded-xl p-6 cursor-pointer transition-all ${
                          selectedPlan === 'viewer'
                            ? 'border-2 border-cyan-400 bg-cyan-400/10'
                            : 'border-2 border-white/10 hover:border-cyan-400/50'
                        }`}
                      >
                        <h3 className="text-xl font-bold mb-2">Viewer</h3>
                        <div className="mb-4">
                          <span className="text-4xl font-bold">$7</span>
                          <span className="text-gray-400">/month</span>
                        </div>
                        <ul className="space-y-2 text-sm">
                          <li className="flex items-center">
                            <CheckCircle className="w-4 h-4 mr-2 text-cyan-400" />
                            Unlimited content
                          </li>
                          <li className="flex items-center">
                            <CheckCircle className="w-4 h-4 mr-2 text-cyan-400" />
                            Join live streams
                          </li>
                          <li className="flex items-center">
                            <CheckCircle className="w-4 h-4 mr-2 text-cyan-400" />
                            Chat & send gifts
                          </li>
                        </ul>
                      </div>
                      <div
                        data-testid="streamer-plan-card"
                        onClick={() => setSelectedPlan('streamer')}
                        className={`glass-effect rounded-xl p-6 cursor-pointer transition-all ${
                          selectedPlan === 'streamer'
                            ? 'border-2 border-purple-400 bg-purple-400/10'
                            : 'border-2 border-white/10 hover:border-purple-400/50'
                        }`}
                      >
                        <div className="bg-gradient-to-r from-purple-600 to-pink-600 px-3 py-1 rounded-full text-xs font-semibold inline-block mb-2">
                          Popular
                        </div>
                        <h3 className="text-xl font-bold mb-2">Streamer</h3>
                        <div className="mb-4">
                          <span className="text-4xl font-bold">$100</span>
                          <span className="text-gray-400">/month</span>
                        </div>
                        <ul className="space-y-2 text-sm">
                          <li className="flex items-center">
                            <CheckCircle className="w-4 h-4 mr-2 text-purple-400" />
                            All viewer features
                          </li>
                          <li className="flex items-center">
                            <CheckCircle className="w-4 h-4 mr-2 text-purple-400" />
                            Unlimited streaming
                          </li>
                          <li className="flex items-center">
                            <CheckCircle className="w-4 h-4 mr-2 text-purple-400" />
                            Earn from views & gifts
                          </li>
                          <li className="flex items-center">
                            <CheckCircle className="w-4 h-4 mr-2 text-purple-400" />
                            Save & export streams
                          </li>
                        </ul>
                      </div>
                    </div>
                    <div className="mt-6 bg-yellow-500/20 border border-yellow-500/50 rounded-lg p-4 text-sm">
                      <p className="text-yellow-200">
                        <strong>Note:</strong> Payment processing is mocked for this demo. Your subscription will be activated immediately.
                      </p>
                    </div>
                    <Button
                      data-testid="confirm-subscribe-btn"
                      onClick={handleSubscribe}
                      disabled={loading}
                      className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:opacity-90 py-6 rounded-xl mt-4"
                    >
                      {loading ? 'Processing...' : `Subscribe to ${selectedPlan} plan`}
                    </Button>
                  </DialogContent>
                </Dialog>
              </div>
            )}
          </div>

          {/* Pricing Info */}
          <div className="glass-effect rounded-xl p-8">
            <h2 className="text-2xl font-bold mb-6">Earning Rates (Streamers)</h2>
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-white/5 rounded-lg p-6">
                <h3 className="font-semibold mb-2 text-cyan-400">Views</h3>
                <p className="text-3xl font-bold mb-2">$0.03</p>
                <p className="text-sm text-gray-400">per 100,000 views</p>
              </div>
              <div className="bg-white/5 rounded-lg p-6">
                <h3 className="font-semibold mb-2 text-purple-400">Gifts</h3>
                <p className="text-3xl font-bold mb-2">$0.002</p>
                <p className="text-sm text-gray-400">per gift received</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
