# rvector — Launch Roadmap

**Target:** $10,000 MRR by Feb 1, 2027
**Start:** Mon May 26, 2026
**Founder bandwidth:** 8–15 hrs/week
**Team:** founder (you), 1 social media marketer, 2 data partners

---

## How to use this document

Each week below is a **self-contained brief** designed to start a fresh Claude Code session cold. At the start of each new session, paste:

> *"Read ROADMAP.md. We are in **Week N** (dates). Today's session focus: [pick from the week's build deliverables]. Confirm you have context, then propose a plan before writing code."*

That single instruction loads everything Claude needs to know — the goal, the prior work, the design system, and the deliverable list.

---

## Constants — don't re-decide these

| Decision | Value |
|---|---|
| **Pricing — Pro** | $19.99 / month |
| **Pricing — Annual** | $99 / year (58% off) |
| **Free tier** | 1 graded assessment / week, squat only |
| **Stack** | Next.js 16 (App Router), Supabase, AWS Bedrock, WHAM (3D body capture) + SMPL-X body mesh + isolated GPU workers (local RTX 5060/cloud L4/T4) |
| **Design system** | Editorial premium: cream bg, serif headings, mono labels |
| **Brand voice** | Clinical, citation-heavy, no hype |
| **Primary CV exercise (launch)** | squat |
| **Launch exercises (Phase 1)** | squat, Pull-up, Plank |
| **Sender email** | `noreply@rvector.fit` (pending domain) |
| **Analytics** | PostHog |
| **Payments** | Stripe |

---

# PHASE 1 — BUILD THE VIRAL LOOP

**May 26 → Jul 6 · 6 weeks**

The product must do **one thing exceptionally**: a person opens it on their phone, performs a squat, and within 60 seconds sees an AI form score with skeleton overlay, percentile vs other users, and a one-tap share. Everything else is infrastructure.

---

## WEEK 1 · May 26 → Jun 1 · Infrastructure

**Goal:** Ship a live URL with working signup → onboarding → assessment.

### Build deliverables

