# Quick Fix Reference - Edge Display Issues
**What Was Wrong & How It Was Fixed**

---

## The Problem (One Sentence)

Frontend JavaScript wasn't extracting the `edges` array from the API response object AND Dashboard was missing the required `week` parameter.

---

## The Fix (30 Seconds)

### Edges Page (`dashboard/templates/edges.html`)
```javascript
// ❌ BEFORE (Line 740):
this.edges = await response.json();

// ✅ AFTER:
const data = await response.json();
this.edges = data.edges;
```

### Dashboard Page (`dashboard/templates/index.html`)
```javascript
// ❌ BEFORE (Line 452):
fetch('/api/edges?min_edge=0.05')

// ✅ AFTER:
fetch(`/api/edges?week=${this.currentWeek}&min_edge=0.05&strategy=all`)
```

---

## Test It (10 Seconds)

```bash
# Open in browser:
http://localhost:5001/          # Dashboard (should show 1 edge)
http://localhost:5001/edges     # Edges page (should show 1 card)

# Hard refresh: Cmd+Shift+R (Mac) or Ctrl+F5 (Windows)
```

---

## Why It Happened

**Backend changed, frontend didn't.**

Old backend returned:
```javascript
[{edge_percentage: 18.5, qb_name: "..."}]  // Direct array
```

New backend (Strategy Aggregator) returns:
```javascript
{success: true, edges: [{edge_pct: 18.5, matchup: "..."}]}  // Wrapped object
```

Frontend was still expecting the old format.

---

## Files Changed

1. ✅ `dashboard/templates/edges.html` (4 changes)
2. ✅ `dashboard/templates/index.html` (5 changes)

Backend files: **No changes needed** - was already working!

---

## Quick Diagnosis (If It Breaks Again)

### Symptoms:
- Shows "0 opportunities" or "No edges found"
- Console error: `edges.reduce is not a function` or `Cannot read property 'forEach'`

### Check:
```bash
# 1. Test API directly
curl "http://localhost:5001/api/edges?week=7&strategy=all&min_edge=0"

# 2. Check console (F12)
# Should see: "✅ Loaded X edges" or "✅ Dashboard loaded X edges"

# 3. If API returns data but page doesn't show it:
# → Response extraction bug (not getting data.edges)

# 4. If API returns error:
# → Missing week parameter or invalid week
```

---

## Summary

| Issue | Location | Fix |
|-------|----------|-----|
| API response not extracted | `edges.html:740` | `data.edges` instead of entire response |
| Wrong field names | `edges.html:838,845,784` | `edge_pct` instead of `edge_percentage` |
| Missing week param | `index.html:452` | Add `week=${this.currentWeek}` |
| No currentWeek variable | `index.html:409` | Add `currentWeek: {{ current_week }}` |
| Table field mismatch | `index.html:327` | Rewrite table for simplified format |

---

## What to Remember

**Golden Rule:** When backend API changes format, update frontend to match.

**Debug Flow:**
1. Test API with curl → If works, issue is frontend
2. Check browser console → Shows exact error
3. Check Network tab → Shows actual API response
4. Fix data extraction → Match response structure
5. Fix field names → Match response fields

---

## Done! 🎯

Both pages now work. Check them at:
- http://localhost:5001/ (Dashboard)
- http://localhost:5001/edges (Edges page)

For full details, see: **COMPLETE_FIX_SUMMARY.md**
