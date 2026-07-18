// student_transactions/student_transactions/staticfiles/js/ce_transactions_table.js
/* CE transactions DataTable wiring (StudentTransaction row shape).
 *
 * Used by student_transactions/student_transactions/templates/transactions/
 * _ce_table.html via initCeTransactionsTable(tableId, opts). Companion
 * config module: student_transactions/student_transactions/table_configs/
 * ce_transactions.py owns the matching <th>/<tfoot> markup and named
 * profiles. Column keys are 'txn.*'.
 *
 * Carries over the summary-card behavior (renderSummary + summaryApiUrl
 * fetch + footer-search wiring) previously inlined in
 * templates/transactions/includes/index_js.html.
 *
 * XSS trust boundary: column renderers concatenate fields from the
 * StudentTransaction serializer into HTML strings. The API serializer is
 * the sanitization point.
 */
(function () {
  'use strict';

  function formatCurrency(amount) {
    if (amount < 0) {
      return '($' + Math.abs(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ')';
    }
    return '$' + amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function getIconForType(label, t_type) {
    var icons = {
      // Payment types
      'cc': 'fa-credit-card',
      'check': 'fa-money-check',
      'school_pay': 'fa-university',
      // Debit types
      'class_charge': 'fa-graduation-cap',
      'school_charge': 'fa-school',
      'check_return_fee': 'fa-exclamation-circle',
      'other': 'fa-file-invoice-dollar',
      // Scholarship types
      '1': 'fa-hand-holding-usd',
      '2': 'fa-hand-holding-usd',
      '3': 'fa-hand-holding-usd',
      // Refund types
      'R1': 'fa-undo',
    };
    return icons[label] || (t_type === 'debit' ? 'fa-minus-circle' : 'fa-plus-circle');
  }

  function renderSummary(data) {
    var html = '';
    var currentLabel = $('#label_filter').val();

    if (data.items && data.items.length > 0) {
      data.items.forEach(function (item) {
        var icon = getIconForType(item.label, item.t_type);
        var iconClass = item.t_type === 'debit' ? 'debit' : 'credit';
        var isActive = currentLabel === item.label;
        var borderClass = isActive ? ' border-primary border-2' : ' border-0';
        html += '<div class="col-xl-3 col-lg-4 col-md-6 mb-3">';
        html += '<div class="card summary-card shadow-sm h-100' + borderClass + '" data-label="' + item.label + '" style="cursor: pointer;">';
        html += '<div class="card-body d-flex align-items-center p-3">';
        html += '<div class="icon-wrapper ' + iconClass + ' mr-3">';
        html += '<i class="fas ' + icon + '"></i>';
        html += '</div>';
        html += '<div class="flex-grow-1">';
        html += '<div class="font-weight-bold text-dark">' + item.display + '</div>';
        html += '<div class="small text-muted">' + item.count + ' Transaction' + (item.count !== 1 ? 's' : '') + '</div>';
        html += '</div>';
        html += '<div class="text-right">';
        html += '<span class="h5 mb-0 font-weight-bold text-' + (item.t_type === 'debit' ? 'danger' : 'success') + '">' + formatCurrency(item.total) + '</span>';
        html += '</div>';
        html += '</div></div></div>';
      });

      html += '<div class="col-xl-3 col-lg-4 col-md-6 mb-3">';
      html += '<div class="card summary-totals shadow-sm border-0 h-100">';
      html += '<div class="card-body d-flex align-items-center p-3">';
      html += '<div class="icon-wrapper primary mr-3">';
      html += '<i class="fas fa-chart-pie"></i>';
      html += '</div>';
      html += '<div class="flex-grow-1">';
      html += '<div class="font-weight-bold text-dark">Summary</div>';
      html += '<div class="small text-muted">Net Balance</div>';
      html += '</div>';
      html += '<div class="text-right">';
      html += '<span class="h5 mb-0 font-weight-bold text-primary">' + formatCurrency(data.totals.net) + '</span>';
      html += '</div>';
      html += '</div></div></div>';
    } else {
      html = '<div class="col-12 text-center py-3">';
      html += '<span class="text-muted">No transactions found</span>';
      html += '</div>';
    }

    $('#summary-container').html(html);
  }

  function loadSummary(opts) {
    if (!opts.summaryApiUrl) return;
    var form = $('form.filter');
    var url = opts.summaryApiUrl + '?' + form.serialize();

    $.get(url)
      .done(function (data) { renderSummary(data); })
      .fail(function () {
        $('#summary-container').html(
          '<div class="col-12 text-center py-3">' +
          '<span class="text-muted">Unable to load summary</span>' +
          '</div>'
        );
      });
  }

  function actionRender(opts) {
    return function (_d, _t, row) {
      var href = row.ce_url || ((opts.detailsPrefix || '') + row.id);
      return "<a class='btn btn-sm btn-primary record-details' refresh-target='table' href='" +
             href + "'>Edit</a>";
    };
  }

  function buildColumns(keys, opts) {
    var defs = {
      'txn.select': {
        searchable: false, orderable: false,
        className: 'select-checkbox',
        render: function () { return ''; },
      },
      'txn.created_on': null,
      'txn.term': null,
      'txn.type':  null,
      'txn.amount': {
        searchable: false,
        render: function (_d, _t, row) {
          return "<span class='transaction-" + row.t_type + "'>" + row.format_amount + "</span>";
        },
      },
      'txn.description': null,
      'txn.student': {
        render: function (_d, _t, row) {
          return row.student.user.last_name + ', ' + row.student.user.first_name;
        },
      },
      'txn.student_id': null,
      'txn.highschool': null,
      'txn.actions': {
        searchable: false, orderable: false,
        render: actionRender(opts),
      },
    };
    return keys.map(function (k) {
      if (!(k in defs)) throw new Error('Unknown ce_transactions_table column: ' + k);
      return defs[k];
    });
  }

  function buildButtons(opts) {
    var buttons = [
      {
        extend: 'csv',
        className: 'btn btn-sm btn-primary text-white text-light',
        text: '<i class="fas fa-file-csv text-white"></i>&nbsp;CSV',
        titleAttr: 'Export results to CSV',
      },
      {
        extend: 'print',
        className: 'btn btn-sm btn-primary text-white text-light',
        text: '<i class="fas fa-print text-white"></i>&nbsp;Print',
        titleAttr: 'Print',
      },
    ];
    if (Array.isArray(opts.bulkActions)) {
      opts.bulkActions.forEach(function (spec) {
        buttons.push({
          className: 'btn btn-sm ' + spec.btnClass + ' text-white text-light',
          text: '<i class="' + spec.icon + ' text-white"></i>&nbsp;' + spec.label,
          titleAttr: spec.label,
          action: function (e, dt) {
            if (spec.confirm && !confirm(spec.confirm)) return;
            window.ActionRegistry.doBulkAction(opts.bulkActionsUrl, spec.slug, dt);
          },
        });
      });
    }
    return buttons;
  }

  function hasSelectColumn(keys) {
    return keys.some(function (k) { return k === 'txn.select'; });
  }

  function wireFooterSearch(api) {
    api.columns().every(function () {
      var column = this;
      var foot = column.footer();
      if (!foot) return;
      var title = foot.textContent;
      if (!title) return;

      var input = document.createElement('input');
      input.className = 'form-control';
      input.placeholder = 'Search ' + title;
      foot.replaceChildren(input);

      input.addEventListener('keyup', $.debounce(1500, function () {
        if (column.search() !== input.value) {
          column.search(input.value).draw();
        }
      }));
    });

    var state = api.state.loaded();
    if (state) {
      api.columns().eq(0).each(function (colIdx) {
        var colSearch = state.columns[colIdx].search;
        if (colSearch && colSearch.search) {
          $('input', api.column(colIdx).footer()).val(colSearch.search);
        }
      });
    }
  }

  window.initCeTransactionsTable = function (tableId, opts) {
    var $table = $(tableId);
    if (!$table.length) {
      throw new Error('initCeTransactionsTable: no element matches ' + tableId);
    }

    var withSelect = hasSelectColumn(opts.columns);

    var dtConfig = {
      initComplete: function () {
        // Wired unconditionally: wireFooterSearch() is a no-op when a
        // column has no <tfoot> cell (config.footer_search is opt-in per
        // profile via the partial's `{% if config.footer_search %}` guard;
        // opts itself carries no matching flag from ce_transactions.py).
        wireFooterSearch(this.api());
      },
      searchDelay: 1500,
      dom: 'B<"float-left mt-3 mb-3"l><"float-right mt-3"f><"row clear">rt<"row"<"col-6"i><"col-6 float-right"p>>',
      buttons: buildButtons(opts),
      orderCellsTop: true,
      fixedHeader: true,
      ajax: opts.apiUrl,
      serverSide: true,
      processing: true,
      stateSave: true,
      language: { loadingRecords: '&nbsp;' },
      lengthMenu: [30, 50, 100],
      order: [opts.defaultOrder || [withSelect ? 1 : 0, 'asc']],
      rowId: 'id',
      columns: buildColumns(opts.columns, opts),
    };
    if (withSelect) {
      dtConfig.columnDefs = [{ orderable: false, className: 'select-checkbox', targets: 0 }];
      dtConfig.select = {
        style: opts.selectStyle || 'os',
        selector: 'td:first-child',
      };
    }

    var table = $table.DataTable(dtConfig);

    // Initial + filter-form-driven summary card refresh (mirrors the
    // pre-refactor `form.filter :input` change handler).
    loadSummary(opts);
    $(document).on('change', 'form.filter :input', function () {
      var form = $('form.filter');
      table.ajax.url(opts.apiUrl + '&' + form.serialize()).load();
      loadSummary(opts);
    });

    // Summary card click handler - filter by label.
    $(document).on('click', '.summary-card[data-label]', function () {
      var label = $(this).data('label');
      var currentLabel = $('#label_filter').val();
      if (currentLabel === label) {
        $('#label_filter').val('');
        $('#clear_label_filter').addClass('d-none');
      } else {
        $('#label_filter').val(label);
        $('#clear_label_filter').removeClass('d-none');
      }
      $('form.filter').trigger('change');
    });

    if (opts.autoReloadMinutes) {
      setInterval(function () {
        if (table.rows({ selected: true }).count() <= 0) {
          table.ajax.reload(null, false);
          loadSummary(opts);
        }
      }, opts.autoReloadMinutes * 60 * 1000);
    }

    window.refreshTable = function () {
      var sel = table.rows({ selected: true });
      sel.deselect();
      table.ajax.reload(null, false);
      loadSummary(opts);
    };
    // Back-compat: pre-refactor templates assigned `table = $(...).DataTable()`
    // so main.js's modal close handler could call `window.table.ajax.reload`.
    window.table = table;

    return table;
  };
})();