1. **Resend SMTP configured in Supabase** (revoke leaked key, generate new, set custom SMTP) — see prior chat
2. **Confirm email toggle ON** in Supabase Auth → Email provider
3. **Vercel deploy from `web/` directory**
   - Connect GitHub repo
   - Set all env vars in Vercel (Production + Preview + Development scopes)
   - Required env vars: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION=us-east-1`, `RESEND_API_KEY`
4. **Domain purchased and connected** — check `rvector.fit`, `getrvector.app`, `rvectorform.ai`, `uservector.com` in that order
5. **Supabase Storage bucket** named `assessment-videos` (private, authenticated upload only, 100MB file size limit)
   - Add RLS policy: users can only upload to their own user_id folder
6. **PostHog installed** in `web/src/app/layout.tsx` — track page views, signup, paywall_hit, paid_conversion
7. **Bedrock generating real assessments** verified live (not mock) — sign up with a real email, complete onboarding, generate assessment, confirm exercises look LLM-generated

### Learn this week
- **Vercel deployment model** — read `node_modules/next/dist/docs/` for the deployment doc
- **Environment variable scoping** — Production vs Preview vs Development in Vercel
- **Supabase Storage RLS** — how `storage.objects` policies work
- **PostHog event model** — events, properties, identify

### Marketing track (your marketer's job)
- Create brand new accounts: TikTok, Instagram, YouTube — handle: `@uservector` or `@rvectorforms`
- Set bio: *"AI calisthenics coach. We grade your form. Free at [URL]."*
- Write July content calendar in a shared Google Sheet — 90 video ideas across 5 hook formats
- Profile photo + cover art (you provide editorial brand assets)

### Data partners track
- Send both partners the data spec (in prior chat)
- Set up shared Google Drive folder: `rvector/training-data/`
- Subfolders: `push_up/good/`, `push_up/bad_hip_sag/`, `push_up/bad_elbow_flare/`, etc.
- First weekly delivery target: 20 squat clips (10 good, 10 bad) by Jun 1

### Metrics (Week 1 — none yet, infrastructure only)
- ✅ Live URL responds < 1s globally
- ✅ Signup flow completes in < 60s
- ✅ Bedrock call returns valid JSON in < 8s
- ✅ Test transaction in Stripe (test mode) succeeds

### Done criteria
A friend can open your URL on their phone, sign up with their real email, confirm via Resend email, complete onboarding, generate an assessment, and see real LLM-generated exercises — all on a non-localhost URL, all in under 5 minutes.

### Session briefing template for new Claude Code sessions

> "Read ROADMAP.md. We are in Week 1 (May 26 – Jun 1). Today I want to work on [Vercel deploy / Storage bucket / PostHog / etc]. The repo is at C:\Users\Parth Dalal\FitnessApp. The codebase is Next.js 16, NOT what's in your training data — always read web/AGENTS.md and the local Next docs before writing code. Read the Week 1 section, confirm what's done vs pending, then propose a plan before writing code."

---

## WEEK 2 · Jun 2 → Jun 8 · MediaPipe Foundation

**Goal:** See live skeleton overlay on yourself doing a squat in the browser.

### Build deliverables

1. **Install MediaPipe Tasks Vision** — `@mediapipe/tasks-vision` package
2. **Create `/test/squat` page** as a client component
   - Camera permission flow (getUserMedia)
   - Video element + canvas overlay
   - 30 fps processing loop using `requestAnimationFrame`
3. **Pose Landmarker initialization** with GPU acceleration where available
4. **Skeleton overlay rendering** — draw all 33 landmarks + bone connections on canvas
5. **Joint angle utility** — `web/src/lib/cv/angles.ts`
   - `angleBetweenPoints(a, b, c)` — vector math, returns degrees
   - Helper functions: `getElbowAngle()`, `getHipAngle()`, `getKneeAngle()`, `getShoulderAngle()`
6. **Live angle readout** — small mono-font overlay showing current hip + elbow angles in real time (no scoring yet, just numbers)
7. **Mobile orientation handling** — works in both portrait and landscape

### Learn this week
- **MediaPipe Pose 33 landmarks** — memorize the index positions (0=nose, 11=left shoulder, etc.)
- **Vector math for angles** — `cos(θ) = (BA · BC) / (|BA| × |BC|)`
- **Canvas 2D coordinate system** — origin top-left, mirrored video
- **The video processing loop pattern** — read frame → predict → render → repeat
- **3Blue1Brown Neural Networks Ep 1** if you haven't

### Marketing track
- Marketer creates 10 "behind the scenes" videos: filming the build process, you explaining the science. Banked for July launch.
- Marketer writes 30 TikTok scripts in Google Sheet

### Data partners track
- Second delivery: 20 squat clips (focus on diversity — different body types, lighting, angles)
- Beginning Sunday morning, partners send weekly delivery + 1-line note on what was hard

### Metrics
- ✅ Pose detection runs at 25–30 fps on iPhone 12+ and mid-tier Android (Pixel 5+)
- ✅ Latency from frame capture to angle readout < 100ms

### Done criteria
You can open `/test/squat` on your phone, allow camera, and see your full skeleton tracking your movement at 30 fps with live elbow + hip angle readouts in mono font.

---

## WEEK 3 · Jun 9 → Jun 15 · squat Grading

**Goal:** A squat gets graded 0–100 in real time with rep counting.

### Build deliverables

1. **squat rule engine** — `web/src/lib/cv/grade-squat.ts`
   - Hip angle should stay between 165–185° throughout (any sag below 165 = penalty)
   - Elbow at bottom should reach ≤ 100° (depth requirement)
   - Body line: shoulder-hip-ankle collinearity within 10° tolerance
   - Elbow tracking: should not flare more than 60° from torso
2. **Rep counter state machine** — `web/src/lib/cv/rep-counter.ts`
   - State: `up` (elbow > 150°), `descending` (elbow decreasing), `down` (elbow < 100°), `ascending` (elbow increasing)
   - Increment count on `down → up` transition
   - Time-smoothing to avoid jitter (require state to hold for ≥150ms)
3. **Per-rep scoring** — store joint angles per rep, compute score after each rep:
   - Depth score (0–25): how close elbow got to 90°
   - Hip stability score (0–25): minimum hip angle during rep
   - Body line score (0–25): collinearity deviation
   - Tempo score (0–25): rep duration in healthy range (1.5–4s)
   - Total: sum, capped at 100
4. **Live score UI** — large mono number, updates per rep, color-coded (green > 80, amber 60–80, red < 60)
5. **Rep-by-rep breakdown panel** — list of completed reps with individual scores

### Learn this week
- **State machines for rep counting** — why a simple threshold doesn't work (jitter)
- **Temporal smoothing** — moving average, hysteresis
- **The classifier-vs-rules trade-off** — when to use ML vs deterministic rules

### Marketing track
- Marketer films first 10 TikToks using a working `/test/squat` (don't publish yet — bank them)
- Founder records 1 build-in-public Twitter thread with screenshots

### Data partners track
- Third delivery: 20 pull-up clips (you'll need these for Week 6)
- They also start labeling specific failure modes in clip filenames

### Metrics
- ✅ Rep counter accuracy ≥ 95% on 20 controlled test recordings (you do them)
- ✅ Score variance < 5 points across 3 attempts of the same person doing identical reps
- ✅ Total latency from rep completion to score displayed < 500ms

### Done criteria
You do 10 squats on camera, the counter says "10", and you can see each rep's individual score in the breakdown panel. Show this to one friend without explanation — they should understand what just happened.

---

## WEEK 4 · Jun 16 → Jun 22 · Virality Mechanics

**Goal:** The score becomes shareable in one tap.

### Build deliverables

1. **Shareable result card generator** — `web/src/app/test/squat/result-card.tsx`
   - Vertical canvas, 1080×1920px (TikTok / Story aspect)
   - Layout: serif title "squat Form Score" · huge mono score (8rem) · percentile · 3 sub-scores · subtle rvector logo
   - Background: subtle gradient from cream to white with grain texture
   - Generated client-side via HTML Canvas (no server round-trip)
   - Download as PNG button + Web Share API
2. **Web Share API integration**
   ```ts
   navigator.share({ files: [file], title: 'My rvector form score', url: 'https://rvector.fit/test/squat' })
   ```
   - Fallback for browsers that don't support file sharing: download + copy link
3. **Anonymous percentile system** — `web/src/lib/cv/percentile.ts`
   - Query: `SELECT percentile_disc(0.5) FROM logged_sets WHERE exercise_slug = 'push_up'`
   - Pre-compute deciles weekly, cache in `cv_percentiles` table
   - Return "Better than X% of users" string
4. **DB migration** for `cv_percentiles`:
   ```sql
   CREATE TABLE cv_percentiles (
     exercise_slug TEXT PRIMARY KEY,
     deciles NUMERIC[] NOT NULL, -- 10 values: 10th, 20th, ..., 100th
     updated_at TIMESTAMPTZ
   );
   ```
5. **Three exercise-specific landing pages** — `/test/squat`, `/test/pullup` (placeholder), `/test/plank` (placeholder)
   - Single CTA above the fold: *"See your form score in 60 seconds →"*
   - No nav, no other distractions
   - Auto-redirect to live grading on click
6. **Smart router** — when user lands on `/test/squat`, if they're not signed in, show inline signup that defers email confirmation until AFTER their first grade (capture the magic moment first)

### Learn this week
- **HTML Canvas 2D API** — text, gradients, images, exports
- **Web Share API** — browser support matrix, fallbacks
- **PostgreSQL percentile functions** — `percentile_disc`, `percentile_cont`
- **Activation funnels** — why deferring friction matters

### Marketing track
- Marketer records 20 "test your form" challenge videos using the shareable card output
- Hashtag strategy: `#formcheck #calisthenics #squatchallenge #aifitness`

