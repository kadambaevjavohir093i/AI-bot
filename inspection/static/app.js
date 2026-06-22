// Photo preview
document.querySelectorAll('.photo-input').forEach(input => {
  input.addEventListener('change', function () {
    const previewId = this.dataset.preview;
    const preview = document.getElementById(previewId);
    const file = this.files[0];
    if (file && preview) {
      const reader = new FileReader();
      reader.onload = e => {
        preview.src = e.target.result;
        preview.style.display = 'block';
      };
      reader.readAsDataURL(file);
    }
  });
});

// Progress bar based on answered items
function updateProgress() {
  const total = document.querySelectorAll('.item-card').length;
  if (total === 0) return;

  let answered = 0;
  document.querySelectorAll('.item-card').forEach(card => {
    const radios = card.querySelectorAll('input[type="radio"]');
    const text = card.querySelector('input[type="text"].text-result');
    if (radios.length > 0) {
      if (card.querySelector('input[type="radio"]:checked')) answered++;
    } else if (text) {
      if (text.value.trim()) answered++;
    } else {
      answered++; // non-result items count as done
    }
  });

  const pct = Math.round((answered / total) * 100);
  const bar = document.getElementById('progressBar');
  if (bar) bar.style.width = pct + '%';
}

document.querySelectorAll('input[type="radio"]').forEach(r => {
  r.addEventListener('change', () => {
    updateProgress();
    // Highlight selected button
    const group = r.closest('.result-group');
    if (group) {
      group.querySelectorAll('.result-btn span').forEach(s => s.style.fontWeight = '');
    }
  });
});

document.querySelectorAll('input[type="text"].text-result').forEach(i => {
  i.addEventListener('input', updateProgress);
});

updateProgress();

// Confirm before leaving with unsaved changes
let formDirty = false;
const form = document.getElementById('inspectForm');
if (form) {
  form.addEventListener('input', () => { formDirty = true; });
  form.addEventListener('submit', () => { formDirty = false; });
  window.addEventListener('beforeunload', e => {
    if (formDirty) {
      e.preventDefault();
      e.returnValue = '';
    }
  });
}

// Loading state on submit
const submitBtn = document.getElementById('submitBtn');
if (submitBtn && form) {
  form.addEventListener('submit', () => {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting…';
  });
}
