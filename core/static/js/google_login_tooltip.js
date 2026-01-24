// Tooltip for Google login button
window.addEventListener('DOMContentLoaded', function() {
  const btn = document.querySelector('.google-login-btn');
  if (!btn) return;

  // Create tooltip element
  const tooltip = document.createElement('div');
  tooltip.innerText = 'Click here to login';
  tooltip.className = 'google-tooltip-glass';
  tooltip.style.position = 'absolute';
  // Place tooltip centered on the button
  tooltip.style.top = '50%';
  tooltip.style.left = '50%';
  tooltip.style.transform = 'translate(-50%, -50%)';
  tooltip.style.left = '50%';
  tooltip.style.transform = 'translateX(-50%)';
  tooltip.style.zIndex = '50';
  tooltip.style.opacity = '0';
  tooltip.style.pointerEvents = 'none';
  tooltip.style.whiteSpace = 'nowrap';
  tooltip.style.transition = 'opacity 0.7s cubic-bezier(.4,2,.6,1)';
  btn.appendChild(tooltip);

  // Show tooltip after 3 seconds, for 3 seconds
  setTimeout(() => {
    tooltip.style.opacity = '1';
    setTimeout(() => {
      tooltip.style.opacity = '0';
    }, 3000);
  }, 3000);
});