### Data partners track
- Begin plank clips (10 good, 10 bad)
- Total deliverables by end of week: 80 clips across push/pull/plank

### Metrics
- ✅ Share card generates in < 500ms
- ✅ Web Share API works on iOS Safari 15+ and Chrome Android 90+
- ✅ Percentile loads from cache in < 50ms

### Done criteria
You do a squat set on your phone, tap "Share," and your form score card appears in the iOS share sheet ready to post directly to TikTok / IG / WhatsApp.

---

## WEEK 5 · Jun 23 → Jun 29 · Monetization

**Goal:** rvector can take a payment.

### Build deliverables

1. **Stripe account configured** — business, tax, bank, test + live keys
2. **Stripe products + prices** created via dashboard or CLI:
   - Product: "rvector Pro"
     - Price 1: $19.99/mo recurring
     - Price 2: $99/year recurring (label: "save 58%")
   - Trial: 7-day free trial on both
3. **`/pricing` page** — clean editorial layout, two columns, annual highlighted as "best value"
4. **Stripe Checkout integration** — `web/src/app/api/stripe/checkout/route.ts`
   - POST endpoint that creates a Checkout Session
   - Pass `client_reference_id = user.id`
   - Success URL: `/dashboard?upgraded=1`
   - Cancel URL: `/pricing?canceled=1`
