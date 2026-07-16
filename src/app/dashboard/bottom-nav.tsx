"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

export function BottomNav() {
  const pathname = usePathname();
  
  return (
    <div className="fixed bottom-0 inset-x-0 bg-background/80 backdrop-blur-lg border-t border-border z-50 pb-safe">
      <div className="flex items-center justify-around h-16 max-w-md mx-auto px-4">
        <Link href="/dashboard" className={`flex flex-col items-center gap-1 ${pathname === '/dashboard' ? 'text-foreground' : 'text-muted-foreground'}`}>
          <div className={`w-6 h-6 rounded flex items-center justify-center ${pathname === '/dashboard' ? 'bg-foreground text-background' : 'bg-muted text-muted-foreground'}`}>
            <span className="font-mono text-xs">DB</span>
          </div>
          <span className="font-mono text-[10px] uppercase">Dashboard</span>
        </Link>
        <Link href="/dashboard/social" className={`flex flex-col items-center gap-1 ${pathname === '/dashboard/social' ? 'text-foreground' : 'text-muted-foreground'}`}>
          <div className={`w-6 h-6 rounded flex items-center justify-center ${pathname === '/dashboard/social' ? 'bg-foreground text-background' : 'bg-muted text-muted-foreground'}`}>
            <span className="font-mono text-xs">SO</span>
          </div>
          <span className="font-mono text-[10px] uppercase">Social</span>
        </Link>
        <Link href="/dashboard/profile" className={`flex flex-col items-center gap-1 ${pathname === '/dashboard/profile' ? 'text-foreground' : 'text-muted-foreground'}`}>
          <div className={`w-6 h-6 rounded flex items-center justify-center ${pathname === '/dashboard/profile' ? 'bg-foreground text-background' : 'bg-muted text-muted-foreground'}`}>
            <span className="font-mono text-xs">PR</span>
          </div>
          <span className="font-mono text-[10px] uppercase">Profile</span>
        </Link>
      </div>
    </div>
  );
}
