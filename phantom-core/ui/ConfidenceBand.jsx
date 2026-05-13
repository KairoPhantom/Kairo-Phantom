import React, { useState, useEffect } from 'react';
import { listen } from '@tauri-apps/api/event';
import { appWindow } from '@tauri-apps/api/window';

export default function ConfidenceBand() {
  const [visible, setVisible] = useState(false);
  const [score, setScore] = useState(null);

  useEffect(() => {
    // Reposition window to bottom center of monitor
    const setupPosition = async () => {
      const monitor = await appWindow.currentMonitor();
      if (monitor) {
        const physicalSize = await appWindow.outerSize();
        const x = (monitor.size.width - physicalSize.width) / 2;
        const y = monitor.size.height - physicalSize.height - 40; // 40px from bottom
        await appWindow.setPosition({ type: 'Physical', x, y });
      }
    };
    setupPosition();

    const unlisten = listen('confidence_update', (event) => {
      setScore(event.payload);
      setVisible(true);

      // Auto dismiss after 1.5s
      setTimeout(() => {
        setVisible(false);
        // Delay hiding window to allow CSS fade animation
        setTimeout(() => appWindow.hide(), 200);
      }, 1500);
    });

    // Listen for ESC to cancel
    const handleKeyDown = async (e) => {
      if (e.key === 'Escape') {
        setVisible(false);
        await appWindow.hide();
        // Invoke rust command to cancel generation
        // invoke('cancel_generation');
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      unlisten.then(f => f());
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  if (!score) return null;

  const getStyle = () => {
    switch (score.level) {
      case 'High': return { color: '#4ade80', bg: 'rgba(20, 40, 20, 0.7)' };
      case 'Medium': return { color: '#fbbf24', bg: 'rgba(40, 30, 10, 0.7)' };
      case 'Low': return { color: '#f87171', bg: 'rgba(40, 15, 15, 0.7)' };
      default: return { color: '#fff', bg: 'rgba(30, 30, 30, 0.7)' };
    }
  };

  const style = getStyle();

  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: '18px',
      border: `1px solid ${style.color}40`,
      background: style.bg,
      backdropFilter: 'blur(10px)',
      WebkitBackdropFilter: 'blur(10px)',
      color: style.color,
      fontFamily: 'system-ui, -apple-system, sans-serif',
      fontSize: '13px',
      fontWeight: '500',
      opacity: visible ? 1 : 0,
      transform: visible ? 'translateY(0)' : 'translateY(20px)',
      transition: 'opacity 0.2s ease, transform 0.2s cubic-bezier(0.2, 0.8, 0.2, 1)',
      userSelect: 'none',
      cursor: 'default'
    }}>
      {score.message}
    </div>
  );
}
