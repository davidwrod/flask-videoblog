document.addEventListener('DOMContentLoaded', () => {
    const player = videojs('my-video', {
        aspectRatio: '16:9',
        fluid: false,
        fill: true,
        controls: true,
        controlBar: {
            children: [
                'playToggle',
                'volumePanel',
                'currentTimeDisplay',
                'timeDivider',
                'durationDisplay',
                'progressControl',
                'playbackRateMenuButton',
                'fullscreenToggle'
            ]
        }
    });

    player.on('play', function () {
        if (!this.hasStarted_) {
            this.hasStarted_ = true;
            // Lógica de registro de visualização aqui se necessário
        }
    });

    document.getElementById('like-btn').addEventListener('click', () => {
        fetch(likeUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(res => res.json())
        .then(data => {
            const likeText = document.getElementById('like-text');
            const likeCount = document.getElementById('like-count');
            if (data.status === 'liked') {
                likeText.innerText = 'Curtido';
            } else {
                likeText.innerText = 'Curtir';
            }
            likeCount.innerText = `(${data.likes})`;
        });
    });
});
