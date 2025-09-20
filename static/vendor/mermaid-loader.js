// Simple loader wrapper for mermaid. The file intentionally uses the official CDN to make it easy
// to later vendor the file by replacing the content with the library's source.
;(function () {
  if (window.mermaid) return
  var s = document.createElement('script')
  s.src = 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js'
  s.onload = function () {
    if (window.mermaid) {
      // default initialize with auto start disabled; we'll call init() explicitly
      try {
        window.mermaid.initialize({ startOnLoad: false, theme: 'base', securityLevel: 'loose' })
      } catch (e) {
        console.warn('mermaid init failed', e)
      }
    }
  }
  s.onerror = function () {
    console.warn('Failed to load mermaid from CDN')
  }
  document.head.appendChild(s)
})()
