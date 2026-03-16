'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import styles from './Sidebar.module.scss';
import {
  FiMessageSquare,
  FiGrid,
  FiBox,
  FiActivity,
  FiSettings,
  FiChevronLeft,
  FiChevronRight,
  FiPlus,
} from 'react-icons/fi';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  match?: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: '대시보드', href: '/', icon: <FiGrid size={20} />, match: '^/$' },
  { label: '대화', href: '/chat', icon: <FiMessageSquare size={20} />, match: '^/chat' },
  { label: '에이전트', href: '/agents', icon: <FiBox size={20} />, match: '^/agents' },
  { label: '트레이스', href: '/trace', icon: <FiActivity size={20} />, match: '^/trace' },
  { label: '설정', href: '/settings', icon: <FiSettings size={20} />, match: '^/settings' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (item: NavItem) => {
    if (item.match) return new RegExp(item.match).test(pathname);
    return pathname === item.href;
  };

  return (
    <aside className={`${styles.sidebar} ${collapsed ? styles.collapsed : ''}`}>
      {/* Logo */}
      <div className={styles.logo}>
        <div className={styles.logoIcon}>X</div>
        {!collapsed && <span className={styles.logoText}>XGEN 3.0</span>}
      </div>

      {/* New Chat */}
      <Link href="/chat" className={styles.newChat}>
        <FiPlus size={18} />
        {!collapsed && <span>새 대화</span>}
      </Link>

      {/* Navigation */}
      <nav className={styles.nav}>
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`${styles.navItem} ${isActive(item) ? styles.active : ''}`}
            title={collapsed ? item.label : undefined}
          >
            <span className={styles.navIcon}>{item.icon}</span>
            {!collapsed && <span className={styles.navLabel}>{item.label}</span>}
          </Link>
        ))}
      </nav>

      {/* Collapse Toggle */}
      <button
        className={styles.collapseBtn}
        onClick={() => setCollapsed(!collapsed)}
      >
        {collapsed ? <FiChevronRight size={16} /> : <FiChevronLeft size={16} />}
      </button>
    </aside>
  );
}
