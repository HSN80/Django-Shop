

(function () {
  var minRange = document.querySelector('.min-range');
  var maxRange = document.querySelector('.max-range');
  var minInput = document.querySelector('.min-price-input');
  var maxInput = document.querySelector('.max-price-input');
  var minLabel = document.querySelector('.min-price');
  var maxLabel = document.querySelector('.max-price');
  var progress = document.querySelector('.slider-progress');
  var applyBtn = document.getElementById('applyPriceFilter');
  var sliderMin = parseInt(minRange.min, 10);
  var sliderMax = parseInt(minRange.max, 10);
  var span = sliderMax - sliderMin || 1;

  function updateProgress() {
    var minVal = parseInt(minRange.value, 10);
    var maxVal = parseInt(maxRange.value, 10);
    progress.style.left = ((minVal - sliderMin) / span * 100) + '%';
    progress.style.width = ((maxVal - minVal) / span * 100) + '%';
  }

  function syncFromRange() {
    var minVal = parseInt(minRange.value, 10);
    var maxVal = parseInt(maxRange.value, 10);
    if (minVal > maxVal) { minVal = maxVal; minRange.value = minVal; }
    minInput.value = minVal;
    maxInput.value = maxVal;
    minLabel.textContent = minVal;
    maxLabel.textContent = maxVal;
    updateProgress();
  }

  function syncFromInput() {
    var minVal = parseInt(minInput.value, 10) || sliderMin;
    var maxVal = parseInt(maxInput.value, 10) || sliderMax;
    minRange.value = minVal;
    maxRange.value = maxVal;
    minLabel.textContent = minVal;
    maxLabel.textContent = maxVal;
    updateProgress();
  }

  minRange.addEventListener('input', syncFromRange);
  maxRange.addEventListener('input', syncFromRange);
  minInput.addEventListener('change', syncFromInput);
  maxInput.addEventListener('change', syncFromInput);

  applyBtn.addEventListener('click', function () {
    var params = new URLSearchParams(window.location.search);
    params.set('min_price', minInput.value);
    params.set('max_price', maxInput.value);
    params.delete('page');
    window.location.search = params.toString();
  });

  updateProgress();
})();