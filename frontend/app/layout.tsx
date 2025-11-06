import type { Metadata } from 'next';
import './globals.css';

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
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
