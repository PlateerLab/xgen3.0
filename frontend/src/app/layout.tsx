import type { Metadata } from 'next';
import { Toaster } from 'react-hot-toast';
import Sidebar from './_common/components/Sidebar';
import './globals.css';

export const metadata: Metadata = {
  title: 'XGEN 3.0',
  description: '대화 기반 AI Agent Runtime 플랫폼',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>
        <Sidebar />
        <main
          style={{
            marginLeft: 260,
            minHeight: '100vh',
            transition: 'margin-left 0.2s ease',
          }}
        >
          {children}
        </main>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 3000,
            style: {
              fontSize: '0.875rem',
              borderRadius: '0.5rem',
            },
          }}
        />
      </body>
    </html>
  );
}
