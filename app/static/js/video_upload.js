document.addEventListener('DOMContentLoaded', function () {
    const availableTags = window.availableTags || [];

    const fileInput = document.getElementById("videos");
    const fileList = document.getElementById("file-list");
    const detailsContainer = document.getElementById("video-details");
    const modelSearch = document.getElementById("model-search");
    const selectedModels = document.getElementById("selected-models");
    const modelInputs = document.getElementById("model-inputs");

    const autocompleteUrl = modelSearch.dataset.autocompleteUrl;

    let dt = new DataTransfer();
    let selectedModelsList = [];

    $(modelSearch).autocomplete({
        source: function(request, response) {
            $.ajax({
                url: autocompleteUrl,
                dataType: "json",
                data: { q: request.term },
                success: function(data) {
                    const filteredData = data.filter(model => !selectedModelsList.includes(model));
                    response(filteredData);
                }
            });
        },
        minLength: 1,
        select: function(event, ui) {
            addModel(ui.item.value);
            $(this).val('');
            return false;
        }
    }).on('keypress', function(e) {
        if (e.which === 13) {
            e.preventDefault();
            const value = $(this).val().trim();
            if (value && !selectedModelsList.includes(value)) {
                addModel(value);
                $(this).val('');
            }
        }
    });

    function addModel(modelName) {
        if (!modelName || selectedModelsList.includes(modelName)) return;
        selectedModelsList.push(modelName);
        updateModelDisplay();
    }

    function removeModel(modelName) {
        const index = selectedModelsList.indexOf(modelName);
        if (index > -1) {
            selectedModelsList.splice(index, 1);
            updateModelDisplay();
        }
    }

    function updateModelDisplay() {
        selectedModels.innerHTML = '';
        modelInputs.innerHTML = '';

        selectedModelsList.forEach((model) => {
            const tag = document.createElement('span');
            tag.className = 'model-tag';
            tag.innerHTML = `${model} <span class="remove" data-model="${model}">&times;</span>`;
            selectedModels.appendChild(tag);

            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'models[]';
            input.value = model;
            modelInputs.appendChild(input);
        });

        document.querySelectorAll('.model-tag .remove').forEach(btn => {
            btn.addEventListener('click', function() {
                removeModel(this.getAttribute('data-model'));
            });
        });
    }

    function generateVideoDetails() {
        detailsContainer.innerHTML = "";
        Array.from(fileInput.files).forEach((file, index) => {
            const tagOptions = availableTags.map(tag => `
                <label class="mr-2">
                    <input type="checkbox" name="tags_${index}_${tag.id}" value="${tag.id}">
                    ${tag.name}
                </label>
            `).join('');

            const wrapper = document.createElement("div");
            wrapper.innerHTML = `
                <div class="border border-gray-700 p-4 rounded mb-4">
                    <p class="font-semibold text-white">${file.name}</p>
                    <label for="title_${index}" class="block text-sm text-gray-300 mt-2">Título:</label>
                    <input type="text" name="title_${index}" id="title_${index}" placeholder="Título do vídeo" value="${file.name}" required
                        class="w-full px-2 py-1 rounded bg-gray-800 text-white border border-gray-600 mb-2">

                    <label class="block text-sm text-gray-300">Tags (opcional):</label>
                    <div class="flex flex-wrap gap-2 text-sm text-gray-200 mb-2">
                        ${tagOptions}
                    </div>
                </div>
            `;
            detailsContainer.appendChild(wrapper);
        });
    }

    fileInput.addEventListener("change", function () {
        dt = new DataTransfer();
        fileList.innerHTML = "";

        Array.from(fileInput.files).forEach((file, index) => {
            dt.items.add(file);

            const item = document.createElement("div");
            item.className = "flex justify-between items-center bg-gray-800 px-4 py-2 rounded border border-gray-600";

            item.innerHTML = `
                <span class="truncate text-sm text-white">${file.name}</span>
                <button type="button" class="remove-file text-red-400 hover:text-red-200 text-sm ml-4" data-index="${index}">Remover</button>
            `;

            fileList.appendChild(item);
        });

        fileInput.files = dt.files;
        generateVideoDetails();
    });

    fileList.addEventListener("click", function (e) {
        if (e.target.classList.contains("remove-file")) {
            const indexToRemove = parseInt(e.target.getAttribute("data-index"));
            dt = new DataTransfer();

            Array.from(fileInput.files).forEach((file, i) => {
                if (i !== indexToRemove) dt.items.add(file);
            });

            fileInput.files = dt.files;

            fileList.innerHTML = "";
            Array.from(fileInput.files).forEach((file, index) => {
                const item = document.createElement("div");
                item.className = "flex justify-between items-center bg-gray-800 px-4 py-2 rounded border border-gray-600";

                item.innerHTML = `
                    <span class="truncate text-sm text-white">${file.name}</span>
                    <button type="button" class="remove-file text-red-400 hover:text-red-200 text-sm ml-4" data-index="${index}">Remover</button>
                `;

                fileList.appendChild(item);
            });

            generateVideoDetails();
        }
    });

    const dropZone = document.getElementById("drop-zone");

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("border-red-500", "bg-gray-800");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("border-red-500", "bg-gray-800");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("border-red-500", "bg-gray-800");

        const files = Array.from(e.dataTransfer.files);
        const dt = new DataTransfer();
        for (let file of fileInput.files) dt.items.add(file);
        for (let file of files) dt.items.add(file);

        fileInput.files = dt.files;

        const event = new Event("change", { bubbles: true });
        fileInput.dispatchEvent(event);
    });

    fileInput.addEventListener('change', (event) => {
        const arquivos = Array.from(event.target.files);
        const tiposValidos = ['video/mp4', 'video/webm', 'video/x-matroska', 'video/quicktime', 'video/x-msvideo'];

        for (const arquivo of arquivos) {
            if (!tiposValidos.includes(arquivo.type)) {
                alert(`Arquivo inválido: ${arquivo.name}`);
                event.target.value = '';
                break;
            }
        }
    });
});
