import { useState } from 'react';
import { BookOpen, User, Lock, LogIn } from 'lucide-react';
import { showToast } from './Toast';

interface LoginPanelProps {
  onLogin: (token: string, username: string) => void;
}

export default function LoginPanel({ onLogin }: LoginPanelProps) {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!username.trim()) { showToast('请输入用户名', 'error'); return; }
    if (!password.trim()) { showToast('请输入密码', 'error'); return; }
    if (isRegister && password.length < 6) { showToast('密码至少6位', 'error'); return; }

    setLoading(true);
    try {
      const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login';
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        showToast(data?.error || '操作失败', 'error');
        setLoading(false);
        return;
      }
      onLogin(data.token, data.username);
    } catch {
      showToast('网络错误', 'error');
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto p-4 sm:p-8 animate-fade-in">
      <div className="text-center mb-10">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-gold-400/20 to-gold-600/10 border border-gold-400/20 mb-4">
          <BookOpen className="w-8 h-8 text-gold-400" />
        </div>
        <h1 className="text-3xl font-bold gradient-text font-serif mb-2">墨流小说生成器</h1>
        <p className="text-ink-300 text-sm">{isRegister ? '创建新账号' : '登录你的账号'}</p>
      </div>

      <div className="space-y-4">
        <div className="bg-ink-900/50 border border-ink-800 rounded-xl p-6 glow-gold">
          <div className="space-y-4">
            <div>
              <label className="block text-ink-300 text-sm mb-2">用户名</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-600" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                  placeholder="输入用户名"
                  className="w-full bg-ink-950 border border-ink-800 rounded-lg pl-10 pr-4 py-2.5 text-ink-50 placeholder-ink-600 focus:outline-none focus:border-gold-400/50 focus:ring-1 focus:ring-gold-400/20 transition-all"
                />
              </div>
            </div>
            <div>
              <label className="block text-ink-300 text-sm mb-2">密码</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-600" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                  placeholder={isRegister ? '设置密码（至少6位）' : '输入密码'}
                  className="w-full bg-ink-950 border border-ink-800 rounded-lg pl-10 pr-4 py-2.5 text-ink-50 placeholder-ink-600 focus:outline-none focus:border-gold-400/50 focus:ring-1 focus:ring-gold-400/20 transition-all"
                />
              </div>
            </div>
          </div>
        </div>

        <button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full py-3 bg-gradient-to-r from-gold-600/80 to-gold-500/80 hover:from-gold-500 hover:to-gold-400 text-ink-950 font-bold rounded-xl transition-all glow-gold-hover transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
        >
          <span className="flex items-center justify-center gap-2">
            <LogIn className="w-5 h-5" />
            {loading ? '请稍候...' : (isRegister ? '注册' : '登录')}
          </span>
        </button>

        <p className="text-center text-ink-500 text-sm">
          {isRegister ? '已有账号？' : '没有账号？'}
          <button onClick={() => setIsRegister(!isRegister)} className="text-gold-400 hover:text-gold-300 ml-1 transition-colors">
            {isRegister ? '去登录' : '去注册'}
          </button>
        </p>
      </div>
    </div>
  );
}
