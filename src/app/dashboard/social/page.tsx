import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { BottomNav } from "../bottom-nav";
import { Heart, MessageCircle, MapPin, Share2 } from "lucide-react";

export default async function SocialFeedPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  
  if (!user) redirect("/signin");

  const MOCK_FEED = [
    {
      id: 1,
      user: "Alex K.",
      time: "2 hours ago",
      title: "Intensification Phase · Week 3",
      stats: { xp: "+450 XP", duration: "42m", volume: "12,400 kg" },
      likes: 12,
      comments: 3,
      liked: true,
      body: "Hit a new PB on weighted pull-ups (+20kg). Form felt solid until the last rep."
    },
    {
      id: 2,
      user: "Sarah M.",
      time: "5 hours ago",
      title: "Recovery Deload",
      stats: { xp: "+120 XP", duration: "25m", volume: "4,200 kg" },
      likes: 8,
      comments: 0,
      liked: false,
      body: "Just going through the motions to keep the joints healthy."
    },
    {
      id: 3,
      user: "David C.",
      time: "Yesterday",
      title: "Baseline Assessment",
      stats: { xp: "+500 XP", duration: "55m", volume: "N/A" },
      likes: 24,
      comments: 5,
      liked: false,
      body: "Just finished my initial calibration. humbled by the strict form requirements."
    }
  ];

  return (
    <main className="min-h-screen bg-background px-4 py-8 pb-24">
      <div className="mx-auto max-w-xl">
        <header className="mb-8 border-b border-border pb-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground mb-1">
            § Global Feed
          </p>
          <h1 style={{ fontFamily: "var(--font-serif)" }} className="text-3xl leading-tight tracking-tight">
            Athlete Network
          </h1>
        </header>

        <div className="space-y-6">
          {MOCK_FEED.map((post) => (
            <article key={post.id} className="bg-card border border-border rounded-2xl p-5 shadow-sm">
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-foreground text-background flex items-center justify-center font-bold text-sm">
                    {post.user.charAt(0)}
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm">{post.user}</h3>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-mono">{post.time}</p>
                  </div>
                </div>
                <div className="bg-sky-500/10 text-sky-700 dark:text-sky-300 px-2 py-1 rounded border border-sky-500/20 font-mono text-[10px] uppercase tracking-widest font-semibold">
                  {post.stats.xp}
                </div>
              </div>

              <h2 className="text-lg font-bold tracking-tight mb-2">{post.title}</h2>
              <p className="text-sm text-foreground/80 mb-4">{post.body}</p>

              <div className="grid grid-cols-2 gap-2 mb-4 bg-muted/30 rounded-xl p-3 border border-border/50">
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-mono">Time</p>
                  <p className="font-mono text-sm">{post.stats.duration}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-mono">Volume</p>
                  <p className="font-mono text-sm">{post.stats.volume}</p>
                </div>
              </div>

              <div className="flex items-center gap-6 border-t border-border pt-4">
                <button className={`flex items-center gap-1.5 text-sm font-medium transition-colors ${post.liked ? 'text-rose-500' : 'text-muted-foreground hover:text-foreground'}`}>
                  <Heart className={`w-5 h-5 ${post.liked ? 'fill-rose-500' : ''}`} />
                  <span>{post.likes}</span>
                </button>
                <button className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                  <MessageCircle className="w-5 h-5" />
                  <span>{post.comments}</span>
                </button>
                <button className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors ml-auto">
                  <Share2 className="w-4 h-4" />
                </button>
              </div>
            </article>
          ))}
        </div>
      </div>
      <BottomNav />
    </main>
  );
}
