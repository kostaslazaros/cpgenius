// Local loader for Highlight.js (loads from CDN). Replace with vendored highlight.min.js if desired.
;(function () {
  const script = document.createElement('script')
  script.src = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js'
  script.crossOrigin = 'anonymous'
  script.referrerPolicy = 'no-referrer'
  script.onload = function () {
    window.hljs = window.hljs || window.hljsHighlight
  }
  document.head.appendChild(script)
})()
