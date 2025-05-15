document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const videoId = this.dataset.id;
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
            form.closest('.video-card').querySelector('.video-info').classList.remove('hidden');
            form.closest('.video-card').querySelector('.action-buttons').classList.remove('hidden');
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
                        'Content-Type': 'application/json'
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
                    throw new Error('Falha ao atualizar');
                }
            } catch (error) {
                alert('Erro ao atualizar o título');
                console.error(error);
            }
        });
    });
});
