import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { useLocation } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();
  
  // Show sidebar only on dashboard and related pages
  const showSidebar = location.pathname.startsWith('/dashboard') || 
                     location.pathname.startsWith('/history') || 
                     location.pathname.startsWith('/settings');

  return (
    <div className="min-h-screen bg-background">
      <Header showMobileMenu={showSidebar} />
      
      {showSidebar ? (
        <div className="flex min-h-[calc(100vh-4rem)]">
          <Sidebar />
          <main className="flex-1 overflow-hidden">
            {children}
          </main>
        </div>
      ) : (
        <main className="min-h-[calc(100vh-4rem)]">
          {children}
        </main>
      )}
    </div>
  );
}