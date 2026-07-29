(function () {
  // ── 搜索 ──────────────────────────────────────────
  var dataEl = document.getElementById('search-data');
  var input = document.getElementById('search-input');
  var resultsEl = document.getElementById('search-results');

  if (dataEl && input && resultsEl) {
    var index = [];
    try { index = JSON.parse(dataEl.textContent); } catch (e) { index = []; }

    function render(items, query) {
      if (!query) { resultsEl.hidden = true; resultsEl.innerHTML = ''; return; }
      if (items.length === 0) {
        resultsEl.innerHTML = '<div class="search-empty">没有找到匹配「' + query + '」的内容</div>';
        resultsEl.hidden = false;
        return;
      }
      var html = items.slice(0, 10).map(function (it) {
        return '<a href="' + it.url + '"><div class="sr-show">' + it.show + ' · ' + it.date + '</div>' +
          '<div class="sr-title">' + it.title + '</div></a>';
      }).join('');
      resultsEl.innerHTML = html;
      resultsEl.hidden = false;
    }

    input.addEventListener('input', function () {
      var q = input.value.trim().toLowerCase();
      if (!q) { render([], ''); return; }
      var matches = index.filter(function (it) {
        return (it.title + ' ' + it.show + ' ' + it.summary + ' ' + it.tags).toLowerCase().indexOf(q) !== -1;
      });
      render(matches, q);
    });

    document.addEventListener('click', function (e) {
      if (!resultsEl.contains(e.target) && e.target !== input) {
        resultsEl.hidden = true;
      }
    });
  }

  // ── 分类筛选 ──────────────────────────────────────
  var chipsWrap = document.getElementById('filter-chips');
  var grid = document.getElementById('show-grid');

  if (chipsWrap && grid) {
    var cards = Array.prototype.slice.call(grid.querySelectorAll('.show-card'));
    chipsWrap.addEventListener('click', function (e) {
      var chip = e.target.closest('.chip');
      if (!chip) return;
      chipsWrap.querySelectorAll('.chip').forEach(function (c) { c.classList.remove('active'); });
      chip.classList.add('active');
      var cat = chip.getAttribute('data-category');
      cards.forEach(function (card) {
        var show = cat === '全部' || card.getAttribute('data-category') === cat;
        card.style.display = show ? '' : 'none';
      });
    });
  }
})();
