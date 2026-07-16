import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { BottomNav } from "../bottom-nav";
import { Settings, LogOut, Flame } from "lucide-react";

export default async function ProfilePage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  
  if (!user) redirect("/signin");

  const { data: profile } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user.id)
    .single();

  return (
    <main className="min-h-screen bg-background px-4 py-8 pb-24">
      <div className="mx-auto max-w-xl">
        <header className="mb-8 border-b border-border pb-4 flex justify-between items-start">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground mb-1">
              § Athlete Profile
            </p>
            <h1 style={{ fontFamily: "var(--font-serif)" }} className="text-3xl leading-tight tracking-tight">
              {profile?.display_name || "Athlete"}
            </h1>
          </div>
          <button className="p-2 border border-border rounded-full hover:bg-muted/50 transition-colors">
            <Settings className="w-4 h-4 text-muted-foreground" />
          </button>
        </header>

        <section className="mb-10">
          <h2 className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-4">
            Recent Muscular Fatigue
          </h2>
          <div className="bg-card border border-border rounded-2xl p-6 shadow-sm flex flex-col items-center justify-center">
            {/* Minimalist SVG Muscle Map */}
            <div className="relative w-48 h-64 border border-border/50 rounded-xl bg-muted/20 flex flex-col items-center justify-center overflow-hidden mb-6">
              <span className="font-mono text-xs text-muted-foreground absolute top-4 left-4">ANTERIOR</span>
              
              {/* Abstract Torso Map */}
              <div className="w-16 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/50 mb-1 flex items-center justify-center">
                <span className="text-[8px] font-mono font-bold text-emerald-700">CHEST (FRESH)</span>
              </div>
              <div className="flex gap-1 mb-1">
                <div className="w-6 h-12 rounded-full bg-rose-500/20 border border-rose-500/50 flex items-center justify-center">
                   <span className="text-[8px] font-mono font-bold text-rose-700 -rotate-90">BICEP</span>
                </div>
                <div className="w-12 h-16 rounded-md bg-sky-500/20 border border-sky-500/50 flex items-center justify-center">
                   <span className="text-[8px] font-mono font-bold text-sky-700">CORE (RECOVERING)</span>
                </div>
                <div className="w-6 h-12 rounded-full bg-rose-500/20 border border-rose-500/50 flex items-center justify-center">
                   <span className="text-[8px] font-mono font-bold text-rose-700 -rotate-90">BICEP</span>
                </div>
              </div>
              
            </div>
            
            <div className="flex gap-4 text-xs font-mono w-full justify-center">
              <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-emerald-500/50"></div>Fresh</div>
              <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-sky-500/50"></div>Recovering</div>
              <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-rose-500/50"></div>Fatigued</div>
            </div>
          </div>
        </section>

        <section className="mb-10">
          <h2 className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-4">
            Account Management
          </h2>
          <div className="space-y-2">
            <button className="w-full flex items-center justify-between p-4 border border-border rounded-xl hover:bg-muted/30 transition-colors">
              <span className="font-semibold text-sm">Subscription Tier</span>
              <span className="font-mono text-[10px] uppercase bg-foreground text-background px-2 py-1 rounded">rvector Pro</span>
            </button>
            <form action="/auth/signout" method="POST">
              <button type="submit" className="w-full flex items-center justify-between p-4 border border-rose-200 bg-rose-50 text-rose-700 rounded-xl hover:bg-rose-100 transition-colors">
                <span className="font-semibold text-sm">Sign Out</span>
                <LogOut className="w-4 h-4" />
              </button>
            </form>
          </div>
        </section>
      </div>
      <BottomNav />
    </main>
  );
}
