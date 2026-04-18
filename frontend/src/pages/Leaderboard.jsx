import { useEffect, useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Trophy, Home, Radio, User as UserIcon, LogOut } from 'lucide-react';
import Logo from '@/components/Logo';
import axios from 'axios';

const medal = (rank) => rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : `#${rank}`;

const Leaderboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/referrals/leaderboard`).then((r) => {
      setRows(r.data.leaderboard || []);
    }).finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-[#05070F] text-white">
      <nav className="fixed top-0 w-full z-50 glass-effect px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Logo size="md" />
          <div className="flex items-center space-x-4">
            <Button data-testid="browse-nav-btn" onClick={() => navigate('/browse')} variant="ghost" className="text-white hover:text-cyan-400"><Home className="w-4 h-4 mr-2" />Browse</Button>
            <Button data-testid="live-nav-btn" onClick={() => navigate('/live')} variant="ghost" className="text-white hover:text-cyan-400"><Radio className="w-4 h-4 mr-2" />Live</Button>
            <Button data-testid="profile-nav-btn" onClick={() => navigate('/profile')} variant="ghost" className="text-white hover:text-cyan-400"><UserIcon className="w-4 h-4 mr-2" />Profile</Button>
            {user && <Button onClick={logout} variant="ghost" className="text-white hover:text-red-400"><LogOut className="w-4 h-4" /></Button>}
          </div>
        </div>
      </nav>

      <div className="pt-24 px-6 pb-12">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8 flex items-center gap-3">
            <Trophy className="w-10 h-10 text-amber-400" />
            <div>
              <h1 className="text-4xl font-bold">Referral Leaderboard</h1>
              <p className="text-gray-400">Top earners — bring the culture, earn 10% of every sub they buy.</p>
            </div>
          </div>

          {loading ? (
            <div className="flex justify-center py-12"><div className="spinner" /></div>
          ) : rows.length === 0 ? (
            <div data-testid="leaderboard-empty" className="glass-panel rounded-xl p-12 text-center">
              <Trophy className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400 text-lg mb-2">Leaderboard is empty</p>
              <p className="text-gray-500 text-sm">Be the first. Share your referral code from Profile.</p>
            </div>
          ) : (
            <div className="glass-panel rounded-xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-white/5">
                  <tr>
                    <th className="text-left p-4 text-sm text-gray-400">Rank</th>
                    <th className="text-left p-4 text-sm text-gray-400">Referrer</th>
                    <th className="text-left p-4 text-sm text-gray-400">Code</th>
                    <th className="text-right p-4 text-sm text-gray-400">Referred</th>
                    <th className="text-right p-4 text-sm text-gray-400">Earnings</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.referral_code} data-testid={`leader-${row.rank}`} className="border-t border-white/5 hover:bg-white/5">
                      <td className="p-4 text-2xl">{medal(row.rank)}</td>
                      <td className="p-4">
                        <div className="font-semibold">{row.name}</div>
                        <div className="text-xs text-gray-500 capitalize">{row.role}</div>
                      </td>
                      <td className="p-4 font-mono text-cyan-400">{row.referral_code}</td>
                      <td className="p-4 text-right">{row.referred_count}</td>
                      <td className="p-4 text-right text-green-400 font-bold text-lg">${row.earnings.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Leaderboard;
