const BASE = 'https://maayanlab.cloud/Enrichr'

const els = {
  csv: document.getElementById('csvFile'),
  geneCol: document.getElementById('geneCol'),
  lib: document.getElementById('library'),
  desc: document.getElementById('desc'),
  run: document.getElementById('runBtn'),
  loadLibs: document.getElementById('loadLibsBtn'),
  status: document.getElementById('status'),
  results: document.getElementById('results'),
  bars: document.getElementById('bars'),
  tableBody: document.getElementById('tableBody'),
  sortSelect: document.getElementById('sortSelect'),
  downloadCsv: document.getElementById('downloadCsv'),
  geneCountContainer: document.getElementById('geneCountContainer'),
  geneCountSlider: document.getElementById('geneCountSlider'),
  geneCountDisplay: document.getElementById('geneCountDisplay'),
  totalGenesDisplay: document.getElementById('totalGenesDisplay'),
}

function showStatus(msg, type = 'info') {
  els.status.classList.remove(
    'hidden',
    'border-slate-700',
    'border-cyan-500/50',
    'border-emerald-500/50',
    'border-rose-500/50',
    'text-slate-300',
    'text-cyan-300',
    'text-emerald-300',
    'text-rose-300',
    'bg-slate-800/40',
    'bg-cyan-950/30',
    'bg-emerald-950/30',
    'bg-rose-950/30'
  )
  els.status.classList.add(
    type === 'info'
      ? 'border-slate-700'
      : type === 'success'
      ? 'border-emerald-500/50'
      : type === 'warn'
      ? 'border-cyan-500/50'
      : 'border-rose-500/50',
    type === 'info'
      ? 'text-slate-300'
      : type === 'success'
      ? 'text-emerald-300'
      : type === 'warn'
      ? 'text-cyan-300'
      : 'text-rose-300',
    type === 'info'
      ? 'bg-slate-800/40'
      : type === 'success'
      ? 'bg-emerald-950/30'
      : type === 'warn'
      ? 'bg-cyan-950/30'
      : 'bg-rose-950/30'
  )
  els.status.textContent = msg
}

function hideStatus() {
  els.status.classList.add('hidden')
}

async function fetchLibraries() {
  try {
    showStatus('Fetching available libraries…')
    const res = await fetch(`${BASE}/datasetStatistics`)
    if (!res.ok) throw new Error('Failed to fetch datasetStatistics')
    const data = await res.json()
    const libs = data.statistics.map((s) => s.libraryName)
    // keep common pathway libs near the top
    const preferred = ['Reactome', 'KEGG', 'WikiPathways', 'BioPlanet', 'Pathway']
    const filtered = libs.filter((name) =>
      preferred.some((p) => name.toLowerCase().includes(p.toLowerCase()))
    )
    els.lib.innerHTML = ''
    filtered.sort().forEach((name) => {
      const opt = document.createElement('option')
      opt.value = name
      opt.textContent = name
      els.lib.appendChild(opt)
    })
    hideStatus()
    showStatus(`Loaded ${filtered.length} pathway libraries.`, 'success')
  } catch (err) {
    console.error(err)
    showStatus(`Could not load libraries: ${err.message}`, 'error')
  }
}

function readCsvGetGenes(file, geneCol) {
  return new Promise((resolve, reject) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (res) => {
        const rows = res.data
        if (!rows.length) return reject(new Error('CSV is empty.'))
        if (!(geneCol in rows[0])) return reject(new Error(`Column \"${geneCol}\" not found.`))
        const genes = Array.from(
          new Set(rows.map((r) => (r[geneCol] ?? '').toString().trim()).filter((v) => v))
        )
        if (!genes.length) return reject(new Error('No genes found in the specified column.'))
        resolve(genes)
      },
      error: (err) => reject(err),
    })
  })
}

async function addListToEnrichr(genes, description) {
  const fd = new FormData()
  fd.append('list', genes.join('\n'))
  if (description) fd.append('description', description)
  const res = await fetch(`${BASE}/addList`, { method: 'POST', body: fd })
  if (!res.ok) throw new Error('addList failed')
  const js = await res.json()
  return js.userListId
}