5. **Stripe webhook handler** — `web/src/app/api/stripe/webhook/route.ts`
   - Handle: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
   - Update Supabase `profiles.subscription_status` column
6. **DB migration**:
   ```sql
   ALTER TABLE profiles ADD COLUMN
     stripe_customer_id TEXT,
     subscription_status TEXT DEFAULT 'free',  -- 'free' | 'trialing' | 'active' | 'canceled'
     subscription_period_end TIMESTAMPTZ;
   ```
7. **Paywall logic** — `web/src/lib/billing.ts`
   - `canGradeThisWeek(userId)` checks subscription + count of grades in last 7 days
   - Free users: 1 grade/week, squat only
   - Pro users: unlimited, all exercises
8. **Paywall UI** — when free user hits limit, show modal: *"You've used your free grade this week. Upgrade for unlimited."* with one big button to /pricing
9. **PostHog events**: `paywall_hit`, `pricing_view`, `checkout_started`, `paid_conversion`

### Learn this week
- **Stripe Checkout vs Elements** — when to use which
- **Webhook security** — verifying signatures
- **Subscription lifecycle states** — trialing → active → past_due → canceled
- **Idempotency** — why webhook handlers need to be idempotent

### Marketing track
- Founder writes a long-form Twitter thread: *"Building rvector — week 5 update. Stripe live, 80 squat clips trained, here's what I learned."*
- Marketer prepares 30 pricing-page screen recordings as B-roll

### Data partners track
- Continue weekly delivery; total target by end of June = 200 clips

### Metrics
- ✅ Test transaction processes end-to-end
- ✅ Webhook updates subscription_status in DB
- ✅ Paywall shows correctly for free users at limit, doesn't show for Pro users

### Done criteria
You sign up with a test card (`4242 4242 4242 4242`), complete checkout, see your dashboard say "Pro," then cancel via Stripe portal and see the dashboard revert to "Free" within 30 seconds.

---

## WEEK 6 · Jun 30 → Jul 6 · Pull-up + Plank

**Goal:** Three exercises grade reliably. Closed beta is ready to open.

### Build deliverables

1. **Pull-up rule engine** — `web/src/lib/cv/grade-pullup.ts`
   - Dead hang start: elbow angle ≥ 160° initially
   - Top of rep: chin above hand level (use nose landmark y > wrist y is approx)
   - No kipping: hip angle stays > 160° throughout (no piking)
   - Full descent: must return to ≥ 160° elbow between reps
2. **Pull-up rep counter** — same state machine pattern adapted
3. **Plank rule engine** — `web/src/lib/cv/grade-plank.ts`
   - Static hold detection: hip angle 175–185° for sustained period
   - Failure triggers: hip drops below 165° (sag) or above 195° (pike) for > 1s
   - Score = total hold duration in seconds, capped at 120s
4. **Plank UI** — different from rep-based: large stopwatch + form indicator (green/amber/red)
5. **`/test/pullup` and `/test/plank`** landing pages now live
6. **Bug bash sprint** — run through full flow 50 times, fix every reproducible bug
7. **Beta invite system** — `web/src/app/beta/page.tsx` with invite code field
   - 100 invite codes pre-generated and stored in `beta_invites` table
   - Each code can be claimed once
8. **Onboarding flow review** — measure: time from landing on `/test/squat` to first score displayed. Target: < 60s.

### Learn this week
- **Hysteresis in state machines** — avoiding rapid toggle near thresholds
- **The 80/20 of beta launches** — what to actually fix vs let slide

### Marketing track
- Marketer locks in July content calendar — 90 videos scheduled across TikTok / IG / YT
- First batch of 20 videos approved by you
- Founder writes the beta invitation email template

### Data partners track
- End of Phase 1 review: total clips delivered, quality assessment, what needs more coverage

