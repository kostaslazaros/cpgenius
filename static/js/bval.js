// --- Configure your endpoints here ---
const URL_BASE = '/bval'
const EXISTS_URL = (id) => `${URL_BASE}/exists/${encodeURIComponent(id)}`
const UPLOAD_URL = `${URL_BASE}/upload`
const IMAGES_BASE_URL = `${URL_BASE}/images`
const DOWNLOAD_ALL_URL = `${URL_BASE}/download-all`

// --- Elements ---
const inputEl = document.getElementById('folderInput')
const shaOut = document.getElementById('sha1Out')
const fileCountOut = document.getElementById('fileCountOut')
const goBtn = document.getElementById('goBtn')
const spinner = document.getElementById('spinner')
const resetBtn = document.getElementById('resetBtn')
const statusEl = document.getElementById('status')

let selectedFiles = []
let bundleId = null

function setStatus(msg, type = 'info') {
  statusEl.classList.remove(
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
  statusEl.classList.add(
    type === 'info'
      ? 'border-slate-700'
      : type === 'ok'
      ? 'border-emerald-500/50'
      : type === 'warn'
      ? 'border-cyan-500/50'
      : 'border-rose-500/50',
    type === 'info'
      ? 'text-slate-300'
      : type === 'ok'
      ? 'text-emerald-300'
      : type === 'warn'
      ? 'text-cyan-300'
      : 'text-rose-300',
    type === 'info'
      ? 'bg-slate-800/40'
      : type === 'ok'
      ? 'bg-emerald-950/30'
      : type === 'warn'
      ? 'bg-cyan-950/30'
      : 'bg-rose-950/30'
  )
  statusEl.textContent = msg
}
function clearStatus() {
  statusEl.classList.add('hidden')
  statusEl.textContent = ''
}

// ---------- Helpers ----------
function toHex(bytes) {
  const hex = []
  for (let i = 0; i < bytes.length; i++) hex.push(bytes[i].toString(16).padStart(2, '0'))
  return hex.join('')
}

// Pure-JS incremental SHA-1 (fallback when crypto.subtle is unavailable)
// Adapted minimal implementation (incremental) for Uint8Array input.
class SHA1 {
  constructor() {
    this.h0 = 0x67452301
    this.h1 = 0xefcdab89
    this.h2 = 0x98badcfe
    this.h3 = 0x10325476
    this.h4 = 0xc3d2e1f0
    this.block = new Uint8Array(64)
    this.blockBytes = 0
    this.lengthLow = 0
    this.lengthHigh = 0
  }
  _addLength(len) {
    const low = (this.lengthLow + (len << 3)) >>> 0
    const carry = low < this.lengthLow ? 1 : 0
    this.lengthLow = low
    this.lengthHigh = (this.lengthHigh + (len >>> 29) + carry) >>> 0
  }
  _processBlock(block) {
    const w = new Uint32Array(80)
    for (let i = 0; i < 16; i++) {
      w[i] = (block[i * 4] << 24) | (block[i * 4 + 1] << 16) | (block[i * 4 + 2] << 8) | block[i * 4 + 3]
    }
    for (let i = 16; i < 80; i++) {
      const n = w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16]
      w[i] = ((n << 1) | (n >>> 31)) >>> 0
    }
    let a = this.h0,
      b = this.h1,
      c = this.h2,
      d = this.h3,
      e = this.h4
    for (let i = 0; i < 80; i++) {
      let f, k
      if (i < 20) {
        f = (b & c) | (~b & d)
        k = 0x5a827999
      } else if (i < 40) {
        f = b ^ c ^ d
        k = 0x6ed9eba1
      } else if (i < 60) {
        f = (b & c) | (b & d) | (c & d)
        k = 0x8f1bbcdc
      } else {
        f = b ^ c ^ d
        k = 0xca62c1d6
      }
      const temp = (((a << 5) | (a >>> 27)) + f + e + k + w[i]) >>> 0
      e = d
      d = c
      c = ((b << 30) | (b >>> 2)) >>> 0
      b = a
      a = temp
    }
    this.h0 = (this.h0 + a) >>> 0
    this.h1 = (this.h1 + b) >>> 0
    this.h2 = (this.h2 + c) >>> 0
    this.h3 = (this.h3 + d) >>> 0
    this.h4 = (this.h4 + e) >>> 0
  }
  update(data) {
    let offset = 0
    while (offset < data.length) {
      const space = 64 - this.blockBytes
      const take = Math.min(space, data.length - offset)
      this.block.set(data.subarray(offset, offset + take), this.blockBytes)
      this.blockBytes += take
      offset += take
      if (this.blockBytes === 64) {
        this._processBlock(this.block)
        this.blockBytes = 0
      }
    }
    this._addLength(data.length)
  }
  digest() {
    // padding
    this.block[this.blockBytes++] = 0x80
    if (this.blockBytes > 56) {
      while (this.blockBytes < 64) this.block[this.blockBytes++] = 0
      this._processBlock(this.block)
      this.blockBytes = 0
    }
    while (this.blockBytes < 56) this.block[this.blockBytes++] = 0
    // length (64-bit big-endian)
    const hi = this.lengthHigh,
      lo = this.lengthLow
    this.block[56] = (hi >>> 24) & 0xff
    this.block[57] = (hi >>> 16) & 0xff
    this.block[58] = (hi >>> 8) & 0xff
    this.block[59] = hi & 0xff
    this.block[60] = (lo >>> 24) & 0xff
    this.block[61] = (lo >>> 16) & 0xff
    this.block[62] = (lo >>> 8) & 0xff
    this.block[63] = lo & 0xff
    this._processBlock(this.block)
    // output
    const out = new Uint8Array(20)
    const words = [this.h0, this.h1, this.h2, this.h3, this.h4]
    for (let i = 0; i < 5; i++) {
      out[i * 4] = (words[i] >>> 24) & 0xff
      out[i * 4 + 1] = (words[i] >>> 16) & 0xff
      out[i * 4 + 2] = (words[i] >>> 8) & 0xff
      out[i * 4 + 3] = words[i] & 0xff
    }
    return out
  }
}

