"""Build an interactive Plotly HTML from Google Sheets.

The Google Sheet has the cities as columns (first row)
and a single variable "Salariu mediu net". The output dashboard mirrors
the layout used by build_iga_html.py.
"""

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
OUT = HERE / "salariu" / "salariu_dashboard.html"
VARIABLE = "Salariu mediu net"

# Google Sheet configuration
SPREADSHEET_ID = "1cIbwZNsg3e3o9o0MY7m2i02Fi_5JkC7RFmBcZ_3mEYc"  # Replace with actual ID from URL
GID = "924355652"  # Replace with actual tab GID from URL

# Romanian month name to number mapping
RO_MONTHS = {
    "ian": "01", "feb": "02", "mar": "03", "apr": "04",
    "mai": "05", "iun": "06", "iul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}

from _sheets import read_sheet


def parse_ro_date(date_str: str) -> str:
    """Convert Romanian date like 'ian. 2020' to '2020-01'."""
    if pd.isna(date_str):
        return None
    s = str(date_str).strip().lower()
    parts = s.replace(".", "").split()
    if len(parts) >= 2:
        month_abbr = parts[0][:3]
        year = parts[1]
        if month_abbr in RO_MONTHS:
            return f"{year}-{RO_MONTHS[month_abbr]}"
    return None


def main():
    df = read_sheet(SPREADSHEET_ID, GID).dropna(how="all")
    date_col = df.columns[0]
    if pd.api.types.is_datetime64_any_dtype(df[date_col]):
        dates = df[date_col].dt.strftime("%Y-%m").tolist()
    else:
        dates = [parse_ro_date(v) for v in df[date_col].tolist()]

    series: dict[str, dict] = {}
    for col in df.columns[1:]:
        city = str(col).strip()
        if not city or city.lower().startswith("unnamed"):
            continue
        point_map = {}
        for d, v in zip(dates, df[col].tolist()):
            if pd.isna(v):
                continue
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if fv == 0:
                continue
            point_map[d] = fv
        if not point_map:
            continue
        if len(set(point_map.values())) <= 1:
            continue
        series[city] = point_map

    all_dates = sorted({d for sm in series.values() for d in sm})
    series_out = {city: [m.get(d) for d in all_dates] for city, m in series.items()}
    payload = {VARIABLE: {"x": all_dates, "series": series_out}}

    print(f"Built 1 variable, {len(series_out)} cities, {len(all_dates)} points")
    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT}")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="utf-8" />
