# 🎙️ 2-3 Minute Hackathon Presentation Plan & Speaker Notes

This guide provides a high-impact, chronological script and interface action plan designed to nail your hackathon presentation in under 3 minutes.

---

## ⏱️ Timeline at a Glance

| Segment | Time | Focus | Interface Action | Spoken Goal |
| :--- | :--- | :--- | :--- | :--- |
| **0. The Hook** | 0:00 - 0:25 | Welcome & Lihai's Editorial | Start on the React landing page. Click **"📰 Data Journalism Editorial"** | Ground the project in real-world civic impact. |
| **1. The Platform** | 0:25 - 1:00 | The 17 Cards & Filters | Close tab, click **"🖥️ Start Pitch Mode"** | Show how you consolidated messy drafts into a production platform. |
| **2. Case Studies** | 1:00 - 1:50 | Timetable, Heatmap, Poisson | Click **"Next ▶"** through Steps 1, 2, and 3 | Walk through three high-signal data science stories. |
| **3. SLA & Detours** | 1:50 - 2:20 | Violations & Geofencing | Click **"Next ▶"** through Steps 4 and 5 | Pitch the business model: automated compliance auditing. |
| **4. Standalone Maps** | 2:20 - 2:45 | TLV Speed & Bunching | Click **"🗺️ TLV Bus Speed Map"** in header | Show the massive, full-scale TLV telemetry dashboards. |
| **5. The Appendix** | 2:45 - 3:00 | Source Material & Wrap | Close tab, scroll to bottom to show **Source Material** | Prove 100% reproducibility and collaboration. |

---

## 🗣️ Step-by-Step Script & Actions

### 0. The Hook & Civic Grounding (0:00 - 0:25)
* **Setup:** Start on the main React page. 
* **Action:** Direct the audience's attention to the header, and click the blue **"📰 Data Journalism Editorial"** button. This opens Lihai's article in a new tab.
* **Spoken Script:**
  > *"Good afternoon, judges. Today we are presenting the **Open Bus Shared Infra Platform**. Public transit open data is often treated as a raw, academic exercise—but we wanted to ground our research in real-world civic impact.*
  >
  > *We start with **Lihai's Data Journalism Editorial**: a long-form public narrative outlining what the open data actually shows about Israeli bus service. But Lihai's article isn't static—every chart and headline numbers is backed by a live, production-ready analytical engine we built together."*

### 1. The Production Platform (0:25 - 1:00)
* **Action:** Close Lihai's tab to return to the React dashboard. Point to the **"Lines: 142"** and **"Operators: דן"** filters. Then, click the orange **"🖥️ Start Pitch Mode"** button.
* **Spoken Script:**
  > *"When we started this hackathon, we each had separate, messy Jupyter notebooks and drafts. Instead of presenting isolated slides, we consolidated all of our work into **one unified, real-time dashboard carrying 17 registered analyses**.*
  >
  > *When we change a single filter—like **Line 142 of Dan**—every single card, map, and heatmap synchronizes instantly. To walk you through our discoveries, we built **Pitch Mode** directly into our interface."*

### 2. Narrative Case Studies: From Timetable to Poisson Decay (1:00 - 1:50)
* **Action:** Click **"Next ▶"** on the Pitch Bar to go to **Step 1 (Optimistic Timetable)**. The screen will automatically scroll and flash-highlight the Segment Reliability card.
* **Spoken Script:**
  > *"Our first discovery is **The Optimistic Timetable**. In 'Where the timetable is optimistic', we compare GTFS scheduled times against actual GPS arrivals. We immediately see that schedulers are chronically optimistic about intermediate segments, leaving no margin for traffic.*
* **Action:** Click **"Next ▶"** to go to **Step 2 (Rush Hour Breakdown)**. The screen scrolls and flashes the Heatmap. Hover over a dark red cell to show the new tooltip formatting.
* **Spoken Script:**
  > *How do those delays form? In 'Which segments break down at rush hour', we continuously map travel-time ratios. We can see the exact segments that collapse during the morning rush hour. Hovering over a cell shows you not just the ratio, but the **exact observed actual vs. planned minutes—and even seconds—lost**.*
