import { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Shield, Lock, AlertTriangle } from 'lucide-react';
import Logo from '@/components/Logo';
import axios from 'axios';
import { toast } from 'sonner';

/**
 * Staff Portal — dedicated admin login. Distinct from the public /auth page.
 * - Uses /api/admin/auth/login (admin-role-only, every attempt audited)
 * - No public-app nav, no registration
 * - Visual language signals "restricted area"
 */
const AdminLogin = () => {
  const navigate = useNavigate();
  const { login } = useContext(AuthContext);
  const [creds, setCreds] = useState({ email: '', password: '' });
  const [step, setStep] = useState('creds'); // creds | totp
  const [totpCode, setTotpCode] = useState('');
  const [loading, setLoading] = useState(false);

  const submitCreds = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await axios.post(`${API}/admin/auth/login`, creds);
      if (res.data.require_2fa) {
        setStep('totp');
      } else {
        login(res.data.token, res.data.user);
        toast.success('Staff access granted');
        navigate('/admin');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const submitTotp = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await axios.post(`${API}/admin/auth/login`, { ...creds, totp_code: totpCode });
      login(res.data.token, res.data.user);
      toast.success('Staff access granted');
      navigate('/admin');
    } catch (error) {
      toast.error(error.response?.data?.detail || '2FA verification failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#030509] text-white relative overflow-hidden flex items-center justify-center px-6 py-12">
      {/* Matrix-grid backdrop */}
      <div
        aria-hidden="true"
        className="absolute inset-0 opacity-[0.05]"
        style={{
          backgroundImage:
            'linear-gradient(rgba(0,217,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(0,217,255,0.5) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />
      <div
        aria-hidden="true"
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse at center, rgba(236,72,153,0.08) 0%, rgba(3,5,9,0.9) 55%, #030509 100%)',
        }}
      />

      <div className="relative z-10 w-full max-w-md">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-fuchsia-500/30 to-cyan-400/20 border border-fuchsia-500/40 mb-4">
            <Shield className="w-10 h-10 text-fuchsia-300" />
          </div>
          <div className="flex items-center justify-center mb-2">
            <Logo size="md" />
          </div>
          <div className="inline-flex items-center gap-2 bg-fuchsia-500/10 text-fuchsia-300 px-3 py-1 rounded-full text-xs font-bold tracking-widest uppercase">
            <Lock className="w-3 h-3" /> Staff Portal
          </div>
          <p className="text-gray-500 text-sm mt-3">Restricted access — every login is audited.</p>
        </div>

        <div className="glass-panel rounded-2xl p-8 border border-fuchsia-500/20">
          {step === 'creds' ? (
            <form onSubmit={submitCreds} className="space-y-4">
              <div>
                <Label htmlFor="admin-email" className="text-white text-xs uppercase tracking-wider">Staff Email</Label>
                <Input
                  data-testid="admin-login-email-input"
                  id="admin-email"
                  type="email"
                  value={creds.email}
                  onChange={(e) => setCreds({ ...creds, email: e.target.value })}
                  required
                  autoComplete="email"
                  className="bg-black/40 border-fuchsia-500/20 text-white placeholder:text-gray-600 mt-2 font-mono"
                  placeholder="staff@viewclip.com"
                />
              </div>
              <div>
                <Label htmlFor="admin-password" className="text-white text-xs uppercase tracking-wider">Password</Label>
                <Input
                  data-testid="admin-login-password-input"
                  id="admin-password"
                  type="password"
                  value={creds.password}
                  onChange={(e) => setCreds({ ...creds, password: e.target.value })}
                  required
                  autoComplete="current-password"
                  className="bg-black/40 border-fuchsia-500/20 text-white placeholder:text-gray-600 mt-2 font-mono"
                  placeholder="••••••••"
                />
              </div>
              <Button
                data-testid="admin-login-submit-btn"
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-fuchsia-500 to-cyan-400 hover:opacity-90 rounded-lg py-6 mt-4 font-bold tracking-wider uppercase text-[#030509]"
              >
                {loading ? 'Authenticating…' : 'Continue'}
              </Button>
            </form>
          ) : (
            <form onSubmit={submitTotp} className="space-y-4" data-testid="admin-totp-step">
              <div className="text-center mb-4">
                <div className="text-xs text-fuchsia-300 tracking-wider uppercase mb-2">Two-Factor Authentication</div>
                <p className="text-gray-400 text-sm">Enter the 6-digit code from your authenticator app, or a recovery code.</p>
              </div>
              <Input
                data-testid="admin-totp-code-input"
                type="text"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.slice(0, 20))}
                required
                inputMode="text"
                autoComplete="one-time-code"
                maxLength={20}
                className="bg-black/40 border-fuchsia-500/20 text-white placeholder:text-gray-600 font-mono text-center text-xl tracking-[0.3em] py-6 uppercase"
                placeholder="000000  or  XXXX-XXXX-XXXX"
                autoFocus
              />
              <Button
                data-testid="admin-totp-submit-btn"
                type="submit"
                disabled={loading || totpCode.trim().length < 6}
                className="w-full bg-gradient-to-r from-fuchsia-500 to-cyan-400 hover:opacity-90 rounded-lg py-6 font-bold tracking-wider uppercase text-[#030509]"
              >
                {loading ? 'Verifying…' : 'Verify & Enter'}
              </Button>
              <p className="text-[11px] text-gray-500 text-center">
                Lost your device? Paste one of your <span className="text-fuchsia-400">recovery codes</span> — each works once.
              </p>
              <button
                type="button"
                data-testid="admin-totp-back-btn"
                onClick={() => { setStep('creds'); setTotpCode(''); }}
                className="w-full text-xs text-gray-500 hover:text-white mt-2"
              >
                ← Use a different account
              </button>
            </form>
          )}

          <div className="mt-6 pt-6 border-t border-white/5 flex items-start gap-2 text-xs text-gray-500">
            <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 text-yellow-500" />
            <span>Unauthorized access attempts are logged with IP address and reported to the security team.</span>
          </div>
        </div>

        <div className="text-center mt-6">
          <Button
            data-testid="public-portal-btn"
            onClick={() => navigate('/')}
            variant="ghost"
            className="text-gray-500 hover:text-white text-xs"
          >
            ← Back to public site
          </Button>
        </div>
      </div>
    </div>
  );
};

export default AdminLogin;
