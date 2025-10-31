import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'GreenFrog - Sustainability Assistant',
  description: 'AI-powered sustainability chatbot with talking avatar, powered by The Matcha Initiative',
  keywords: ['sustainability', 'AI', 'chatbot', 'RAG', 'avatar', 'matcha initiative'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