* **Action:** Click **"Next ▶"** to go to **Step 3 (Regularity Decay)**. The screen scrolls and flashes Yuval's Poisson card.
* **Spoken Script:**
  > *As these delayed buses travel downstream, headway spacing decays. In Yuval’s **Poisson Arrival Regularity** card, we map the headway Coefficient of Variation ($C_v$). Buses leave the origin perfectly spaced, but by the end of the route, $C_v$ approaches `1.0`—indicating fully random, exponential Poisson spacing. The schedule is completely lost."*

### 3. Business Model: Automated SLA Auditing (1:50 - 2:20)
* **Action:** Click **"Next ▶"** to go to **Step 4 (SLA Audits)**. The screen scrolls and flashes the Service Violations card.
* **Spoken Script:**
  > *"This headway decay leads directly to severe bus bunching and contractual SLA infractions. In Israel, operators are heavily fined by the Ministry of Transport for early departures and cancellations.*
  >
  > *We built an **Automated SLA Audit Tool** that scans GPS pings on the fly. It filters out pre-departure boarding pings to prevent false alarms, and flags exact early departures, late terminal starts, and cancelled ghost rides. This is a ready-to-use contract enforcement platform for municipalities."*
* **Action:** Click **"Next ▶"** to go to **Step 5 (Route Divergences)**. The screen scrolls and flashes the Divergence map.
* **Spoken Script:**
  > *If a bus takes an unauthorized detour, our geofencing algorithm detects route divergence, plotting the exact physical streets where the driver strayed from the GTFS shape."*

### 4. Standalone Tel Aviv Dashboards (2:20 - 2:45)
* **Action:** Scroll to the top and click the blue **"🗺️ TLV Bus Speed Map"** button. This opens the speed map in a new tab.
* **Spoken Script:**
  > *"Finally, to show the scale of our data engine, we integrated two full-scale interactive Tel Aviv dashboards. This is our **Bus Speed Map**, analyzing door-to-door speeds across every street in Tel Aviv for **over 100,000 rides**. It calculates exactly how many 'bus-minutes' are lost in gridlock, showing planners exactly where a bus lane is economically justified."*

### 5. Open Source Collaboration & Wrap (2:45 - 3:00)
* **Action:** Close the Speed Map tab. Scroll to the absolute bottom of the React dashboard to display the **"Source Material"** appendix. Expand one of the files (e.g. `open_bus_poisson_analysis_all_in_one.ipynb`) to show the code cell rendering.
* **Spoken Script:**
  > *"To ensure 100% data transparency and peer reproducibility, we built a **Source Material appendix** at the bottom of the page. It connects server-side to fetch our original Jupyter notebooks, scripts, and static drafts—displaying our raw research side-by-side with our final interactive cards.*
  >
  > *We didn't just build a dashboard; we built a collaborative data infrastructure for public transit accountability. Thank you, and we welcome your questions!"*

---

### 💡 Pro Presenter Tips for the Q&A Session:
1. **"Why do we see different sample sizes in the Heatmap?"**
   * *Answer:* "Our data doesn't hide telemetry realities. Dropouts are due to poor cellular reception or cellular canyons. Furthermore, buses passing too quickly between 30-second SIRI pings skip the narrow geofences of intermediate stops, which naturally drops their sample sizes."
2. **"How do you resolve ambiguous line numbers?"**
   * *Answer:* "We engineered a geographical dropdown filter 'City / route contains'. By choosing a city like 'תל אביב', our backend automatically resolves the correct line variant, preventing the uvicorn API from mixing up routes."
3. **"Can we scan more days?"**
   * *Answer:* "Yes! To prevent heavy network loads during a live demo, we sample two weekdays by default, but we've built a 'Max days' option directly onto the bunching card so you can disable sampling and scan the entire date window on the fly."
