import { useStore } from './store';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ConfigPanel from './components/ConfigPanel';
import GeneratingPanel from './components/GeneratingPanel';
import ReaderPanel from './components/ReaderPanel';
import HistoryPanel from './components/HistoryPanel';
import GenerationRunner from './components/GenerationRunner';
import ToastContainer from './components/Toast';
import LoginPanel from './components/LoginPanel';
import { useEffect, useState } from 'react';

function App() {
  const { view, token, setAuth } = useStore();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!token) {
      setChecking(false);
      return;
    }
    fetch('/api/auth/me', {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => {
      if (!r.ok) {
        useStore.getState().logout();
      }
      setChecking(false);
    }).catch(() => setChecking(false));
  }, [token]);

  if (checking) {
    return (
      <div className="h-screen flex items-center justify-center bg-ink-950">
        <div className="text-ink-500">加载中...</div>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="h-screen flex flex-col bg-ink-950">
        <ToastContainer />
        <div className="flex-1 flex items-center justify-center">
          <LoginPanel onLogin={(t, u) => setAuth(t, u)} />
        </div>
      </div>
    );
  }

  const renderContent = () => {
    switch (view) {
      case 'config':
        return <ConfigPanel />;
      case 'generating':
        return <GeneratingPanel />;
      case 'reading':
        return <ReaderPanel />;
      case 'history':
        return <HistoryPanel />;
      default:
        return null;
    }
  };

  return (
    <div className="h-screen flex flex-col bg-ink-950">
      <GenerationRunner />
      <ToastContainer />
      <Header />
      <div className="flex-1 flex overflow-hidden">
        {view === 'generating' || view === 'reading' ? <Sidebar /> : null}
        <main className="flex-1 overflow-auto">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}

export default App;