### Metrics
- ✅ Pull-up rep counter accuracy ≥ 90% on 10 test sets
- ✅ Plank failure detection within 1s of actual failure
- ✅ < 5 reproducible bugs remaining
- ✅ Time-to-first-score under 60s for a new user

### Done criteria
Three friends can each use `/test/squat`, `/test/pullup`, `/test/plank` on their phones without any guidance from you, get a score, share a card, and tell you the experience was "smooth."

---

# PHASE 2 — CLOSED BETA

**Jul 7 → Jul 27 · 3 weeks**

**Goal:** 100 hand-picked users. 5–10 obsessed. Quote-able testimonials. NPS > 40.

---

## WEEK 7 · Jul 7 → Jul 13 · Beta Opens

### Build deliverables
- **In-app feedback widget** (e.g. Crisp or homegrown — single text box bottom-right)
- **Email automation** via Resend transactional API
  - Day 0: welcome + 2-min walkthrough video link
  - Day 1: "How was your first form score?"
  - Day 3: "Have you tried pull-ups yet?"
  - Day 7: "What would make rvector a 10/10?"
- **Admin dashboard** at `/admin` (you only) — list of beta users, their grades, their feedback
- **Bug-priority queue** in Linear, Notion, or GitHub Issues — every bug from beta lives here

### Recruit 30 beta users this week
- **DMs only — no public post yet**. Sources:
  1. 10 friends who do calisthenics
  2. 10 cold DMs to micro-creators (5K–20K) in r/bodyweightfitness, r/calisthenics
  3. 10 friends-of-friends via your existing network

### Done criteria
- 30 beta users signed up
- 25 of them complete at least one grade
- You have 5+ written feedback notes
- You've personally video-replied (Loom) to every signup

---

## WEEK 8 · Jul 14 → Jul 20 · Beta Iteration

### Build deliverables
- Ship one improvement per day based on beta feedback (7 ships minimum)
- **Friction logger** — track at which step users drop off in PostHog funnel
- **Testimonial capture form** — easy way for beta users to send video/text testimonials

### Recruit 40 more beta users
- Open one Reddit AMA-style post in **r/bodyweightfitness**: *"I built an AI form grader for calisthenics — looking for honest feedback"*
- Hand-curated reach-outs to fitness Discord servers, YouTubers, Twitter fitness niche

### Done criteria
- 70 total beta users
- 10 written feedback notes
- 3 documented "wow moments" you can quote
- 2 video testimonials in hand

---

## WEEK 9 · Jul 21 → Jul 27 · Beta Polish + Pre-launch

### Build deliverables
- **NPS survey** sent to all beta users
- **Launch waitlist** at `rvector.fit` (homepage hero) — collect emails for July 28 soft launch
- **Final bug bash** — no P1 bugs by Jul 27
- **Vercel scale check** — load test, ensure CV doesn't choke at 100 concurrent users

### Marketing prep
- Marketer's first 30 TikToks scheduled for posting Jul 28 → Aug 26 (1/day)
- ProductHunt assets prepped (we ship PH in September, but build the page now)
- Press list compiled — 30 outlets, contact emails, beat reporters

### Done criteria
- 100 beta users, 80% retention (still using weekly)
- NPS score collected
- Waitlist open
- All P1 bugs fixed
- Soft launch ready to fire

---

# PHASE 3 — SOFT LAUNCH

**Jul 28 → Sep 14 · 7 weeks**

**Goal:** $1,500 MRR · 3K signups · 200K cumulative TikTok views.

---

## WEEKS 10–16 (Jul 28 → Sep 14) · Soft Launch Operations

These are **operational weeks**, not heavy build weeks. Your time shifts from coding to growth.

### Weekly cadence (every week)

**Monday — 30 min strategic review**
- Last week's metrics in PostHog
- This week's top 3 priorities written down
- Marketing performance review (top 5 videos, top 5 underperformers)

**Tuesday — 30 min marketer sync**
- Review next week's content calendar
- Approve hooks for top-funnel videos
- Spot-check captions, hashtags, posting times

**Wednesday — 15 min data partners sync**
- Confirm weekly clip delivery received
- Flag any quality issues
- Plan next week's labeling focus

**Thursday — 4 hr build session with Claude**
- Pick one improvement from the priority queue
- Ship it before end of session
- Always batch coding into one block — not 30 min/day

