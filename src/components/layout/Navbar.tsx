"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useBiomechanicsStore } from "@/lib/store";
import { Activity, Upload, LayoutDashboard, Video, Cpu, Users, Shield, UserCheck, Camera } from "lucide-react";

export function Navbar() {
  const pathname = usePathname();
  const { userRole, setUserRole } = useBiomechanicsStore();

  const navItems = [
    { href: "/", label: "Home", icon: Activity },
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/test/squat", label: "Live Squat CV", icon: Camera },
    { href: "/upload", label: "Upload", icon: Upload },
    { href: "/analysis", label: "Analysis", icon: Video },
    { href: "/demo", label: "3-Cam Command", icon: Cpu },
    { href: "/roster", label: "Squad Roster", icon: Users },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/80 bg-background/85 backdrop-blur-md transition-all">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8 h-16">
        {/* Brand Logo */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground font-semibold text-lg shadow-sm transition-transform group-hover:scale-105">
            r
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-lg tracking-tight font-sans text-foreground leading-none">
              rvector
            </span>
            <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest leading-none mt-1">
              Precision Biomechanics
            </span>
          </div>
        </Link>

        {/* Navigation Items */}
        <nav className="hidden md:flex items-center gap-1 bg-secondary/50 p-1 rounded-lg border border-border/40">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? "bg-background text-foreground shadow-xs font-semibold"
                    : "text-muted-foreground hover:text-foreground hover:bg-background/40"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Status Badge & Role Toggle */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setUserRole(userRole === "coach" ? "athlete" : "coach")}
            className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-lg bg-secondary border border-border hover:bg-muted text-xs font-mono transition-colors"
            title="Toggle Dual-Role Experience Engine"
          >
            {userRole === "coach" ? (
              <>
                <Shield className="h-3.5 w-3.5 text-primary" />
                <span>Coach Mode</span>
              </>
            ) : (
              <>
                <UserCheck className="h-3.5 w-3.5 text-emerald-700" />
                <span>Athlete Mode</span>
              </>
            )}
          </button>

          <Link
            href="/test/squat"
            className="inline-flex items-center justify-center gap-2 px-3.5 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-medium transition-colors shadow-xs"
          >
            <Camera className="h-3.5 w-3.5" />
            <span>Live CV Check</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
