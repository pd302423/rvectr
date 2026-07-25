"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Box, Activity, Video, Camera, Users, Cpu } from "lucide-react";

export function Navbar() {
  const pathname = usePathname();

  const navItems = [
    { href: "/demo", label: "3D Motion Command", icon: Box },
    { href: "/analysis", label: "Kinematic Workspace", icon: Activity },
    { href: "/test/squat", label: "Live Optical CV", icon: Camera },
    { href: "/roster", label: "Athlete Roster", icon: Users },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[#262626] bg-[#000000]/95 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8 h-14">
        {/* Brand Logo */}
        <Link href="/demo" className="flex items-center gap-3 group">
          <div className="flex h-7 w-7 items-center justify-center border border-[#ffffff] bg-[#ffffff] text-[#000000] font-bold text-xs">
            r
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-sm tracking-widest uppercase font-mono text-[#ffffff]">
              rvectr_OS
            </span>
            <span className="text-[9px] font-mono text-[#a3a3a3] uppercase tracking-widest leading-none">
              Professional Biomechanics v1.0
            </span>
          </div>
        </Link>

        {/* Navigation Items */}
        <nav className="flex items-center gap-1 bg-[#000000] p-1 border border-[#262626]">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 px-3 py-1 text-xs font-mono transition-colors ${
                  isActive
                    ? "bg-[#ffffff] text-[#000000] font-bold"
                    : "text-[#a3a3a3] hover:text-[#ffffff] hover:bg-[#171717]"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Status Badge */}
        <div className="flex items-center gap-2 border border-[#262626] px-3 py-1 font-mono text-[10px] uppercase text-[#ffffff]">
          <div className="w-1.5 h-1.5 bg-[#ffffff] animate-pulse" />
          <span>Local Engine Active</span>
        </div>
      </div>
    </header>
  );
}