<title>Salariu mediu net — Dashboard interactiv</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  :root {
    --bg: #0f172a; --panel: #1e293b; --text: #e2e8f0;
    --muted: #94a3b8; --accent: #38bdf8; --border: #334155;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: var(--bg); color: var(--text); min-height: 100vh; }
  header { padding: 18px 28px; border-bottom: 1px solid var(--border); background: var(--panel); }
  header h1 { margin: 0; font-size: 20px; font-weight: 600; }
  header p { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
  main { display: grid; grid-template-columns: 320px 1fr; gap: 20px; padding: 20px 28px; }
  .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
  label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px;
          text-transform: uppercase; letter-spacing: 0.05em; }
  select, input[type="search"] { width: 100%; padding: 8px 10px; background: #0b1220;
    color: var(--text); border: 1px solid var(--border); border-radius: 6px; font-size: 13px; outline: none; }
  select:focus, input[type="search"]:focus { border-color: var(--accent); }
  .city-list { max-height: 460px; overflow-y: auto; margin-top: 8px;
    border: 1px solid var(--border); border-radius: 6px; padding: 8px; background: #0b1220; }
  .city-item { display: flex; align-items: center; gap: 8px; padding: 4px 6px;
    border-radius: 4px; cursor: pointer; font-size: 13px; }
  .city-item:hover { background: #1f2937; }
  .city-item input { accent-color: var(--accent); }
  .actions { display: flex; gap: 8px; margin-top: 10px; }
  .actions button { flex: 1; padding: 6px 10px; background: transparent; color: var(--text);
    border: 1px solid var(--border); border-radius: 6px; font-size: 12px; cursor: pointer; }
  .actions button:hover { border-color: var(--accent); color: var(--accent); }
  #plot { width: 100%; height: 72vh; min-height: 520px; background: var(--panel);
    border: 1px solid var(--border); border-radius: 8px; padding: 10px; }
  .count { color: var(--muted); font-size: 12px; margin-top: 6px; }
</style>
</head>
<body>
<header>
  <h1>Salariu mediu net — Grafice interactive</h1>
  <p>Alege una sau mai multe orașe pentru a le compara pe același grafic.</p>
</header>
<main>
  <aside class="panel">
    <label for="variable">Variabilă</label>
    <select id="variable"></select>

    <label for="filter" style="margin-top:14px;">Orașe</label>
    <input type="search" id="filter" placeholder="Caută..." />
    <div class="actions">
      <button id="selectAll">Toate</button>
      <button id="clearAll">Niciunul</button>
    </div>
    <div id="cityList" class="city-list"></div>
    <div class="count" id="count"></div>
  </aside>
  <section>
    <div id="plot"></div>
  </section>
</main>
<script>
const DATA = __DATA__;
const variableSelect = document.getElementById('variable');
const cityList = document.getElementById('cityList');
const filterInput = document.getElementById('filter');
const countEl = document.getElementById('count');

Object.keys(DATA).sort().forEach(name => {
  const opt = document.createElement('option');
  opt.value = name; opt.textContent = name;
  variableSelect.appendChild(opt);
});

let currentVar = variableSelect.value;
let selected = new Set();

const PALETTE = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf','#38bdf8','#f472b6','#a3e635','#fb7185','#fbbf24'];
function colorOf(name) {
  const cities = Object.keys(DATA[currentVar].series).sort();
  return PALETTE[cities.indexOf(name) % PALETTE.length];
}

function renderCityList() {
  const cities = Object.keys(DATA[currentVar].series).sort();
  const q = filterInput.value.trim().toLowerCase();
  cityList.innerHTML = '';
  cities.filter(n => !q || n.toLowerCase().includes(q)).forEach(name => {
    const wrap = document.createElement('label');
    wrap.className = 'city-item';
    const color = colorOf(name);
    wrap.innerHTML = `<input type="checkbox" style="accent-color:${color}" ${selected.has(name) ? 'checked' : ''} data-name="${name.replace(/"/g,'&quot;')}"/> <span style="color:${color}">${name}</span>`;
    cityList.appendChild(wrap);
  });
  cityList.querySelectorAll('input[type=checkbox]').forEach(cb => {
    cb.addEventListener('change', () => {
      const n = cb.getAttribute('data-name');
      if (cb.checked) selected.add(n); else selected.delete(n);
      drawPlot(); updateCount();
    });
  });
  updateCount();
}

function updateCount() {
  const total = Object.keys(DATA[currentVar].series).length;
  countEl.textContent = `${selected.size} / ${total} selectate`;
}

function drawPlot() {
  const v = DATA[currentVar];
  const traces = [...selected].map(name => {
    const c = colorOf(name);
    return {
      x: v.x, y: v.series[name],
      mode: 'lines+markers', name: name, connectgaps: true,
      line: { color: c }, marker: { color: c },
    };
  });
  const layout = {
    title: { text: currentVar, font: { color: '#e2e8f0' } },
    paper_bgcolor: '#1e293b', plot_bgcolor: '#0b1220',
    font: { color: '#e2e8f0' },
    margin: { l: 60, r: 20, t: 50, b: 60 },
    xaxis: { gridcolor: '#334155', title: 'Luna' },
    yaxis: { gridcolor: '#334155', title: currentVar },
    showlegend: false,
    hovermode: 'x unified',
  };
  Plotly.react('plot', traces, layout, { responsive: true, displayModeBar: false, scrollZoom: true });
}

function onVariableChange() {
  currentVar = variableSelect.value;
  selected = new Set();
  filterInput.value = '';
  renderCityList(); drawPlot();
}

variableSelect.addEventListener('change', onVariableChange);
filterInput.addEventListener('input', renderCityList);
document.getElementById('selectAll').addEventListener('click', () => {
  Object.keys(DATA[currentVar].series).forEach(n => selected.add(n));
  renderCityList(); drawPlot();
});
document.getElementById('clearAll').addEventListener('click', () => {
  selected.clear(); renderCityList(); drawPlot();
});

onVariableChange();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