**Friday — 1 hr customer touchpoints**
- DM 5 active users with a question
- Reply to all in-app feedback
- One Loom walkthrough to a power user thanking them

**Saturday/Sunday — buffer**

### Build priorities during soft launch (work the queue)

Pick from this list during your Thursday session:
1. **Streaks** — daily login streak counter, badge in profile
2. **Daily challenge** — one squat rep at noon, leaderboard
3. **History view** — `/history` page with all past grades + trend chart
4. **Form score trend chart** — recharts line graph showing weekly average score
5. **Profile picture upload** — small thing, big retention bump
6. **Squat grading** — fourth exercise (once data is in)
7. **Battery saver mode** — lower fps when phone gets hot
8. **iOS PWA installability** — "Add to Home Screen" prompt
9. **Onboarding video** — 30s explainer on `/welcome`
10. **Email digest** — weekly "your form scores this week" Resend automation

### Marketing operations (your marketer)

- **3 TikToks / day** — non-negotiable. Cross-post to IG Reels + YT Shorts (zero extra work).
- **1 Reddit post / week** — r/bodyweightfitness or r/calisthenics, thoughtful, not promotional
- **Reply to every comment** on TikTok within 4 hours
- **DM every TikTok user who comments asking how it works** with the link to `/test/squat`

### Data partners during soft launch

- Shift focus from raw clips to **edge cases** — unusual body types, lighting, common mistakes
- Total goal by end of soft launch: 500 labeled clips across 4 exercises
- This builds the foundation for v2 ML model (post-launch)

### Metrics targets — end of soft launch (Sep 14)

| Metric | Target |
|---|---|
| Signups | 3,000 |
| Paying users | 100 |
| MRR | $1,500 |
| TikTok views (cumulative) | 200,000 |
| Videos > 50K views | 10 |
| Discord members | 250 |
| Reddit karma in fitness subs | 5,000+ |

---

# PHASE 4 — FULL LAUNCH

**Sep 15 → Oct 31 · 6 weeks**

**Goal:** $5,000 MRR · 8K signups · paid acquisition working.

---

## WEEK 17 · Sep 15 → Sep 21 · ProductHunt Launch

### Pre-launch (Sep 15–16)
- Confirm PH page polished
- Pre-warm 100 supporters via DM (NO public post yet) — *"PH launch Tuesday, mind upvoting in the first hour?"*
- Submit for **Tuesday Sep 17, 12:01 AM PST** launch

### Launch day (Sep 17)
- 6 AM: Founder posts on Twitter, LinkedIn, Reddit (where allowed)
- 8 AM: Marketer posts launch announcement on all socials with link
- All day: Reply to every PH comment within 30 min
- Goal: Top 5 of the day

### Post-launch (Sep 18–21)
- Send launch summary email to waitlist
- Cross-post to Hacker News (Show HN), Indie Hackers
- Apply to ProductHunt's "Maker of the Week"

### Metrics this week
- 300+ upvotes on PH
- 800–1,500 signups from PH alone
- $300–800 MRR boost from launch buyers

---

## WEEK 18 · Sep 22 → Sep 28 · Micro-Influencer Wave 1

### Build deliverables
- **Affiliate tracking system** — `affiliate_codes` table, `?ref=` URL handling, 30% rev share per Stripe payment
- **Affiliate dashboard** for influencers — see clicks, signups, earnings

### Outreach
- DM **50 fitness micro-influencers** (5K–50K followers) on IG + TikTok
- Personalized pitch: *"Hey [name], I built an AI form grader specifically for [their niche]. Free Pro account + 30% rev share — no minimum follower count needed, just want creators we love to try it."*
- Expected: 15 yeses, 5 actually post in week 1

### Metrics
- 10 affiliate signups
- 3 affiliate posts published
- 500 referrals from affiliates

---

## WEEK 19 · Sep 29 → Oct 5 · Paid Ads Test

### Build deliverables
- **UTM parameter handling** on all signups
- **Cost-per-signup tracking** in PostHog
- **CAC calculation script** — `web/scripts/cac.ts` outputs CAC and LTV daily

### Ads operations (your marketer)
- $500/week test budget on TikTok Ads Manager
- Boost the top 3 organic videos as paid (Spark Ads — uses your real videos)
- Target: 18–35, fitness interests, US + UK + AU
- Pause anything with CAC > $20