async function fetchExportTSV(userListId, library) {
  const params = new URLSearchParams({ userListId, filename: 'enrichr_results', backgroundType: library })
  const res = await fetch(`${BASE}/export?${params.toString()}`)
  if (!res.ok) throw new Error('export failed')
  return await res.text()
}

// Parse Enrichr export TSV into rows with desired columns
function parseEnrichrTSV(tsvText) {
  const lines = tsvText.trim().split(/\r?\n/)
  if (lines.length < 2) return []
  const header = lines[0].split('\t')
  const idx = {
    term: header.indexOf('Term') !== -1 ? header.indexOf('Term') : header.indexOf('Term Name'),
    overlap: header.indexOf('Overlap'),
    p: header.indexOf('P-value'),
    cs: header.indexOf('Combined Score'),
  }
  const rows = lines.slice(1).map((line, i) => {
    const parts = line.split('\t')
    const term = parts[idx.term] ?? ''
    const overlap = parts[idx.overlap] ?? ''
    const p = parseFloat(parts[idx.p])
    const cs = parseFloat(parts[idx.cs])
    let pathwayGenes = null,
      overlapCnt = null
    if (overlap && overlap.includes('/')) {
      const [k, m] = overlap.split('/')
      overlapCnt = parseInt(k, 10)
      pathwayGenes = parseInt(m, 10)
    }
    return {
      rank: i + 1,
      Pathway: term,
      Pathway_Genes: pathwayGenes,
      Overlap: overlapCnt,
      P_value: p,
      Combined_Score: cs,
    }
  })
  return rows.filter((r) => Number.isFinite(r.P_value) && Number.isFinite(r.Combined_Score))
}

function renderTable(rows) {
  els.tableBody.innerHTML = ''
  const top10 = rows.slice(0, 10)
  top10.forEach((r, i) => {
    const tr = document.createElement('tr')
    tr.innerHTML = `
          <td class=\"px-3 py-2 text-slate-500\">${i + 1}</td>
          <td class=\"px-3 py-2\">${r.Pathway}</td>
          <td class=\"px-3 py-2\">${r.Pathway_Genes ?? '—'}</td>
          <td class=\"px-3 py-2\">${r.Overlap ?? '—'}</td>
          <td class=\"px-3 py-2\">${r.P_value.toExponential(2)}</td>
          <td class=\"px-3 py-2\">${r.Combined_Score.toFixed(2)}</td>`
    els.tableBody.appendChild(tr)
  })
}

function renderBars(rows, topN = 20) {
  els.bars.innerHTML = ''
  const top = rows.slice(0, topN)
  const maxCS = Math.max(...top.map((r) => r.Combined_Score))
  top.forEach((r, i) => {
    const widthPct = maxCS > 0 ? (r.Combined_Score / maxCS) * 100 : 0
    const bar = document.createElement('div')
    bar.className = 'flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 mb-3'
    bar.innerHTML = `
          <div class=\"flex-shrink-0 w-8 sm:w-12 text-right text-xs text-slate-500\">${i + 1}.</div>
          <div class=\"flex-1 min-w-0\">
            <div class=\"flex flex-col sm:flex-row sm:justify-between text-xs mb-1 gap-1\">
              <div class=\"font-medium truncate pr-2\">${r.Pathway}</div>
              <div class=\"text-slate-500 flex-shrink-0\">p=${r.P_value.toExponential(
                2
              )} · CS=${r.Combined_Score.toFixed(2)}</div>
            </div>
            <div class=\"w-full bg-slate-900 rounded-full overflow-hidden\">
              <div class=\"h-3 rounded-full transition-all duration-300\" style=\"width: ${widthPct}%; background: linear-gradient(90deg, #10b981, #06d6a0); box-shadow: 0 0 10px #10b981, 0 0 20px #10b981, 0 0 30px #10b981; border: 1px solid #10b981;\"></div>
            </div>
          </div>`
    els.bars.appendChild(bar)
  })
}

