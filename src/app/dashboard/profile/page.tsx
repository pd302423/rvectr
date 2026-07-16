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
            Muscular Fatigue Profile
          </h2>
          <div className="bg-card border border-border rounded-2xl p-6 shadow-sm">
            <div className="space-y-5">
              
              {/* Muscle Group: Chest */}
              <div>
                <div className="flex justify-between items-end mb-2">
                  <span className="text-sm font-semibold tracking-tight">Pectoralis Major</span>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-600">Fresh (0%)</span>
                </div>
                <div className="w-full bg-muted/30 rounded-full h-1.5 overflow-hidden">
                  <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: "5%" }}></div>
                </div>
              </div>

              {/* Muscle Group: Lats */}
              <div>
                <div className="flex justify-between items-end mb-2">
                  <span className="text-sm font-semibold tracking-tight">Latissimus Dorsi</span>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-rose-600">Fatigued (85%)</span>
                </div>
                <div className="w-full bg-muted/30 rounded-full h-1.5 overflow-hidden">
                  <div className="bg-rose-500 h-1.5 rounded-full" style={{ width: "85%" }}></div>
                </div>
              </div>

              {/* Muscle Group: Biceps */}
              <div>
                <div className="flex justify-between items-end mb-2">
                  <span className="text-sm font-semibold tracking-tight">Biceps Brachii</span>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-sky-600">Recovering (40%)</span>
                </div>
                <div className="w-full bg-muted/30 rounded-full h-1.5 overflow-hidden">
                  <div className="bg-sky-500 h-1.5 rounded-full" style={{ width: "40%" }}></div>
                </div>
              </div>

              {/* Muscle Group: Triceps */}
              <div>
                <div className="flex justify-between items-end mb-2">
                  <span className="text-sm font-semibold tracking-tight">Triceps Brachii</span>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-600">Fresh (10%)</span>
                </div>
                <div className="w-full bg-muted/30 rounded-full h-1.5 overflow-hidden">
                  <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: "10%" }}></div>
                </div>
              </div>

              {/* Muscle Group: Core */}
              <div>
                <div className="flex justify-between items-end mb-2">
                  <span className="text-sm font-semibold tracking-tight">Abdominals</span>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-rose-600">Fatigued (95%)</span>
                </div>
                <div className="w-full bg-muted/30 rounded-full h-1.5 overflow-hidden">
                  <div className="bg-rose-500 h-1.5 rounded-full" style={{ width: "95%" }}></div>
                </div>
              </div>

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
