let provincesData = [];
let citiesData = [];

async function load_data() {
    try {
        const response = await fetch(jsonurl);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        provincesData = data.provinces;
        citiesData = data.cities;

        populateUI();
    } catch (error) {
        console.error(error);
    }
}

function populateUI() {
    const stateSelect = document.getElementById('StateSelect');
    const citySelect = document.getElementById('CitySelect');

    provincesData.forEach(prov => {
        const option = document.createElement('option');
        option.value = prov.name;           
        option.textContent = prov.name;
        option.dataset.id = prov.id;
        stateSelect.appendChild(option);
    });

    stateSelect.addEventListener('change', function () {
        const selected = this.options[this.selectedIndex];
        const selectedProvinceId = selected ? selected.dataset.id : null;
        populateCities(selectedProvinceId, citySelect);
    });

}

function populateCities(provinceId, citySelect) {
    citySelect.innerHTML = '<option value="">Select a city</option>';

    if (!provinceId) return;

    const filteredCities = citiesData.filter(city => city.province_id === provinceId);

    filteredCities.forEach(city => {
        const option = document.createElement('option');
        option.value = city.name;      
        option.textContent = city.name;
        citySelect.appendChild(option);
    });
}

load_data();
