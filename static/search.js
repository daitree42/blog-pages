async function initSearch(inputId, resultsId) {
  var input = document.getElementById(inputId);
  var results = document.getElementById(resultsId);
  if (!input) return;

  var res = await fetch(PREFIX + "/search.json");
  var index = await res.json();

  input.addEventListener("input", function () {
    var q = input.value.trim().toLowerCase();
    results.innerHTML = "";
    if (!q) return;

    var hits = index.filter(function (a) {
      return a.title.toLowerCase().includes(q) ||
        a.excerpt.toLowerCase().includes(q) ||
        a.tags.some(function (t) { return t.toLowerCase().includes(q); });
    }).slice(0, 10);

    hits.forEach(function (a) {
      results.innerHTML +=
        '<a href="' + PREFIX + '/' + a.url + '" class="search-result">' +
          '<span class="search-title">' + a.title + '</span>' +
          '<span class="search-meta">' + a.date + ' · ' + a.category + '</span>' +
          '<span class="search-excerpt">' + a.excerpt + '</span>' +
        '</a>';
    });
    if (!hits.length) results.innerHTML = "<p class='search-empty'>无结果</p>";
  });
}
