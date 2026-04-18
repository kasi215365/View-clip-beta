import { useEffect, useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Bell } from 'lucide-react';
import axios from 'axios';

/**
 * Small bell icon with unread count badge. Polls /api/notifications every 30s.
 */
export const NotificationBell = () => {
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (!user) return undefined;
    const load = async () => {
      try { const r = await axios.get(`${API}/notifications`); setUnread(r.data.unread_count || 0); }
      catch (e) { /* noop */ }
    };
    load();
    const iv = setInterval(load, 30000);
    return () => clearInterval(iv);
  }, [user]);

  if (!user) return null;

  return (
    <Button
      data-testid="notif-bell-btn"
      onClick={() => navigate('/notifications')}
      variant="ghost"
      className="relative text-white hover:text-cyan-400"
    >
      <Bell className="w-5 h-5" />
      {unread > 0 && (
        <span data-testid="notif-bell-count" className="absolute -top-1 -right-1 bg-fuchsia-500 text-white text-[10px] rounded-full px-1.5 min-w-[18px] h-[18px] flex items-center justify-center font-bold">
          {unread > 99 ? '99+' : unread}
        </span>
      )}
    </Button>
  );
};

export default NotificationBell;
