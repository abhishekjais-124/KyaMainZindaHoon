// Handles inline editing and autosave for the profile name

document.addEventListener('DOMContentLoaded', function() {
  const nameSpan = document.getElementById('editable-full-name');
  if (!nameSpan) return;

  let originalName = nameSpan.innerText;

  nameSpan.addEventListener('click', function() {
    if (nameSpan.querySelector('input')) return;
    const input = document.createElement('input');
    input.type = 'text';
    input.value = originalName;
    input.className = 'inline-edit-input py-1 px-2 rounded bg-black/40 text-white border border-white/20';
    input.style.boxShadow = 'none';
    input.style.outline = 'none';
    input.style.width = (nameSpan.offsetWidth + 20) + 'px';
    nameSpan.innerHTML = '';
    nameSpan.appendChild(input);
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);

    function saveName() {
      const newName = input.value.trim();
      if (newName && newName !== originalName) {
        fetch(window.location.pathname, {
          method: 'POST',
          headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: 'full_name=' + encodeURIComponent(newName)
        })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            originalName = newName;
            nameSpan.innerText = newName;
          } else {
            nameSpan.innerText = originalName;
            alert(data.message || 'Failed to update name.');
          }
        })
        .catch(() => {
          nameSpan.innerText = originalName;
          alert('Failed to update name.');
        });
      } else {
        nameSpan.innerText = originalName;
      }
    }

    input.addEventListener('blur', saveName);
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        input.blur();
      } else if (e.key === 'Escape') {
        nameSpan.innerText = originalName;
      }
    });
  });
});
