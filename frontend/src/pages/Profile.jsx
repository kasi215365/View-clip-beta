import { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { User as UserIcon, CreditCard, CheckCircle, XCircle, LogOut, Home, Radio, Wallet, Gift as GiftIcon, Banknote, Trophy, Copy } from 'lucide-react';
import Logo from '@/components/Logo';
import NotificationBell from '@/components/NotificationBell';
import axios from 'axios';
import { toast } from 'sonner';

const Profile = () => {
  const navigate = useNavigate();
  const { user, logout, fetchUser } = useContext(AuthContext);
  const [subscription, setSubscription] = useState(null);
  const [tiers, setTiers] = useState([]);
  const [wallet, setWallet] = useState({});
  const [referral, setReferral] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isBundleOpen, setIsBundleOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState('viewer');

  useEffect(() => {
    (async () => {
      try {
        const [sub, t, w, ref] = await Promise.all([
          axios.get(`${API}/subscriptions/status`),
          axios.get(`${API}/gifts/tiers`),
          axios.get(`${API}/gifts/wallet`),
          axios.get(`${API}/referrals/my`),
        ]);
        if (sub.data.has_subscription) setSubscription(sub.data.subscription);
        setTiers(t.data.tiers || []);
        setWallet(w.data.wallet || {});
        setReferral(ref.data);
      } catch (e) {
        console.error(e);
      }
    })();
  }, []);

  const copyReferralLink = () => {
    if (!referral) return;
    const link = `${window.location.origin}/auth?ref=${referral.code}`;
    navigator.clipboard.writeText(link);
    toast.success('Referral link copied');
  };

  const handleSubscribe = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API}/payments/checkout/subscribe`, {
        type: selectedPlan,
        origin_url: window.location.origin,
      });
      if (res.data.url) {
        window.location.href = res.data.url;
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to start checkout');
      setLoading(false);
    }
  };

  const handleBundle = async (tierId) => {
    try {
      const res = await axios.post(`${API}/payments/checkout/gift-bundle`, {
        tier_id: tierId,
        origin_url: window.location.origin,
      });
      if (res.data.url) window.location.href = res.data.url;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to start checkout');
    }
  };

  const handleConnectOnboard = async () => {
    try {
      const res = await axios.post(`${API}/streamers/connect/onboard`);
      toast.success('Payout account connected.');
      await fetchUser();
      console.log('Connect URL:', res.data.onboarding_url);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Connect onboarding failed');
    }
  };

  return (
    <div className="min-h-screen bg-[#05070F] text-white">
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Logo size="md" />
          <div className="flex items-center space-x-4">
            <Button data-testid="browse-nav-btn" onClick={() => navigate('/browse')} variant="ghost" className="text-white hover:text-cyan-400">
              <Home className="w-4 h-4 mr-2" /> Browse
            </Button>
            <Button data-testid="live-nav-btn" onClick={() => navigate('/live')} variant="ghost" className="text-white hover:text-cyan-400">
              <Radio className="w-4 h-4 mr-2" /> Live
            </Button>
            {(user?.role === 'streamer' || user?.role === 'admin') && (
              <Button data-testid="streamer-nav-btn" onClick={() => navigate('/streamer')} variant="ghost" className="text-white hover:text-cyan-400">Dashboard</Button>
            )}
            {user?.role === 'admin' && (
              <Button data-testid="admin-nav-btn" onClick={() => navigate('/admin')} variant="ghost" className="text-white hover:text-cyan-400">Admin</Button>
            )}
            <Button data-testid="leaderboard-nav-btn" onClick={() => navigate('/leaderboard')} variant="ghost" className="text-white hover:text-cyan-400"><Trophy className="w-4 h-4 mr-2" />Top 50</Button>
            <NotificationBell />
            <Button data-testid="profile-nav-btn" onClick={() => navigate('/profile')} variant="ghost" className="text-cyan-400">
              <UserIcon className="w-4 h-4 mr-2" /> Profile
            </Button>
            <Button data-testid="logout-nav-btn" onClick={logout} variant="ghost" className="text-white hover:text-red-400">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </nav>

      <div className="pt-24 px-6 pb-12">
        <div className="max-w-5xl mx-auto">
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2">Profile</h1>
            <p className="text-gray-400">Manage your account, subscription, and gift wallet</p>
          </div>

          {/* Profile Card */}
          <div data-testid="profile-card" className="glass-panel rounded-xl p-8 mb-8">
            <div className="flex items-center space-x-6 mb-6">
              <div className="w-20 h-20 bg-gradient-to-br from-cyan-400 to-fuchsia-500 rounded-full flex items-center justify-center text-3xl font-bold text-[#05070F]">
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
                <p className="text-lg font-semibold">{new Date(user?.created_at).toLocaleDateString()}</p>
              </div>
            </div>
          </div>

          {/* Subscription */}
          <div data-testid="subscription-card" className="glass-panel rounded-xl p-8 mb-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold flex items-center">
                <CreditCard className="w-6 h-6 mr-3 text-cyan-400" />
                Subscription
              </h2>
              {user?.subscription_status === 'active' ? (
                <div className="flex items-center text-green-400"><CheckCircle className="w-5 h-5 mr-2" /><span className="font-semibold">Active</span></div>
              ) : (
                <div className="flex items-center text-red-400"><XCircle className="w-5 h-5 mr-2" /><span className="font-semibold">Inactive</span></div>
              )}
            </div>
            {user?.subscription_status === 'active' && subscription ? (
              <div className="bg-white/5 rounded-lg p-4">
                <div className="grid md:grid-cols-3 gap-4">
                  <div><p className="text-gray-400 text-sm mb-1">Plan</p><p className="text-lg font-semibold capitalize">{subscription.type}</p></div>
                  <div><p className="text-gray-400 text-sm mb-1">Amount</p><p className="text-lg font-semibold">${subscription.amount}/mo</p></div>
                  <div><p className="text-gray-400 text-sm mb-1">Renews</p><p className="text-lg font-semibold">{new Date(subscription.expires_at).toLocaleDateString()}</p></div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-400 mb-6">You don't have an active subscription</p>
                <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                  <DialogTrigger asChild>
                    <Button data-testid="subscribe-btn" className="bg-gradient-to-r from-cyan-400 to-fuchsia-500 hover:opacity-90 px-8 py-6 rounded-xl text-[#05070F] font-semibold">
                      Subscribe Now
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="bg-[#0A0E27] border-white/10 text-white max-w-2xl">
                    <DialogHeader><DialogTitle className="text-2xl">Choose Your Plan</DialogTitle></DialogHeader>
                    <div className="grid md:grid-cols-2 gap-6 mt-6">
                      <div data-testid="viewer-plan-card" onClick={() => setSelectedPlan('viewer')}
                        className={`glass-panel rounded-xl p-6 cursor-pointer transition-all ${selectedPlan === 'viewer' ? 'border-2 border-cyan-400 bg-cyan-400/10' : 'border-2 border-white/10 hover:border-cyan-400/50'}`}>
                        <h3 className="text-xl font-bold mb-2">Viewer</h3>
                        <div className="mb-4"><span className="text-4xl font-bold">$7</span><span className="text-gray-400">/month</span></div>
                        <ul className="space-y-2 text-sm">
                          <li className="flex items-center"><CheckCircle className="w-4 h-4 mr-2 text-cyan-400" />Unlimited content</li>
                          <li className="flex items-center"><CheckCircle className="w-4 h-4 mr-2 text-cyan-400" />Join live streams</li>
                          <li className="flex items-center"><CheckCircle className="w-4 h-4 mr-2 text-cyan-400" />Chat & gift</li>
                        </ul>
                      </div>
                      <div data-testid="streamer-plan-card" onClick={() => setSelectedPlan('streamer')}
                        className={`glass-panel rounded-xl p-6 cursor-pointer transition-all ${selectedPlan === 'streamer' ? 'border-2 border-fuchsia-500 bg-fuchsia-500/10' : 'border-2 border-white/10 hover:border-fuchsia-500/50'}`}>
                        <div className="bg-gradient-to-r from-cyan-400 to-fuchsia-500 px-3 py-1 rounded-full text-xs font-semibold inline-block mb-2 text-[#05070F]">Popular</div>
                        <h3 className="text-xl font-bold mb-2">Streamer</h3>
                        <div className="mb-4"><span className="text-4xl font-bold">$50</span><span className="text-gray-400">/month</span></div>
                        <ul className="space-y-2 text-sm">
                          <li className="flex items-center"><CheckCircle className="w-4 h-4 mr-2 text-fuchsia-400" />All viewer features</li>
                          <li className="flex items-center"><CheckCircle className="w-4 h-4 mr-2 text-fuchsia-400" />Unlimited streaming</li>
                          <li className="flex items-center"><CheckCircle className="w-4 h-4 mr-2 text-fuchsia-400" />Earn from views & gifts</li>
                          <li className="flex items-center"><CheckCircle className="w-4 h-4 mr-2 text-fuchsia-400" />Save & export streams</li>
                        </ul>
                      </div>
                    </div>
                    <Button data-testid="confirm-subscribe-btn" onClick={handleSubscribe} disabled={loading}
                      className="w-full bg-gradient-to-r from-cyan-400 to-fuchsia-500 hover:opacity-90 py-6 rounded-xl mt-4 font-semibold text-[#05070F]">
                      {loading ? 'Redirecting to Stripe…' : `Checkout $${selectedPlan === 'viewer' ? 7 : 50}`}
                    </Button>
                  </DialogContent>
                </Dialog>
              </div>
            )}
          </div>

          {/* Referral Card */}
          {referral && (
            <div data-testid="referral-card" className="glass-panel rounded-xl p-8 mb-8 border-amber-400/30">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold flex items-center"><Trophy className="w-6 h-6 mr-3 text-amber-400" />Referrals</h2>
                <Button data-testid="view-leaderboard-btn" onClick={() => navigate('/leaderboard')} className="bg-amber-500 hover:bg-amber-600 text-[#05070F]">View Leaderboard</Button>
              </div>
              <p className="text-gray-400 mb-4">Share your code. When someone you refer subscribes, you earn <span className="text-amber-400 font-semibold">10%</span> commission.</p>
              <div className="grid md:grid-cols-3 gap-4 mb-4">
                <div className="bg-white/5 rounded-lg p-4">
                  <div className="text-xs text-gray-400 mb-1">Your Code</div>
                  <div data-testid="referral-code" className="font-mono text-2xl font-bold text-cyan-400 flex items-center gap-2">
                    {referral.code}
                    <button data-testid="copy-referral-btn" onClick={copyReferralLink} className="text-gray-400 hover:text-cyan-400"><Copy className="w-4 h-4" /></button>
                  </div>
                </div>
                <div className="bg-white/5 rounded-lg p-4">
                  <div className="text-xs text-gray-400 mb-1">People Referred</div>
                  <div data-testid="referral-count" className="text-2xl font-bold">{referral.referred_count}</div>
                </div>
                <div className="bg-white/5 rounded-lg p-4">
                  <div className="text-xs text-gray-400 mb-1">Earnings</div>
                  <div data-testid="referral-earnings" className="text-2xl font-bold text-green-400">${referral.earnings.toFixed(2)}</div>
                </div>
              </div>
              {referral.events && referral.events.length > 0 && (
                <div className="mt-4">
                  <div className="text-xs text-gray-400 mb-2">Recent rewards</div>
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {referral.events.map((e) => (
                      <div key={e.id} className="flex justify-between text-sm bg-white/5 rounded px-3 py-2">
                        <span>{e.sub_type} subscription ({new Date(e.created_at).toLocaleDateString()})</span>
                        <span className="text-green-400 font-semibold">+${e.amount.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Gift Wallet */}
          <div data-testid="gift-wallet-card" className="glass-panel rounded-xl p-8 mb-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold flex items-center">
                <Wallet className="w-6 h-6 mr-3 text-fuchsia-400" />
                Gift Wallet
              </h2>
              <Dialog open={isBundleOpen} onOpenChange={setIsBundleOpen}>
                <DialogTrigger asChild>
                  <Button data-testid="buy-bundle-btn" className="bg-fuchsia-500 hover:bg-fuchsia-600 rounded-full px-6">
                    <GiftIcon className="w-4 h-4 mr-2" /> Buy Bundle
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-[#0A0E27] border-white/10 text-white max-w-3xl max-h-[80vh] overflow-y-auto">
                  <DialogHeader><DialogTitle className="text-2xl">Gift Bundles — 500 units each</DialogTitle></DialogHeader>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                    {tiers.map((t) => (
                      <button key={t.id} data-testid={`bundle-${t.id}`} onClick={() => handleBundle(t.id)}
                        className="glass-panel rounded-xl p-4 hover:border-cyan-400 transition-all text-left">
                        <div className="text-4xl mb-2">{t.emoji}</div>
                        <div className="font-semibold">{t.name}</div>
                        <div className="text-xs text-gray-400 mb-2">${t.value_per_unit.toFixed(3)}/unit · {t.qty} units</div>
                        <div className="text-cyan-400 font-bold">${t.price}</div>
                      </button>
                    ))}
                  </div>
                </DialogContent>
              </Dialog>
            </div>
            {tiers.length > 0 ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {tiers.map((t) => (
                  <div key={t.id} data-testid={`wallet-${t.id}`} className="bg-white/5 rounded-lg p-3 flex items-center space-x-3">
                    <span className="text-2xl">{t.emoji}</span>
                    <div>
                      <div className="text-xs text-gray-400">{t.name}</div>
                      <div className="font-bold text-lg">{wallet[t.id] || 0}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : <p className="text-gray-500 text-sm">Loading gift tiers…</p>}
          </div>

          {/* Streamer Payouts */}
          {(user?.role === 'streamer' || user?.role === 'admin') && (
            <div data-testid="connect-card" className="glass-panel rounded-xl p-8 mb-8">
              <h2 className="text-2xl font-bold mb-4 flex items-center">
                <Banknote className="w-6 h-6 mr-3 text-green-400" /> Payout Account
              </h2>
              {user?.connect_account_status === 'active' ? (
                <div className="flex items-center text-green-400"><CheckCircle className="w-5 h-5 mr-2" />Connect account active — payouts enabled</div>
              ) : (
                <div>
                  <p className="text-gray-400 mb-4">Connect a Stripe Connect Express account to receive payouts from views and gifts.</p>
                  <Button data-testid="connect-onboard-btn" onClick={handleConnectOnboard} className="bg-green-500 hover:bg-green-600">
                    Connect Payout Account
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Rates */}
          <div className="glass-panel rounded-xl p-8">
            <h2 className="text-2xl font-bold mb-6">Streamer Earning Rates</h2>
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-white/5 rounded-lg p-6">
                <h3 className="font-semibold mb-2 text-cyan-400">Views</h3>
                <p className="text-3xl font-bold mb-2">$0.005</p>
                <p className="text-sm text-gray-400">per qualified view (30-min watch)</p>
              </div>
              <div className="bg-white/5 rounded-lg p-6">
                <h3 className="font-semibold mb-2 text-fuchsia-400">Gifts</h3>
                <p className="text-3xl font-bold mb-2">$0.002+</p>
                <p className="text-sm text-gray-400">per gift unit (scales by tier)</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
