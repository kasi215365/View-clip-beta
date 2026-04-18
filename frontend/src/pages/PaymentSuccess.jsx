import { useEffect, useState, useContext, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { CheckCircle, Loader2, XCircle } from 'lucide-react';
import Logo from '@/components/Logo';
import axios from 'axios';

const PaymentSuccess = () => {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const sessionId = params.get('session_id');
  const { fetchUser } = useContext(AuthContext);
  const [status, setStatus] = useState('checking'); // checking | paid | expired | error
  const [details, setDetails] = useState(null);
  const attempts = useRef(0);

  useEffect(() => {
    if (!sessionId) {
      setStatus('error');
      return;
    }
    poll();
  }, [sessionId]);

  const poll = async () => {
    const max = 8;
    const delay = 2000;
    if (attempts.current >= max) {
      setStatus('error');
      return;
    }
    attempts.current += 1;
    try {
      const res = await axios.get(`${API}/payments/checkout/status/${sessionId}`);
      setDetails(res.data);
      if (res.data.payment_status === 'paid') {
        setStatus('paid');
        await fetchUser();
        return;
      }
      if (res.data.status === 'expired') {
        setStatus('expired');
        return;
      }
      setTimeout(poll, delay);
    } catch (e) {
      setTimeout(poll, delay);
    }
  };

  return (
    <div className="min-h-screen bg-[#05070F] text-white flex items-center justify-center px-6">
      <div className="max-w-lg w-full glass-panel rounded-2xl p-10 text-center">
        <div className="flex justify-center mb-6">
          <Logo size="md" />
        </div>
        {status === 'checking' && (
          <div data-testid="payment-checking">
            <Loader2 className="w-16 h-16 text-cyan-400 animate-spin mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-2">Confirming payment…</h2>
            <p className="text-gray-400">Session: {sessionId?.slice(0, 14)}…</p>
          </div>
        )}
        {status === 'paid' && (
          <div data-testid="payment-success">
            <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-2">Payment Successful</h2>
            <p className="text-gray-400 mb-6">
              {details?.purpose === 'subscription'
                ? 'Your subscription is now active.'
                : details?.purpose === 'gift_bundle'
                ? 'Your gift bundle has been credited to your wallet.'
                : 'Payment confirmed.'}
            </p>
            <div className="flex gap-3 justify-center">
              <Button data-testid="go-profile-btn" onClick={() => navigate('/profile')} className="bg-cyan-400 text-[#05070F] hover:bg-cyan-300">
                Profile
              </Button>
              <Button data-testid="go-browse-btn" onClick={() => navigate('/browse')} className="bg-white/10 hover:bg-white/20">
                Browse
              </Button>
            </div>
          </div>
        )}
        {status === 'expired' && (
          <div data-testid="payment-expired">
            <XCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-2">Session Expired</h2>
            <Button onClick={() => navigate('/profile')} className="bg-cyan-400 text-[#05070F]">Back to Profile</Button>
          </div>
        )}
        {status === 'error' && (
          <div data-testid="payment-error">
            <XCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-2">Could not verify payment</h2>
            <p className="text-gray-400 mb-6">Check your email for confirmation or try again.</p>
            <Button onClick={() => navigate('/profile')} className="bg-cyan-400 text-[#05070F]">Back to Profile</Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default PaymentSuccess;
