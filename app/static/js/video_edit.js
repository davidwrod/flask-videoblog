document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.cookie.split('; ')
        .find(row => row.startsWith('csrf_token='))
        ?.split('=')[1];

    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const card = this.closest('.video-card');
            card.querySelector('.video-info').classList.add('hidden');
            card.querySelector('.action-buttons').classList.add('hidden');
            card.querySelector('.edit-form').classList.remove('hidden');
        });
    });

    document.querySelectorAll('.cancel-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const form = this.closest('.edit-form');
            form.classList.add('hidden');
            const card = form.closest('.video-card');
            card.querySelector('.video-info').classList.remove('hidden');
            card.querySelector('.action-buttons').classList.remove('hidden');
        });
    });

    document.querySelectorAll('.edit-form').forEach(form => {
        form.addEventListener('submit', async function (e) {
            e.preventDefault();
            const videoId = this.dataset.id;
            const newTitle = this.querySelector('input[name="new_title"]').value.trim();

            if (!newTitle) {
                alert('O título não pode estar vazio');
                return;
            }

            try {
                const response = await fetch(`/edit_video_title/${videoId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ new_title: newTitle })
                });

                if (response.ok) {
                    const card = this.closest('.video-card');
                    card.querySelector('.video-title').textContent = newTitle;
                    card.querySelector('.video-info').classList.remove('hidden');
                    card.querySelector('.action-buttons').classList.remove('hidden');
                    this.classList.add('hidden');
                } else {
                    const error = await response.json();
                    alert(error.error || 'Erro ao atualizar o título');
                }
            } catch (error) {
                alert('Erro ao atualizar o título');
                console.error(error);
            }
        });
    });
});

function openSuggestModelModal() {
    document.getElementById('suggestModelModal').classList.remove('hidden');
    document.getElementById('suggestionStatus').innerText = '';
    document.getElementById('modelInput').value = '';
}

function closeSuggestModelModal() {
    document.getElementById('suggestModelModal').classList.add('hidden');
}

async function submitModelSuggestion() {
  const model = document.getElementById('modelInput').value.trim();
  if (!model) return;

  const modalEl = document.getElementById('suggestModelModal');
  const videoSlug = modalEl.dataset.videoSlug;

  if (!videoSlug) {
    console.error("Video slug não encontrado no modal.");
    return;
  }

  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

  try {
    const res = await fetch(`/video/${videoSlug}/suggest_model`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ model })
    });

    const data = await res.json();
    const statusText = document.getElementById('suggestionStatus');

    if (res.ok) {
      statusText.innerText = data.message || "Sugestão enviada com sucesso!";
      statusText.className = "text-green-400 text-sm mt-3";
      setTimeout(() => window.location.reload(), 1500);
    } else {
      statusText.innerText = data.error || "Erro ao enviar sugestão.";
      statusText.className = "text-red-400 text-sm mt-3";
    }
  } catch (error) {
    console.error("Erro no fetch:", error);
  }
}