const hasSubtle = typeof crypto !== 'undefined' && crypto.subtle && typeof crypto.subtle.digest === 'function'
function encoder(str) {
  return new TextEncoder().encode(str)
}

async function sha1ArrayBuffer(ab) {
  if (hasSubtle) {
    const digest = await crypto.subtle.digest('SHA-1', ab)
    return toHex(new Uint8Array(digest))
  } else {
    const hasher = new SHA1()
    hasher.update(new Uint8Array(ab))
    return toHex(hasher.digest())
  }
}

// ---------- Folder hashing ----------
async function computeBundleSha(files) {
  const filtered = Array.from(files).filter((f) => {
    const name = (f.name || '').toLowerCase()
    return name.endsWith('.csv') || name.endsWith('.idat')
  })

  if (filtered.length === 0) return { bundleId: null, items: [] }

  filtered.sort((a, b) => {
    const pa = a.name
    const pb = b.name
    return pa.localeCompare(pb)
  })

  const lines = []
  let processed = 0

  for (const f of filtered) {
    try {
      const ab = await f.arrayBuffer() // sequential read per file
      const fileSha = await sha1ArrayBuffer(ab)
      const rel = f.name
      lines.push(`${rel}\n${f.size}\n${fileSha}\n`)
    } catch (e) {
      // Surface which file failed for easier debugging
      throw new Error(`Hashing failed for "${f.name}": ${e?.message || e}`)
    }
    processed++
    if (processed % 5 === 0) setStatus(`Hashing files… ${processed}/${filtered.length}`, 'warn')
  }

  const canonical = lines.join('')
  // Hash canonical manifest text
  let bundleShaHex
  const manifestAb = encoder(canonical).buffer
  try {
    bundleShaHex = await sha1ArrayBuffer(manifestAb)
  } catch (e) {
    throw new Error(`Manifest SHA-1 failed: ${e?.message || e}`)
  }

  return { bundleId: bundleShaHex, items: filtered }
}

