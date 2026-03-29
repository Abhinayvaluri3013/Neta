/* =====================================================
   NETA — National Electronic Transparent Authentication
   Main JavaScript
   ===================================================== */

/* ── Live Clock (Ribbon) ── */
function updateClock() {
  const now = new Date();
  const opts = {
    weekday: 'short', day: 'numeric', month: 'short',
    year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit'
  };
  const el = document.getElementById('ribbon-time');
  if (el) el.textContent = now.toLocaleString('en-IN', opts);
}
setInterval(updateClock, 1000);
updateClock();

/* ── Scroll-triggered Animations ── */
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) e.target.classList.add('visible');
  });
}, { threshold: 0.15 });

document.querySelectorAll('.fade-up, .how-step').forEach(el => observer.observe(el));

/* ── Smooth Anchor Scroll ── */
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const target = document.querySelector(a.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});