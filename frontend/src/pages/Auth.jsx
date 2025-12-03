import { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Video } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const Auth = () => {
  const navigate = useNavigate();
  const { login } = useContext(AuthContext);
  const [loading, setLoading] = useState(false);

  const [loginData, setLoginData] = useState({ email: '', password: '' });
  const [registerData, setRegisterData] = useState({
    email: '',
    password: '',
    name: '',
    role: 'viewer'
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/auth/login`, loginData);
      login(response.data.token, response.data.user);
      toast.success('Welcome back!');
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
      toast.success('Account created successfully!');
      navigate('/browse');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0E27] flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center space-x-2 mb-4">
            <Video className="w-10 h-10 text-cyan-400" />
            <h1 className="text-3xl font-bold">StreamHub</h1>
          </div>
          <p className="text-gray-400">Join the ultimate streaming platform</p>
        </div>

        <div className="glass-effect rounded-2xl p-8">
          <Tabs defaultValue="login" className="w-full">
            <TabsList data-testid="auth-tabs" className="grid w-full grid-cols-2 mb-6 bg-white/5">
              <TabsTrigger data-testid="login-tab" value="login" className="data-[state=active]:bg-cyan-400 data-[state=active]:text-[#0A0E27]">Login</TabsTrigger>
              <TabsTrigger data-testid="register-tab" value="register" className="data-[state=active]:bg-cyan-400 data-[state=active]:text-[#0A0E27]">Register</TabsTrigger>
            </TabsList>

            <TabsContent value="login">
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <Label htmlFor="login-email" className="text-white">Email</Label>
                  <Input
                    data-testid="login-email-input"
                    id="login-email"
                    type="email"
                    value={loginData.email}
                    onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                    required
                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 mt-2"
                    placeholder="you@example.com"
                  />
                </div>
                <div>
                  <Label htmlFor="login-password" className="text-white">Password</Label>
                  <Input
                    data-testid="login-password-input"
                    id="login-password"
                    type="password"
                    value={loginData.password}
                    onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                    required
                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 mt-2"
                    placeholder="••••••••"
                  />
                </div>
                <Button
                  data-testid="login-submit-btn"
                  type="submit"
                  disabled={loading}
                  className="w-full bg-cyan-400 text-[#0A0E27] hover:bg-cyan-500 rounded-full py-6 mt-6"
                >
                  {loading ? 'Logging in...' : 'Login'}
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="register">
              <form onSubmit={handleRegister} className="space-y-4">
                <div>
                  <Label htmlFor="register-name" className="text-white">Name</Label>
                  <Input
                    data-testid="register-name-input"
                    id="register-name"
                    type="text"
                    value={registerData.name}
                    onChange={(e) => setRegisterData({ ...registerData, name: e.target.value })}
                    required
                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 mt-2"
                    placeholder="Your name"
                  />
                </div>
                <div>
                  <Label htmlFor="register-email" className="text-white">Email</Label>
                  <Input
                    data-testid="register-email-input"
                    id="register-email"
                    type="email"
                    value={registerData.email}
                    onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                    required
                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 mt-2"
                    placeholder="you@example.com"
                  />
                </div>
                <div>
                  <Label htmlFor="register-password" className="text-white">Password</Label>
                  <Input
                    data-testid="register-password-input"
                    id="register-password"
                    type="password"
                    value={registerData.password}
                    onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                    required
                    className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 mt-2"
                    placeholder="••••••••"
                  />
                </div>
                <div>
                  <Label htmlFor="register-role" className="text-white">I want to be a</Label>
                  <select
                    data-testid="register-role-select"
                    id="register-role"
                    value={registerData.role}
                    onChange={(e) => setRegisterData({ ...registerData, role: e.target.value })}
                    className="w-full bg-white/5 border border-white/10 text-white rounded-md px-4 py-2 mt-2"
                  >
                    <option value="viewer" className="bg-[#0A0E27]">Viewer ($7/month)</option>
                    <option value="streamer" className="bg-[#0A0E27]">Streamer ($100/month)</option>
                  </select>
                </div>
                <Button
                  data-testid="register-submit-btn"
                  type="submit"
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:opacity-90 rounded-full py-6 mt-6"
                >
                  {loading ? 'Creating account...' : 'Create Account'}
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
