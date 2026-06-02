import { useStore } from './store';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ConfigPanel from './components/ConfigPanel';
import GeneratingPanel from './components/GeneratingPanel';
import ReaderPanel from './components/ReaderPanel';
import HistoryPanel from './components/HistoryPanel';
import GenerationRunner from './components/GenerationRunner';
import ToastContainer from './components/Toast';

function App() {
  const { view } = useStore();

  const renderContent = () => {
    switch (view) {
      case 'config':
        return (
          <div className="flex-1 overflow-y-auto p-4 sm:p-8">
            <ConfigPanel />
          </div>
        );
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