### Metrics
- CAC ≤ $15 → scale
- CAC $15–25 → tune creative
- CAC > $25 → pause and rethink

---

## WEEK 20–22 (Oct 6 → Oct 31) · Scale

If paid ads work in Week 19, scale to **$2,000/week** ad spend.

### Build priorities (work the queue, 4 hours/week)
1. **Squat grading**
2. **Subscription cancellation flow** — survey, win-back offer
3. **Win-back email automation** — Day 14 of canceled, *"Come back, 50% off next month"*
4. **Referral program** — give a free month, get a free month
5. **Trust signals on pricing page** — testimonials, count of grades performed
6. **Mobile app announcement banner** — "iOS app coming Q1 2027" to capture demand

### Metrics targets — end of October
| Metric | Target |
|---|---|
| Signups (cumulative) | 8,000 |
| Paying users | 250 |
| MRR | $5,000 |
| CAC | < $15 |
| LTV / CAC | > 3 |

---

# PHASE 5 — REGIONAL EXHIBITION + JAPAN

**Nov 1 → Nov 30 · 4 weeks**

**Goal:** $8,000 MRR · double press exposure (regional + Japan).

---

## WEEK 23 · Nov 1 → Nov 7 · Regional Exhibition

### Action items
- **Final exhibition prep** — booth, printed materials, demo phones charged
- **Press release** sent to 30 outlets the morning of the exhibition
- **Live demo recorded** for socials
- **Win the regional** (if possible)

### After the exhibition
- **Press release V2** — "[Your name] wins regional science exhibition with AI calisthenics coach"
- Reach out to local + niche fitness outlets: Barbend, T-Nation, GMB Fitness, Calisthenic Movement YT
- Pin the win to all socials

### Metrics
- 1 press piece picked up
- 1,000+ signups from PR
- $500+ MRR boost

---

## WEEK 24–26 (Nov 8 → Nov 30) · Japan Content Sprint

### You're now in Tokyo (or wherever in Japan)

### Content sprint — 30 days of Japan content
- **Daily TikTok**: filming in Japan with location context
- **Weekly Reel series**: "Japanese street calisthenics" — get a local crew using rvector
- **Long-form blog/Twitter thread**: "Building an AI fitness coach from Tokyo" — distribute to Hacker News, Indie Hackers

### Specific outreach
- **2 Japanese gym partnerships** — let them use rvector free for content rights
- **1 Japanese gymnast or street workout athlete** featured — high-trust signal
- **Reach out to Tokyo-based English-language tech press** (Tokyodev, Disrupting Japan podcast)

### Build priorities (light week — you're traveling)
- Subscription churn investigation — who's canceling, why
- One UI polish per week max

### Metrics targets — end of November
| Metric | Target |
|---|---|
| Signups (cumulative) | 12,000 |
| Paying users | 400 |
| MRR | $8,000 |
| Press pieces | 3+ |

---

# PHASE 6 — HOLIDAY PUSH

**Dec 1 → Dec 31 · 4 weeks**

**Goal:** $11,000 MRR — hit the target.

This is the biggest fitness app spending month of the year. Run aggressive promo.

---

## WEEK 27–30 (Dec 1 → Dec 31) · New Year Campaign

### Campaign: "Test Your 2026 Starting Strength"

- **Annual plan promo** — $49 for first year (50% off the already-discounted $99) — limit to first 200 sign-ups
- **Email campaign** to entire signup list (~12K people) — *"Where will you be by March?"*
- **Content series** — 5 TikToks each showing predicted progression based on starting form score
- **Affiliate push** — bonus 50% rev share for December
- **Black Friday flash sale** (Nov 29) — pre-positioned, $29 first year, 24 hours only

### Build priorities
- **Year-end report** generator — auto email each user their 2026 stats
- **Resolution tracker** — let users set a goal for end of January

### Press
- **Year-end retrospective post** — *"What we learned building rvector in 2026"* — push to HN, IH, Twitter

### Metrics targets — end of December
| Metric | Target |
|---|---|
| Signups (cumulative) | 18,000 |
| Paying users | 550 |
| MRR | $11,000 ✅ |

---

# PHASE 7 — NATIONAL + STABILIZE

**Jan 1 → Jan 31, 2027 · 5 weeks**

**Goal:** $14,000+ MRR · National exhibition press · retention focus.

---

