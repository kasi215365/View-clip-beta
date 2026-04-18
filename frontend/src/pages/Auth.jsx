import { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Logo from '@/components/Logo';
import axios from 'axios';
import { toast } from 'sonner';

// Curated movie/TV poster backsplash (public Unsplash photos)
const POSTERS = [
  'https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=400',
  'https://images.unsplash.com/photo-1598899134739-24c46f58b8c0?w=400',
  'https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=400',
  'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=400',
  'https://images.unsplash.com/photo-1527224857830-43a7acc85260?w=400',
  'https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=400',
  'https://images.unsplash.com/photo-1478720568477-152d9b164e26?w=400',
  'https://images.unsplash.com/photo-1440404653325-ab127d49abc1?w=400',
  'https://images.unsplash.com/photo-1485846234645-a62644f84728?w=400',
  'https://images.unsplash.com/photo-1542204165-65bf26472b9b?w=400',
  'https://images.unsplash.com/photo-1518676590629-3dcba9c5a555?w=400',
  'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=400',
  'https://images.unsplash.com/photo-1596727147705-61a532a659bd?w=400',
  'https://images.unsplash.com/photo-1478720568477-b0829d4f7b14?w=400',
  'https://images.unsplash.com/photo-1504805572947-34fad45aed93?w=400',
  'https://images.unsplash.com/photo-1559583109-3e7968136c99?w=400',
  'https://images.unsplash.com/photo-1531259683007-016a7b628fc3?w=400',
  'https://images.unsplash.com/photo-1524985069026-dd778a71c7b4?w=400',
  'https://images.unsplash.com/photo-1540224485089-80dd7a7b6a28?w=400',
  'https://images.unsplash.com/photo-1513106580091-1d82408b8cd6?w=400',
];

const Auth = () => {
  const navigate = useNavigate();
  const { login } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);

  const [loginData, setLoginData] = useState({ email: '', password: '' });
  const [registerData, setRegisterData] = useState({
    email: '',
    password: '',
    name: '',
    role: 'viewer',
    referral_code: ''
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/login`, loginData);
      login(response.data.token, response.data.user);
      toast.success('Welcome back.');
      navigate('/browse');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/register`, registerData);
      login(response.data.token, response.data.user);
      toast.success('Account created.');
      navigate('/browse');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  // Duplicate poster list for seamless drift animation
  const posters = [...POSTERS, ...POSTERS];

  return (
    <div className="min-h-screen bg-[#05070F] relative overflow-hidden flex items-center justify-center px-6 py-12">
      {/* Poster backsplash */}
      <div data-testid="auth-poster-backsplash" className="poster-grid" aria-hidden="true">
        {posters.map((src, i) => (
          <img key={i} src={src} alt="" loading="lazy" />
        ))}
      </div>
      <div className="auth-vignette" aria-hidden="true" />

      <div className="relative z-10 w-full max-w-md">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-4">
            <Logo size="lg" animated />
          </div>
          <p className="text-gray-400">Premium streaming. Interactive live.</p>
        </div>

        <div className="glass-panel rounded-2xl p-8">
          <Tabs defaultValue="login" className="w-full">
            <TabsList data-testid="auth-tabs" className="grid w-full grid-cols-2 mb-6 bg-white/5">
              <TabsTrigger data-testid="login-tab" value="login" className="data-[state=active]:bg-cyan-400 data-[state=active]:text-[#05070F]">Sign In</TabsTrigger>
              <TabsTrigger data-testid="register-tab" value="register" className="data-[state=active]:bg-cyan-400 data-[state=active]:text-[#05070F]">Sign Up</TabsTrigger>
            </TabsList>

            <TabsContent value="login">
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <Label htmlFor="login-email" className="text-white">Email</Label>
                  <Input data-testid="login-email-input" id="login-email" type="email" value={loginData.email}
                    onChange={(e) => setLoginData({ ...loginData, email: e.target.value })} required
                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 mt-2"
                    placeholder="you@example.com" />
                </div>
                <div>
                  <Label htmlFor="login-password" className="text-white">Password</Label>
                  <Input data-testid="login-password-input" id="login-password" type="password" value={loginData.password}
                    onChange={(e) => setLoginData({ ...loginData, password: e.target.value })} required
                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 mt-2"
                    placeholder="••••••••" />
                </div>
                <Button data-testid="login-submit-btn" type="submit" disabled={loading}
                  className="w-full bg-cyan-400 text-[#05070F] hover:bg-cyan-300 rounded-full py-6 mt-6 font-semibold">
                  {loading ? 'Signing in…' : 'Sign In'}
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="register">
              <form onSubmit={handleRegister} className="space-y-4">
                <div>
                  <Label htmlFor="register-name" className="text-white">Name</Label>
                  <Input data-testid="register-name-input" id="register-name" type="text" value={registerData.name}
                    onChange={(e) => setRegisterData({ ...registerData, name: e.target.value })} required
                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 mt-2" placeholder="Your name" />
                </div>
                <div>
                  <Label htmlFor="register-email" className="text-white">Email</Label>
                  <Input data-testid="register-email-input" id="register-email" type="email" value={registerData.email}
                    onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })} required
                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 mt-2" placeholder="you@example.com" />
                </div>
                <div>
                  <Label htmlFor="register-password" className="text-white">Password</Label>
                  <Input data-testid="register-password-input" id="register-password" type="password" value={registerData.password}
                    onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })} required
                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 mt-2" placeholder="••••••••" />
                </div>
                <div>
                  <Label htmlFor="register-role" className="text-white">I want to join as</Label>
                  <select data-testid="register-role-select" id="register-role" value={registerData.role}
                    onChange={(e) => setRegisterData({ ...registerData, role: e.target.value })}
                    className="w-full bg-white/5 border border-white/10 text-white rounded-md px-4 py-2 mt-2">
                    <option value="viewer" className="bg-[#0A0E27]">Viewer — $7/month</option>
                    <option value="streamer" className="bg-[#0A0E27]">Streamer — $50/month</option>
                  </select>
                </div>
                <div>
                  <Label htmlFor="register-referral" className="text-white">Referral code <span className="text-gray-500 text-xs">(optional)</span></Label>
                  <Input data-testid="register-referral-input" id="register-referral" type="text" value={registerData.referral_code}
                    onChange={(e) => setRegisterData({ ...registerData, referral_code: e.target.value.toUpperCase() })}
                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 mt-2 uppercase" placeholder="e.g. KAICE1A2B3" />
                </div>
                <Button data-testid="register-submit-btn" type="submit" disabled={loading}
                  className="w-full bg-gradient-to-r from-cyan-400 to-fuchsia-500 hover:opacity-90 rounded-full py-6 mt-6 font-semibold text-[#05070F]">
                  {loading ? 'Creating account…' : 'Create Account'}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </div>

        <div className="text-center mt-6">
          <Button data-testid="back-home-btn" onClick={() => navigate('/')} variant="ghost" className="text-gray-400 hover:text-white">
            Back to Home
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Auth;
