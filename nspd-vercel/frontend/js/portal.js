/**
 * NSPD Ghana — seafarer "My Application" page.
 *
 * States:
 *   - no application yet  -> empty form, "Submit Application"
 *   - Pending / Rejected  -> form prefilled and editable ("Save Changes" /
 *                            "Update & Resubmit"), documents manageable
 *   - Under Review / Approved -> everything read-only with a lock notice
 */
(function () {
  var application = null;

  function portalFetch(path, options) {
    options = options || {};
    options.credentials = 'same-origin';
    return fetch(path, options).then(function (response) {
      if (response.status === 401) {
        window.location.href = 'portal-login.html';
        throw new Error('Unauthorized');
      }
      return response;
    });
  }

  function detailText(data, fallback) {
    var detail = data && data.detail;
    if (Array.isArray(detail)) {
      return detail.map(function (d) { return d.msg; }).join('; ');
    }
    return detail || fallback;
  }

  function showBox(id, message) {
    var box = document.getElementById(id);
    box.textContent = message;
    box.style.display = '';
  }

  function hideBox(id) {
    document.getElementById(id).style.display = 'none';
  }

  function statusBadge(status) {
    var cls = 'status-' + String(status || 'Pending').toLowerCase().replace(/\s+/g, '-');
    return '<span class="status-badge ' + cls + '">' + esc(status) + '</span>';
  }

  // ── Form state ──

  function fillForm(app) {
    document.getElementById('surname').value = app.surname || '';
    document.getElementById('firstName').value = app.first_name || '';
    document.getElementById('otherNames').value = app.other_names || '';
    document.getElementById('telephone').value = app.telephone || '';
    document.getElementById('ghanaCard').value = app.ghana_card_number || '';
    document.getElementById('lastShipType').value = app.last_ship_type || '';
    document.getElementById('shortCourses').value = app.short_courses_rmu || 'No';
    document.getElementById('isps').value = app.familiarisation_isps_gma || 'No';
    document.getElementById('attachment').value = app.attachment === 'Yes' ? 'Yes' : 'No';
    document.getElementById('medicals').value = app.medicals === 'Yes' ? 'Yes' : 'No';
    document.getElementById('seaExperience').value = app.sea_experience === 'Yes' ? 'Yes' : 'No';
    document.getElementById('totalYears').value =
      app.total_sea_experience_years !== null && app.total_sea_experience_years !== undefined
        ? app.total_sea_experience_years : 0;
    // The rank select may not be populated yet; remembered for ensureRankOption
    document.getElementById('positionRank').setAttribute('data-selected', app.position_rank || '');
  }

  function ensureRankSelected() {
    var select = document.getElementById('positionRank');
    var wanted = select.getAttribute('data-selected');
    if (!wanted) return;
    var exists = Array.from(select.options).some(function (o) { return o.value === wanted; });
    if (!exists) {
      var option = document.createElement('option');
      option.value = wanted;
      option.textContent = wanted;
      select.appendChild(option);
    }
    select.value = wanted;
  }

  function formPayload() {
    var totalYears = parseFloat(document.getElementById('totalYears').value);
    return {
      surname: document.getElementById('surname').value.trim(),
      first_name: document.getElementById('firstName').value.trim(),
      other_names: document.getElementById('otherNames').value.trim() || null,
      telephone: document.getElementById('telephone').value.trim(),
      ghana_card_number: document.getElementById('ghanaCard').value.trim().toUpperCase(),
      position_rank: document.getElementById('positionRank').value,
      short_courses_rmu: document.getElementById('shortCourses').value,
      familiarisation_isps_gma: document.getElementById('isps').value,
      attachment: document.getElementById('attachment').value,
      medicals: document.getElementById('medicals').value,
      sea_experience: document.getElementById('seaExperience').value,
      total_sea_experience_years: isNaN(totalYears) ? null : totalYears,
      last_ship_type: document.getElementById('lastShipType').value.trim() || null
    };
  }

  function setFormDisabled(disabled) {
    document.querySelectorAll('#applicationForm input, #applicationForm select').forEach(function (el) {
      el.disabled = disabled;
    });
    document.getElementById('saveButton').style.display = disabled ? 'none' : '';
  }

  function renderState() {
    hideBox('lockNotice');
    var banner = document.getElementById('statusBanner');

    if (!application) {
      banner.style.display = 'none';
      document.getElementById('formTitle').textContent = 'Submit Your Application';
      document.getElementById('saveButton').textContent = 'Submit Application';
      setFormDisabled(false);
      document.getElementById('documentsCard').style.display = 'none';
      document.getElementById('certificationsCard').style.display = 'none';
      document.getElementById('historyCard').style.display = 'none';
      return;
    }

    banner.style.display = '';
    document.getElementById('bannerRef').textContent = '#' + application.id;
    document.getElementById('bannerSubmitted').textContent =
      ' — submitted ' + fmtDateLong(application.submitted_at);
    document.getElementById('bannerStatus').innerHTML = statusBadge(application.status);
    document.getElementById('documentsCard').style.display = '';
    document.getElementById('certificationsCard').style.display = '';
    document.getElementById('historyCard').style.display = '';

    if (application.editable) {
      setFormDisabled(false);
      if (application.status === 'Rejected') {
        document.getElementById('formTitle').textContent = 'Update & Resubmit Your Application';
        document.getElementById('saveButton').textContent = 'Update & Resubmit';
        showBox('lockNotice',
          'Your application was not approved. You may update your details and documents, then resubmit for a new review.');
      } else {
        document.getElementById('formTitle').textContent = 'Your Application (editable while Pending)';
        document.getElementById('saveButton').textContent = 'Save Changes';
      }
      document.getElementById('uploadForm').style.display = '';
      document.getElementById('certForm').style.display = '';
    } else {
      setFormDisabled(true);
      document.getElementById('formTitle').textContent = 'Your Application';
      showBox('lockNotice',
        'Your application is ' + application.status + ' and can no longer be edited. ' +
        'Contact the Ghana Maritime Authority if a correction is needed.');
      document.getElementById('uploadForm').style.display = 'none';
      document.getElementById('certForm').style.display = 'none';
    }
  }

  // ── Timeline ──

  function loadHistory() {
    if (!application) return;
    portalFetch('/api/portal/application/history')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        document.getElementById('historyContainer').innerHTML = timelineHTML(data.history);
      })
      .catch(function (error) { console.error('Failed to load history:', error); });
  }

  // ── Certifications ──

  function loadCertifications() {
    if (!application) return;
    portalFetch('/api/portal/certifications')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var certs = data.certifications || [];
        var container = document.getElementById('certificationsList');
        if (!certs.length) {
          container.innerHTML = '<span class="muted">No certifications recorded yet.</span>';
          return;
        }
        container.innerHTML = '<div class="table-container"><table><thead><tr>' +
          '<th>Type</th><th>Title</th><th>Issued</th><th>Expires</th><th>Status</th><th></th>' +
          '</tr></thead><tbody>' +
          certs.map(function (cert) {
            var removable = application.editable && cert.added_by === null;
            return '<tr>' +
              '<td class="text-sm">' + esc(cert.cert_type) + '</td>' +
              '<td>' + esc(cert.title) + '</td>' +
              '<td class="text-sm">' + (cert.issued_on ? fmtDateShort(cert.issued_on) : '—') + '</td>' +
              '<td class="text-sm">' + (cert.expires_on ? fmtDateShort(cert.expires_on) : '—') + '</td>' +
              '<td>' + certBadge(cert.status) + '</td>' +
              '<td>' + (removable
                ? '<button class="text-danger-action" data-cert="' + cert.id + '">Delete</button>'
                : '') + '</td>' +
            '</tr>';
          }).join('') + '</tbody></table></div>';

        container.querySelectorAll('button[data-cert]').forEach(function (button) {
          button.addEventListener('click', function () {
            if (!window.confirm('Delete this certification record?')) return;
            portalFetch('/api/portal/certifications/' + button.getAttribute('data-cert'), { method: 'DELETE' })
              .then(function () { loadCertifications(); })
              .catch(function (error) { console.error(error); });
          });
        });
      })
      .catch(function (error) { console.error('Failed to load certifications:', error); });
  }

  // ── Documents ──

  function fmtSize(bytes) {
    if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + ' MB';
    if (bytes >= 1024) return Math.round(bytes / 1024) + ' KB';
    return bytes + ' B';
  }

  function loadDocuments() {
    if (!application) return;
    portalFetch('/api/portal/documents')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var docs = data.documents || [];
        var container = document.getElementById('documentsList');
        if (!docs.length) {
          container.innerHTML = '<span class="muted">No documents uploaded yet.</span>';
          return;
        }
        container.innerHTML = '<div class="table-container"><table><thead><tr>' +
          '<th>Type</th><th>File</th><th>Size</th><th>Uploaded</th><th></th>' +
          '</tr></thead><tbody>' +
          docs.map(function (doc) {
            var removable = application.editable && doc.uploaded_by === null;
            return '<tr>' +
              '<td>' + esc(doc.doc_type) + '</td>' +
              '<td>' + esc(doc.original_name) + '</td>' +
              '<td class="text-sm">' + fmtSize(doc.size_bytes) + '</td>' +
              '<td class="text-sm">' + fmtDateShort(doc.uploaded_at) + '</td>' +
              '<td>' + (removable
                ? '<button class="text-danger-action" data-doc="' + doc.id + '">Delete</button>'
                : '') + '</td>' +
            '</tr>';
          }).join('') + '</tbody></table></div>';

        container.querySelectorAll('button[data-doc]').forEach(function (button) {
          button.addEventListener('click', function () {
            if (!window.confirm('Delete this document?')) return;
            portalFetch('/api/portal/documents/' + button.getAttribute('data-doc'), { method: 'DELETE' })
              .then(function () { loadDocuments(); })
              .catch(function (error) { console.error(error); });
          });
        });
      })
      .catch(function (error) { console.error('Failed to load documents:', error); });
  }

  // ── Bootstrap ──

  portalFetch('/api/portal/me')
    .then(function (r) { return r.json(); })
    .then(function (me) {
      document.getElementById('portalUserName').textContent = me.applicant.full_name;
      return portalFetch('/api/portal/application');
    })
    .then(function (response) {
      if (response.status === 404) return null;
      return response.json().then(function (data) { return data.application; });
    })
    .then(function (app) {
      application = app;
      if (application) fillForm(application);
      renderState();
      loadDocuments();
      loadCertifications();
      loadHistory();
    })
    .catch(function (error) { console.error(error); });

  // Rank options
  fetch('/api/portal/ranks', { credentials: 'same-origin' })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var select = document.getElementById('positionRank');
      (data.ranks || []).forEach(function (rank) {
        var option = document.createElement('option');
        option.value = rank;
        option.textContent = rank;
        select.appendChild(option);
      });
      ensureRankSelected();
    })
    .catch(function (error) { console.error('Failed to load ranks:', error); });

  // Save / submit
  document.getElementById('applicationForm').addEventListener('submit', function (e) {
    e.preventDefault();
    hideBox('formError');
    hideBox('formSuccess');

    var creating = !application;
    portalFetch('/api/portal/application', {
      method: creating ? 'POST' : 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formPayload())
    })
      .then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (data) {
          if (!response.ok) {
            throw new Error(detailText(data, 'Could not save your application'));
          }
          application = data.application;
          fillForm(application);
          ensureRankSelected();
          renderState();
          loadDocuments();
          loadCertifications();
          loadHistory();
          showBox('formSuccess', creating
            ? 'Application submitted. Your reference number is #' + application.id +
              '. A confirmation email has been sent.'
            : 'Your application has been updated.');
          window.scrollTo(0, 0);
        });
      })
      .catch(function (error) {
        if (error.message !== 'Unauthorized') {
          showBox('formError', error.message || 'Could not save your application.');
          window.scrollTo(0, 0);
        }
      });
  });

  // Document upload
  document.getElementById('uploadForm').addEventListener('submit', function (e) {
    e.preventDefault();
    var fileInput = document.getElementById('docFile');
    var message = document.getElementById('uploadMessage');
    if (!fileInput.files.length) {
      message.textContent = 'Choose a file first.';
      return;
    }
    var formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('doc_type', document.getElementById('docType').value);
    message.textContent = 'Uploading...';
    portalFetch('/api/portal/documents', { method: 'POST', body: formData })
      .then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok) throw new Error(detailText(data, 'Upload failed'));
          message.textContent = 'Uploaded.';
          fileInput.value = '';
          loadDocuments();
        });
      })
      .catch(function (error) {
        message.textContent = error.message || 'Upload failed.';
      });
  });

  // Certification add
  document.getElementById('certForm').addEventListener('submit', function (e) {
    e.preventDefault();
    var message = document.getElementById('certMessage');
    var title = document.getElementById('certTitle').value.trim();
    if (!title) { message.textContent = 'Enter a title.'; return; }
    message.textContent = 'Saving...';
    portalFetch('/api/portal/certifications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cert_type: document.getElementById('certType').value,
        title: title,
        issued_on: document.getElementById('certIssued').value || null,
        expires_on: document.getElementById('certExpires').value || null,
        issuer: document.getElementById('certIssuer').value.trim() || null
      })
    })
      .then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok) throw new Error(detailText(data, 'Could not add the certification'));
          message.textContent = 'Added.';
          document.getElementById('certForm').reset();
          loadCertifications();
        });
      })
      .catch(function (error) {
        message.textContent = error.message || 'Could not add the certification.';
      });
  });

  // Logout
  document.getElementById('portalLogout').addEventListener('click', function (e) {
    e.preventDefault();
    fetch('/api/portal/logout', { method: 'POST', credentials: 'same-origin' })
      .catch(function () {})
      .then(function () { window.location.href = 'portal-login.html'; });
  });
})();
