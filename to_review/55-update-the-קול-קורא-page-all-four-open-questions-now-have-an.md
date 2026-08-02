> ### ⚠️ AI-generated draft — needs human validation
>
> This issue was **written by an AI agent** from materials produced during the
> hasadna Open Bus hackathon (July 2026). The underlying analysis was built fast,
> under hackathon conditions, and **has not been peer-reviewed**. Figures,
> endpoint behaviour and conclusions all need independent verification before
> anyone acts on them or quotes them publicly.
>
> **Please validate before implementing. Corrections very welcome.**

## What

The [public-appeal page](https://open-bus-map-search.hasadna.org.il/public-appeal)
asks the public for help with four research questions. **The hackathon answered all
four.** The page should say so, point at the answers, and ask the next question
instead.

## Question by question

### 1. איפה נדרשים נתיבי תעדוף לתחבורה ציבורית (נת״צים)?
*Where are bus priority lanes needed?*

**Answered — with a ranked, costed list.** 725 corridors ranked by bus-minutes lost
per hour; worst is Geha W-bound at **787 min/hr**, running 25.7 km/h against 62.6
free-flow. Built from 60.3M street readings. → **#43**, dashboard in **#41**

### 2. חישוב שעת היציאה מתחנת המוצא, ושעת ההגעה לתחנות השונות במסלול
*Computing departure from the origin stop and arrival at stops along the route*

**Answered, including the trap.** The API serves no actual arrival times, so they
are derived by interpolating the vehicle's closest approach to each stop (±30 s).
Critically: the obvious approach — take the first GPS ping as departure — **is
wrong**. The feed reports a vehicle ~30 or ~5 minutes before its scheduled start
while it is still parked, which makes ~90% of rides look early. → **#1778**, method
in **#1782**

### 3. איך לשייך קווי אוטובוס לאזורים גיאוגרפיים?
*How to associate bus lines with geographic areas?*

**Answered — no join required.** The ministry's own `cluster_nm` ("אשכול") ships in
the per-line ticketing dataset and is a real geographic/service grouping. An earlier
attempt to derive a distance-to-city-centre score failed because the resource it
read has no line column at all. → **#1797**

### 4. התקבצות אוטובוסים
*Bus bunching*

**Answered at scale, with causes attributed.** 127,754 consecutive pairs across 709
line-directions; 9.9% ran bunched; every event attributed to late departure (13%),
first fifth of the route (10%) or en route (73%). → **#36**, dashboard in **#35**,
rider cost in **#37**

## Also closes #1231

#1231 asks to embed a notebook about vehicle velocities into this page. The speed
dashboard (**#41**) *is* that research, at national-data scale and already
interactive — a better fit than a Colab link.

## Suggested next questions to ask the public

The hackathon surfaced questions it could not answer, which are better appeals than
the four now closed:

- **Which operators are contractually exempt from AVL reporting?** Four operators
  never appear in the tracking feed (#1780). From outside it is impossible to tell
  whether that is an exemption or a compliance failure — and it changes the national
  non-execution rate by ~2.2 points.
- **What are the actual regulatory tolerances** for early and late departure?
  #1793 had to invent thresholds because the fine schedule was not available.
- **How should unserved areas be measured?** 59% of mapped street-km in Tel Aviv has
  no bus (#44), but street-km is the wrong unit — population-weighted access is the
  right one, and nobody has built it (#50).

## Note on provenance

Every linked answer is AI-drafted from hackathon materials and carries
`needs-validation`. The public-appeal page should not present them as settled — the
honest framing is *"the hackathon produced candidate answers; help us check them"*,
which is also a better invitation.

Related: #768 (page touch-ups).

---

**Credit & provenance**
Found during the hasadna Open Bus hackathon, July 2026 — the hackathon team.
· Source material, republished with the participants' permission: [`source-material/`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/source-material/README.md)
· Per-solution write-ups: [`README.md`](https://github.com/hasadna/open-bus-hackathon-26/blob/main/algorithms/README.md)