// ---------- Network ----------
async function checkExists(id) {
  const res = await fetch(EXISTS_URL(id), { method: 'GET' })
  if (res.ok) return true
  if (res.status === 404) return false
  const text = await res.text().catch(() => '')
  throw new Error(`Exists check failed: ${res.status} ${text}`)
}

async function uploadBundle(id, files) {
  const fd = new FormData()
  fd.append('bundle_id', id)
  fd.append('file_count', String(files.length))
  for (const f of files) {
    fd.append('files', f, f.name)
  }
  const res = await fetch(UPLOAD_URL, { method: 'POST', body: fd })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Upload failed: ${res.status} ${text}`)
  }
  return res
}

// ---------- UI wiring ----------
inputEl.addEventListener('change', async () => {
  clearStatus()
  shaOut.value = ''
  fileCountOut.value = '0'
  bundleId = null
  selectedFiles = []
  const files = inputEl.files
  if (!files || files.length === 0) {
    setStatus('No files selected.', 'info')
    return
  }

  goBtn.disabled = true
  spinner.classList.remove('hidden')
  if (!hasSubtle && !isSecureContext) {
    // Helpful hint if they were running from file:// or http
    setStatus(
      'Running in non-secure context; using JS SHA-1 fallback. Consider https:// or http://localhost for Web Crypto.',
      'warn'
    )
  } else if (!hasSubtle) {
    setStatus('Web Crypto not available; using JS SHA-1 fallback.', 'warn')
  } else {
    setStatus('Scanning folder and computing SHA-1…', 'warn')
  }

  try {
    const { bundleId: id, items } = await computeBundleSha(files)
    if (!id) {
      setStatus('No .csv or .idat files found in the selected folder.', 'info')
      return
    }
    bundleId = id
    selectedFiles = items
    shaOut.value = bundleId
    fileCountOut.value = String(selectedFiles.length)
    setStatus(`Bundle ready. ${selectedFiles.length} file(s) hashed.`, 'ok')
  } catch (err) {
    console.error(err)
    setStatus(String(err.message || err || 'Failed to compute SHA-1 for the folder.'), 'error')
  } finally {
    spinner.classList.add('hidden')
    goBtn.disabled = false
  }
})

goBtn.addEventListener('click', async () => {
  clearStatus()
  if (!bundleId || selectedFiles.length === 0) {
    setStatus('Please choose a folder first.', 'info')
    return
  }
  goBtn.disabled = true
  spinner.classList.remove('hidden')
  setStatus('Checking if this bundle already exists…', 'warn')
  try {
    const exists = await checkExists(bundleId)
    if (exists) {
      setStatus('Bundle already exists on the server. No upload needed.', 'ok')
      // Load images for existing bundle
      await loadImages(bundleId)
      return
    }
    setStatus('Not found on server. Uploading files…', 'warn')
    const uploadResponse = await uploadBundle(bundleId, selectedFiles)
    const data = await uploadResponse.json()
    console.log(data.task_id ? 'Upload task ID: ' + data.task_id : 'No task ID returned')
    setStatus('Upload complete. Bundle is now stored. Processing files...', 'ok')

    // Start polling for images after successful upload
    startImagePolling(bundleId)
  } catch (err) {
    console.error(err)
    setStatus(err.message || 'Something went wrong.', 'error')
  } finally {
    spinner.classList.add('hidden')
    goBtn.disabled = false
  }
})

resetBtn.addEventListener('click', () => {
  inputEl.value = ''
  shaOut.value = ''
  fileCountOut.value = '0'
  bundleId = null
  selectedFiles = []
  clearStatus()
  hideImagesSection()
})

// Test button for demonstrating image functionality
const testImagesBtn = document.getElementById('testImagesBtn')
if (testImagesBtn) {
  testImagesBtn.addEventListener('click', async () => {
    const testSha1 = 'e07b3e4c058ea1a32bb99898172a580fe4954e27'
    shaOut.value = testSha1
    setStatus('Loading test images...', 'warn')
    try {
      await loadImages(testSha1)
      setStatus('Test images loaded successfully!', 'ok')
    } catch (error) {
      setStatus('Error loading test images: ' + error.message, 'error')
    }
  })
}

// =============================================================================
// IMAGE GALLERY FUNCTIONALITY
// =============================================================================

// Image gallery elements
const imagesSection = document.getElementById('imagesSection')
const imageGallery = document.getElementById('imageGallery')
const noImages = document.getElementById('noImages')
const downloadAllSection = document.getElementById('downloadAllSection')
const downloadAllBtn = document.getElementById('downloadAllBtn')

// Download all button functionality
if (downloadAllBtn) {
  const downloadIcon = document.getElementById('downloadIcon')
  const downloadSpinner = document.getElementById('downloadSpinner')
  const downloadBtnText = document.getElementById('downloadBtnText')

  downloadAllBtn.addEventListener('click', async () => {
    if (!window.currentImagesSha1) {
      setStatus('No images loaded to download', 'error')
      return
    }

    try {
      // Show loading state
      downloadAllBtn.disabled = true
      downloadIcon.classList.add('hidden')
      downloadSpinner.classList.remove('hidden')
      downloadBtnText.textContent = 'Creating ZIP file...'
      downloadAllBtn.classList.add('cursor-not-allowed')
      setStatus('📦 Compressing files, please wait...', 'warn')

      const response = await fetch(`${DOWNLOAD_ALL_URL}/${window.currentImagesSha1}`)
      if (!response.ok) {
        throw new Error(`Download failed: ${response.status}`)
      }

      // Update status for download phase
      downloadBtnText.textContent = 'Downloading...'
      setStatus('⬇️ ZIP file ready, downloading...', 'warn')

      // Create download link
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `analysis_results_${window.currentImagesSha1}.zip`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      setStatus('✅ Files downloaded successfully!', 'ok')
    } catch (error) {
      setStatus('❌ Error downloading files: ' + error.message, 'error')
    } finally {
      // Restore button state
      downloadAllBtn.disabled = false
      downloadIcon.classList.remove('hidden')
      downloadSpinner.classList.add('hidden')
      downloadBtnText.textContent = 'Download All Files (ZIP)'
      downloadAllBtn.classList.remove('cursor-not-allowed')
    }
  })
}

function hideImagesSection() {
  if (imagesSection) {
    imagesSection.classList.add('hidden')
    imageGallery.innerHTML = ''
  }
  if (downloadAllSection) {
    downloadAllSection.classList.add('hidden')
  }
}

function showImagesSection() {
  if (imagesSection) {
    imagesSection.classList.remove('hidden')
  }
}

function showDownloadAllSection() {
  if (downloadAllSection) {
    downloadAllSection.classList.remove('hidden')
  }
}

async function loadImages(sha1Hash) {
  if (!sha1Hash) return

  try {
    const response = await fetch(`${IMAGES_BASE_URL}/${sha1Hash}`)
    if (!response.ok) {
      if (response.status === 404) {
        // No images yet, hide the section
        hideImagesSection()
        return
      }
      throw new Error(`Failed to load images: ${response.status}`)
    }

    const data = await response.json()

    if (data.images && data.images.length > 0) {
      renderImageGallery(data.images)
      showImagesSection()
      showDownloadAllSection()
      // Store current SHA1 for download functionality
      window.currentImagesSha1 = sha1Hash
    } else {
      hideImagesSection()
    }
  } catch (error) {
    console.error('Error loading images:', error)
    hideImagesSection()
  }
}

function renderImageGallery(images) {
  imageGallery.innerHTML = ''
  noImages.style.display = 'none'

  // Sort images by filename for consistent ordering
  const sortedImages = [...images].sort((a, b) =>
    a.filename.localeCompare(b.filename, undefined, { numeric: true, sensitivity: 'base' })
  )

  sortedImages.forEach((image) => {
    const sizeInMB = (image.file_size / (1024 * 1024)).toFixed(2)

    const imageCard = document.createElement('div')
    imageCard.className =
      'border border-cyan-600/30 rounded-xl bg-gradient-to-r from-cyan-950/30 to-blue-950/30 p-4 shadow-[0_0_15px_rgba(34,211,238,0.2)] hover:shadow-[0_0_25px_rgba(34,211,238,0.4)] transition-all duration-300'

    imageCard.innerHTML = `
      <div class="space-y-4">
        <div class="aspect-square rounded-lg overflow-hidden bg-slate-800/50 border border-cyan-500/30">
          <img src="${image.image_url}"
               alt="${image.filename}"
               class="w-full h-full object-contain cursor-pointer hover:scale-105 transition-transform duration-300"
               onclick="openImageModal('${image.image_url}', '${image.filename}')"
               loading="lazy">
        </div>
        <div class="space-y-2">
          <h4 class="text-cyan-200 font-medium text-sm leading-tight break-all">${image.filename}</h4>
          <div class="flex justify-between items-center text-xs text-slate-400">
            <span>${sizeInMB} MB</span>
            <span>${new Date(image.created_time * 1000).toLocaleDateString()}</span>
          </div>
          <a href="${image.image_url}"
             download="${image.filename}"
             class="block w-full text-center px-3 py-2 text-sm font-medium text-cyan-200 bg-gradient-to-r from-cyan-900/50 to-blue-900/50 hover:from-cyan-800/70 hover:to-blue-800/70 border border-cyan-500/50 hover:border-cyan-400 rounded-lg transition-all duration-200 shadow-[0_0_15px_rgba(34,211,238,0.3)] hover:shadow-[0_0_25px_rgba(34,211,238,0.5)]">
            <svg class="w-4 h-4 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
            Download
          </a>
        </div>
      </div>
    `

    imageGallery.appendChild(imageCard)
  })

  if (images.length === 0) {
    noImages.style.display = 'block'
  }
}

function openImageModal(imageUrl, filename) {
  // Create modal overlay
  const modal = document.createElement('div')
  modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4'
  modal.onclick = () => modal.remove()

  // Create modal content
  const modalContent = document.createElement('div')
  modalContent.className =
    'bg-slate-900/95 border border-slate-700 rounded-2xl shadow-2xl max-w-7xl max-h-[90vh] overflow-hidden'
  modalContent.onclick = (e) => e.stopPropagation()

  modalContent.innerHTML = `
    <div class="flex items-center justify-between p-4 border-b border-slate-700">
      <h3 class="text-lg font-medium text-slate-200 truncate">${filename}</h3>
      <button onclick="this.closest('.fixed').remove()"
              class="text-slate-400 hover:text-slate-200 transition-colors">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
        </svg>
      </button>
    </div>
    <div class="p-4">
      <img src="${imageUrl}"
           alt="${filename}"
           class="max-w-full max-h-[70vh] mx-auto rounded-lg shadow-lg">
    </div>
    <div class="p-4 border-t border-slate-700 text-center">
      <a href="${imageUrl}"
         download="${filename}"
         class="inline-flex items-center gap-2 px-6 py-3 text-base font-medium text-cyan-200 bg-gradient-to-r from-cyan-800/60 to-blue-800/60 hover:from-cyan-700/80 hover:to-blue-700/80 border border-cyan-500/50 hover:border-cyan-400 rounded-xl transition-all duration-200 shadow-[0_0_15px_rgba(34,211,238,0.3)] hover:shadow-[0_0_25px_rgba(34,211,238,0.5)]">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
        </svg>
        Download Image
      </a>
    </div>
  `

  modal.appendChild(modalContent)
  document.body.appendChild(modal)
}

// Periodically check for new images (useful for background processing)
async function startImagePolling(sha1Hash, intervalMs = 10000) {
  if (!sha1Hash) return

  const checkImages = async () => {
    try {
      await loadImages(sha1Hash)
    } catch (error) {
      console.log('Image polling check failed (normal if no images yet):', error.message)
    }
  }

  // Initial check
  await checkImages()

  // Check every intervalMs (default 10 seconds)
  const pollInterval = setInterval(checkImages, intervalMs)

  // Stop polling after 5 minutes (enough time for most processing)
  setTimeout(() => {
    clearInterval(pollInterval)
    console.log('Stopped image polling for', sha1Hash)
  }, 5 * 60 * 1000)

  return pollInterval
}