## WEEKS 31–35 (Jan 2027) · National + Retention

### National exhibition (mid-Jan)
- **Mainstream press push** — actual newspapers, TV if possible
- **The story now is the journey**: "From science exhibition to 18,000 users in 8 months"
- **Investor inbound** likely starts — have a one-pager ready

### Build priorities — shift to retention
- **Cohort retention analysis** — who churns, when, why
- **Email re-engagement** for inactive users (14d, 30d, 60d)
- **Progressive milestones** — celebrate every 10 reps milestone, share-worthy
- **Stop building new features** unless they fix a known retention problem

### Metrics targets — end of January
| Metric | Target |
|---|---|
| Signups | 25,000 |
| Paying users | 700 |
| MRR | $14,000+ |
| Monthly churn | < 8% |
| LTV / CAC | > 4 |

---

# CRITICAL-PATH DEPENDENCIES

These are the dominoes. If one falls late, everything after it slips.

| Domino | Latest acceptable date | Why |
|---|---|---|
| Vercel deploy live | Jun 1 | Marketer can't post until URL exists |
| MediaPipe working | Jun 15 | Whole product depends on this |
| Stripe live | Jun 29 | Can't take money without it |
| Closed beta opens | Jul 7 | Need 3 weeks of feedback before public |
| Soft launch | Jul 28 | Marketer's calendar is locked to this |
| ProductHunt | Sep 17 | Tuesday slot reserved |
| Regional exhibition | Nov 1–7 | School-set date |
| New Year campaign | Dec 1 | Annual fitness spending peak |

---

# DECISION POINTS

Build in deliberate checkpoints to avoid sunk-cost thinking.

### Sep 14 (end of soft launch)
- **If MRR > $2K**: stay the course, scale ad spend
- **If MRR < $500**: stop, re-evaluate the product. Likely the CV grading isn't perceived as magical enough — fix the wow moment

### Oct 31 (end of full launch)
- **If MRR > $5K**: ready for big PR push, you're on track
- **If MRR < $2K**: kill paid ads, focus on organic + product

### Dec 31 (target month)
- **If MRR > $10K**: ✅ press hard, ride momentum into January
- **If MRR < $7K**: not failure — adjust IB timeline expectation, keep building

---

# OPEN DECISIONS — make these THIS WEEK

| Decision | Options | Default |
|---|---|---|
| **Domain** | rvector.fit / getrvector.app / rvectorform.ai / uservector.com | Buy whatever's available, in that order |
| **Friend / future CEO equity** | Co-founder now vs advisor → CEO | Co-founder now with 4-yr vest, 1-yr cliff |
| **Marketer compensation** | Cash only / cash + equity / equity only | Cash + small equity grant (2–4%) |
| **Data partners** | Contractors / co-founders | Contractors, paid per delivery |
| **Office of record** | Personal / LLC / Delaware C-Corp | LLC now, Delaware C-Corp at $50K MRR |
| **Bank account** | Personal / business | Open business banking with Mercury or Wise this week |

---

# RESOURCE BUDGET

Monthly spend forecast through the program:

| Item | Jun–Jul | Aug–Sep | Oct–Nov | Dec–Jan |
|---|---|---|---|---|
| Vercel | $0 (free) | $20 | $20 | $20 |
| Supabase | $0 (free) | $25 (Pro) | $25 | $25 |
| Bedrock | $5 | $15 | $30 | $50 |
| Resend | $0 (free) | $20 | $20 | $20 |
| PostHog | $0 (free) | $0 (free) | $0 (free) | $0 (free) |
| Stripe | $0 (transactional only) | — | — | — |
| TikTok ads | $0 | $0 | $2,000 | $2,000 |
| Marketer | $varies | $varies | $varies | $varies |
| **Total infra** | **~$5** | **~$80** | **~$2,100** | **~$2,115** |

---

# THE ONE THING TO REMEMBER

You are not racing to $10K MRR. You are building the muscle of a startup operator. Every week, you ship one thing, you talk to users, you watch metrics. Months compound.

If you treat each Claude Code session as a focused, scoped build sprint with a clear "done" criterion, you'll move faster than 95% of founders trying to do everything at once.

**Next session brief**: *"Read ROADMAP.md. We are in Week 1. Today I want to deploy to Vercel. Confirm context, propose a plan."*