function downloadCSV(rows) {
  const header = ['Pathway', 'Pathway_Genes', 'Overlap', 'P_value', 'Combined_Score']
  const lines = [header.join(',')].concat(
    rows.map((r) =>
      [
        '"' + r.Pathway.replaceAll('"', '""') + '"',
        r.Pathway_Genes ?? '',
        r.Overlap ?? '',
        r.P_value,
        r.Combined_Score,
      ].join(',')
    )
  )
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'enrichr_results.csv'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

let allGenes = []

// Handle CSV file selection - extract genes and show slider
els.csv.addEventListener('change', async () => {
  if (!els.csv.files[0]) {
    els.geneCountContainer.classList.add('hidden')
    allGenes = []
    return
  }

  try {
    showStatus('Reading CSV and extracting genes…')
    const file = els.csv.files[0]
    allGenes = await readCsvGetGenes(file, els.geneCol.value.trim())

    // Update slider with total gene count and show it
    els.totalGenesDisplay.textContent = allGenes.length
    els.geneCountSlider.max = allGenes.length
    els.geneCountSlider.value = Math.min(allGenes.length, Math.max(5, Math.min(100, allGenes.length)))
    els.geneCountDisplay.textContent = els.geneCountSlider.value
    els.geneCountContainer.classList.remove('hidden')

    showStatus(
      `Found ${allGenes.length} genes. Use slider to select how many to use for enrichment.`,
      'success'
    )
  } catch (err) {
    console.error(err)
    showStatus(`Error reading CSV: ${err.message}`, 'error')
    els.geneCountContainer.classList.add('hidden')
    allGenes = []
  }
})

let lastRows = []

async function handleRun() {
  try {
    els.run.disabled = true
    els.results.classList.add('hidden')

    if (!els.csv.files[0]) throw new Error('Please choose a CSV file.')
    if (!allGenes.length) throw new Error('No genes found. Please select a valid CSV file.')

    // Use only the selected number of genes (first N genes)
    const selectedGeneCount = parseInt(els.geneCountSlider.value)
    const genes = allGenes.slice(0, selectedGeneCount)
    // console.log('Using', genes.length, 'genes for enrichment.')

    if (genes.length < 5) throw new Error('Please provide at least 5 genes for enrichment.')
    showStatus(`Uploading ${genes.length} of ${allGenes.length} genes to Enrichr…`)
    const userListId = await addListToEnrichr(genes, els.desc.value.trim())
    showStatus('Running enrichment & fetching results…')
    const tsv = await fetchExportTSV(userListId, els.lib.value)
    const rows = parseEnrichrTSV(tsv)
    if (!rows.length) throw new Error('No enrichment results returned.')

    // Sort by p-value (asc) or combined score (desc)
    const sortByPref = () => {
      const sorted = els.sortSelect.checked
        ? [...rows].sort((a, b) => a.P_value - b.P_value)
        : [...rows].sort((a, b) => b.Combined_Score - a.Combined_Score)
      return sorted
    }
    lastRows = sortByPref()

    renderBars(lastRows)
    renderTable(lastRows)
    els.results.classList.remove('hidden')
    hideStatus()
  } catch (err) {
    console.error(err)
    showStatus(err.message || String(err), 'error')
  } finally {
    els.run.disabled = false
  }
}

// Event listeners
els.run.addEventListener('click', handleRun)
els.loadLibs.addEventListener('click', fetchLibraries)
els.sortSelect.addEventListener('change', () => {
  if (!lastRows.length) return
  const rows = els.sortSelect.checked
    ? [...lastRows].sort((a, b) => a.P_value - b.P_value)
    : [...lastRows].sort((a, b) => b.Combined_Score - a.Combined_Score)
  lastRows = rows
  renderBars(rows)
  renderTable(rows)
})
els.downloadCsv.addEventListener('click', () => {
  if (lastRows.length) downloadCSV(lastRows)
})
els.geneCountSlider.addEventListener('input', () => {
  els.geneCountDisplay.textContent = els.geneCountSlider.value
})
