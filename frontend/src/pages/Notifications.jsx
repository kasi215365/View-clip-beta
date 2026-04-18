import { useEffect, useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Bell, Home, Radio, User as UserIcon, LogOut, CheckCheck, Gift, UserPlus, Radio as LiveIcon, Trophy, ShieldAlert } from 'lucide-react';
import Logo from '@/components/Logo';
import axios from 'axios';
import { toast } from 'sonner';

const icon = (type) => {
  if (type === 'gift_received') return <Gift className="w-5 h-5 text-fuchsia-400" />;
  if (type === 'new_follower') return <UserPlus className="w-5 h-5 text-cyan-400" />;
  if (type === 'stream_live') return <LiveIcon className="w-5 h-5 text-red-400" />;
  if (type === 'referral') return <Trophy className="w-5 h-5 text-amber-400" />;
  if (type === 'security_anomaly') return <ShieldAlert className="w-5 h-5 text-red-500" />;
  return <Bell className="w-5 h-5 text-gray-400" />;
};

const Notifications = () => {
  const navigate = useNavigate();
  const { logout } = useContext(AuthContext);
  const [notifs, setNotifs] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchNotifs = async () => {
    try {
      const r = await axios.get(`${API}/notifications`);
      setNotifs(r.data.notifications || []);
    } catch (e) { /* noop */ }
    setLoading(false);
  };

  useEffect(() => { fetchNotifs(); }, []);

  const readAll = async () => {
    try { await axios.post(`${API}/notifications/read-all`); toast.success('Marked all read'); fetchNotifs(); }
    catch (e) { toast.error('Failed'); }
  };

  const readOne = async (id) => {
    try { await axios.post(`${API}/notifications/${id}/read`); fetchNotifs(); } catch (e) { /* noop */ }
  };

  const openTarget = async (n) => {
    if (!n.read) await readOne(n.id);
    if (n.type === 'stream_live' && n.data?.stream_id) navigate(`/stream/${n.data.stream_id}`);
  };

  return (
    <div className="min-h-screen bg-[#05070F] text-white">
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Logo size="md" />
          <div className="flex items-center space-x-4">
            <Button onClick={() => navigate('/browse')} variant="ghost" className="text-white hover:text-cyan-400"><Home className="w-4 h-4 mr-2" />Browse</Button>
            <Button onClick={() => navigate('/live')} variant="ghost" className="text-white hover:text-cyan-400"><Radio className="w-4 h-4 mr-2" />Live</Button>
            <Button onClick={() => navigate('/profile')} variant="ghost" className="text-white hover:text-cyan-400"><UserIcon className="w-4 h-4 mr-2" />Profile</Button>
            <Button onClick={logout} variant="ghost" className="text-white hover:text-red-400"><LogOut className="w-4 h-4" /></Button>
          </div>
        </div>
      </nav>

      <div className="pt-24 px-6 pb-12">
        <div className="max-w-3xl mx-auto">
          <div className="mb-8 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Bell className="w-8 h-8 text-cyan-400" />
              <h1 className="text-4xl font-bold">Notifications</h1>
            </div>
            {notifs.some((n) => !n.read) && (
              <Button data-testid="read-all-btn" onClick={readAll} className="bg-cyan-400 text-[#05070F] hover:bg-cyan-300">
                <CheckCheck className="w-4 h-4 mr-2" />Mark all read
              </Button>
            )}
          </div>

          {loading ? (
            <div className="flex justify-center py-12"><div className="spinner" /></div>
          ) : notifs.length === 0 ? (
            <div data-testid="notifs-empty" className="glass-panel rounded-xl p-12 text-center">
              <Bell className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">No notifications yet</p>
            </div>
          ) : (
            <div className="space-y-2">
              {notifs.map((n) => (
                <div
                  key={n.id}
                  data-testid={`notif-${n.id}`}
                  onClick={() => openTarget(n)}
                  className={`glass-panel rounded-xl p-4 flex items-start gap-4 cursor-pointer transition-all hover:border-cyan-400/40 ${!n.read ? 'border-l-4 border-l-cyan-400' : 'opacity-60'}`}
                >
                  <div className="pt-1">{icon(n.type)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold">{n.title}</div>
                    <div className="text-sm text-gray-400">{n.body}</div>
                    <div className="text-xs text-gray-500 mt-1">{new Date(n.created_at).toLocaleString()}</div>
                  </div>
                  {!n.read && <span className="w-2 h-2 rounded-full bg-cyan-400 mt-2" />}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Notifications;
