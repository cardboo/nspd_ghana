/**
 * NSPD Ghana — submission detail page.
 *
 * Replaces view-submission.php; data comes from GET /api/applications/{id}.
 * v2 adds the review status panel (approve/reject), internal reviewer
 * comments, and document upload/download.
 */
(function () {
  var params = new URLSearchParams(window.location.search);
  var id = parseInt(params.get('id') || '0', 10);

  // Invalid ID -> back to the list, same as the PHP page
  if (!id || id <= 0) {
    window.location.href = 'submissions.html';
    return;
  }

  var currentUser = null;

  function isReviewer() {
    return currentUser && (currentUser.role === 'Administrator' || currentUser.role === 'Reviewer');
  }

  function yesNoBadge(value) {
    if (value === 'Yes') {
      return '<span class="badge badge-success-lg">&#10003; Yes</span>';
    }
    return '<span class="badge badge-danger-lg">&#10007; No</span>';
  }

  function detailItem(label, valueHtml, extraClass) {
    return '<div class="detail-item">' +
      '<div class="detail-label">' + esc(label) + '</div>' +
      '<div class="detail-value' + (extraClass ? ' ' + extraClass : '') + '">' + valueHtml + '</div>' +
    '</div>';
  }

  function renderStatus(app) {
    var html = '';
    html += detailItem('Current Status', statusBadge(app.status));
    if (app.reviewer_name) {
      html += detailItem('Reviewed By', esc(app.reviewer_name));
    }
    if (app.reviewed_at) {
      html += detailItem('Reviewed At', esc(fmtDateLong(app.reviewed_at)));
    }
    document.getElementById('statusGrid').innerHTML = html;
  }

  function renderDetails(app) {
    renderStatus(app);

    // Personal Information
    var personal = '';
    personal += detailItem('Surname', esc(app.surname));
    personal += detailItem('First Name', esc(app.first_name));
    if (app.other_names) {
      personal += detailItem('Other Names', esc(app.other_names));
    }
    personal += detailItem('Telephone', esc(app.telephone));
    if (app.ghana_card_number) {
      personal += detailItem('Ghana Card', esc(app.ghana_card_number));
    }
    personal += detailItem('Email', esc(app.email));
    personal += detailItem('Submission Date', esc(fmtDateLong(app.submitted_at)));
    document.getElementById('personalGrid').innerHTML = personal;

    // Position & Qualifications
    var qualifications = '';
    qualifications += detailItem('Position/Rank', esc(app.position_rank), 'text-primary');
    qualifications += detailItem('Short Courses (RMU)', yesNoBadge(app.short_courses_rmu));
    qualifications += detailItem('Familiarisation ISPS/GMA', yesNoBadge(app.familiarisation_isps_gma));
    qualifications += detailItem('Attachment', yesNoBadge(app.attachment || 'No'));
    qualifications += detailItem('Medicals', yesNoBadge(app.medicals || 'No'));
    document.getElementById('qualificationsGrid').innerHTML = qualifications;

    // Sea Experience
    var totalYears = parseFloat(app.total_sea_experience_years || 0);
    var sea = '';
    sea += detailItem('Has Sea Experience', yesNoBadge(app.sea_experience || 'No'));
    sea += detailItem('Total Sea Experience',
      esc(fmtYears(app.total_sea_experience_years)) + ' Years',
      'detail-value-large text-primary');
    sea += detailItem('Sea Experience in Months',
      Math.round(totalYears * 12) + ' Months',
      'detail-value-large text-accent');
    if (app.last_ship_type) {
      sea += detailItem('Last Ship Type', esc(app.last_ship_type));
    }
    document.getElementById('seaGrid').innerHTML = sea;
  }

  // ── Review status actions ──

  function wireStatusActions() {
    if (!isReviewer()) return;
    var container = document.getElementById('statusActions');
    container.style.display = '';
    container.querySelectorAll('button[data-status]').forEach(function (button) {
      button.addEventListener('click', function (e) {
        e.preventDefault();
        var newStatus = button.getAttribute('data-status');
        var message = document.getElementById('statusMessage');
        message.textContent = 'Saving...';
        API.fetch('/api/applications/' + id + '/status', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: newStatus })
        })
          .then(function (response) {
            if (!response.ok) throw new Error('Status update failed');
            return response.json();
          })
          .then(function (data) {
            renderStatus(data.application);
            loadHistory();
            var note = data.notification || {};
            if (note.status === 'sent') {
              message.textContent = 'Saved. Applicant notified at ' + note.recipient + '.';
            } else if (note.status === 'skipped') {
              message.textContent = 'Saved. Email skipped (no email service configured).';
            } else if (note.status === 'failed') {
              message.textContent = 'Saved, but the notification email failed.';
            } else {
              message.textContent = 'Saved.';
            }
          })
          .catch(function () {
            message.textContent = 'Could not update the status.';
          });
      });
    });
  }

  // ── Status history ──

  function loadHistory() {
    API.json('/api/applications/' + id + '/history')
      .then(function (data) {
        document.getElementById('historyContainer').innerHTML = timelineHTML(data.history);
      })
      .catch(function (error) { console.error('Failed to load history:', error); });
  }

  // ── Certifications ──

  function loadCertifications() {
    API.json('/api/applications/' + id + '/certifications')
      .then(function (data) {
        var certs = data.certifications || [];
        var container = document.getElementById('certificationsList');
        if (!certs.length) {
          container.innerHTML = '<span class="muted">No certifications recorded yet.</span>';
          return;
        }
        container.innerHTML = '<div class="table-container"><table><thead><tr>' +
          '<th>Type</th><th>Title</th><th>Issued</th><th>Expires</th><th>Status</th><th>Issuer</th><th></th>' +
          '</tr></thead><tbody>' +
          certs.map(function (cert) {
            return '<tr>' +
              '<td class="text-sm">' + esc(cert.cert_type) + '</td>' +
              '<td>' + esc(cert.title) + '</td>' +
              '<td class="text-sm">' + (cert.issued_on ? fmtDateShort(cert.issued_on) : '—') + '</td>' +
              '<td class="text-sm">' + (cert.expires_on ? fmtDateShort(cert.expires_on) : '—') + '</td>' +
              '<td>' + certBadge(cert.status) + '</td>' +
              '<td class="text-sm">' + esc(cert.issuer || '') + '</td>' +
              '<td>' + (isReviewer()
                ? '<button class="text-danger-action" data-cert="' + cert.id + '">Delete</button>'
                : '') + '</td>' +
            '</tr>';
          }).join('') + '</tbody></table></div>';

        container.querySelectorAll('button[data-cert]').forEach(function (button) {
          button.addEventListener('click', function () {
            if (!window.confirm('Delete this certification record?')) return;
            API.fetch('/api/applications/certifications/' + button.getAttribute('data-cert'), { method: 'DELETE' })
              .then(function () { loadCertifications(); })
              .catch(function (error) { console.error(error); });
          });
        });
      })
      .catch(function (error) { console.error('Failed to load certifications:', error); });
  }

  function wireCertForm() {
    if (!isReviewer()) return;
    var form = document.getElementById('certForm');
    form.style.display = '';
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var message = document.getElementById('certMessage');
      var title = document.getElementById('certTitle').value.trim();
      if (!title) { message.textContent = 'Enter a title.'; return; }
      message.textContent = 'Saving...';
      API.fetch('/api/applications/' + id + '/certifications', {
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
            if (!response.ok) {
              var detail = data.detail;
              if (Array.isArray(detail)) detail = detail.map(function (d) { return d.msg; }).join('; ');
              throw new Error(detail || 'Could not add the certification');
            }
            message.textContent = 'Added.';
            form.reset();
            loadCertifications();
          });
        })
        .catch(function (error) {
          message.textContent = error.message || 'Could not add the certification.';
        });
    });
  }

  // ── Documents ──

  function fmtSize(bytes) {
    if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + ' MB';
    if (bytes >= 1024) return Math.round(bytes / 1024) + ' KB';
    return bytes + ' B';
  }

  function loadDocuments() {
    API.json('/api/applications/' + id + '/documents')
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
            return '<tr>' +
              '<td>' + esc(doc.doc_type) + '</td>' +
              '<td><a class="link-primary" target="_blank" href="/api/documents/' + doc.id + '/download">' +
                esc(doc.original_name) + '</a></td>' +
              '<td class="text-sm">' + fmtSize(doc.size_bytes) + '</td>' +
              '<td class="text-sm">' + fmtDateShort(doc.uploaded_at) + '</td>' +
              '<td>' + (isReviewer()
                ? '<button class="text-danger-action" data-doc="' + doc.id + '">Delete</button>'
                : '') + '</td>' +
            '</tr>';
          }).join('') + '</tbody></table></div>';

        container.querySelectorAll('button[data-doc]').forEach(function (button) {
          button.addEventListener('click', function () {
            if (!window.confirm('Delete this document?')) return;
            API.fetch('/api/documents/' + button.getAttribute('data-doc'), { method: 'DELETE' })
              .then(function () { loadDocuments(); })
              .catch(function (error) { console.error('Delete failed:', error); });
          });
        });
      })
      .catch(function (error) {
        console.error('Failed to load documents:', error);
      });
  }

  function wireUploadForm() {
    if (!isReviewer()) return;
    var form = document.getElementById('uploadForm');
    form.style.display = '';
    form.addEventListener('submit', function (e) {
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
      API.fetch('/api/applications/' + id + '/documents', { method: 'POST', body: formData })
        .then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok) throw new Error(data.detail || 'Upload failed');
            message.textContent = 'Uploaded.';
            fileInput.value = '';
            loadDocuments();
          });
        })
        .catch(function (error) {
          message.textContent = error.message || 'Upload failed.';
        });
    });
  }

  // ── Comments ──

  function loadComments() {
    API.json('/api/applications/' + id + '/comments')
      .then(function (data) {
        var comments = data.comments || [];
        var container = document.getElementById('commentsList');
        if (!comments.length) {
          container.innerHTML = '<span class="muted">No comments yet.</span>';
          return;
        }
        container.innerHTML = comments.map(function (c) {
          var canDelete = currentUser &&
            (c.user_id === currentUser.id || currentUser.role === 'Administrator');
          return '<div class="comment-item">' +
            '<div class="comment-meta"><strong>' + esc(c.username) + '</strong> — ' +
              esc(fmtDateLong(c.created_at)) +
              (canDelete
                ? ' &nbsp;<button class="text-danger-action" data-comment="' + c.id + '">Delete</button>'
                : '') +
            '</div>' +
            '<div class="comment-text">' + esc(c.comment) + '</div>' +
          '</div>';
        }).join('');

        container.querySelectorAll('button[data-comment]').forEach(function (button) {
          button.addEventListener('click', function () {
            if (!window.confirm('Delete this comment?')) return;
            API.fetch('/api/applications/comments/' + button.getAttribute('data-comment'), { method: 'DELETE' })
              .then(function () { loadComments(); })
              .catch(function (error) { console.error('Delete failed:', error); });
          });
        });
      })
      .catch(function (error) {
        console.error('Failed to load comments:', error);
      });
  }

  function wireCommentForm() {
    if (!isReviewer()) return;
    var form = document.getElementById('commentForm');
    form.style.display = '';
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var textarea = document.getElementById('commentText');
      var text = textarea.value.trim();
      if (!text) return;
      API.fetch('/api/applications/' + id + '/comments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment: text })
      })
        .then(function (response) {
          if (!response.ok) throw new Error('Comment failed');
          textarea.value = '';
          loadComments();
        })
        .catch(function (error) { console.error(error); });
    });
  }

  // ── Page bootstrap ──

  initLayout('', 'Submission Details').then(function (user) {
    if (!user) return;
    currentUser = user;

    API.fetch('/api/applications/' + id)
      .then(function (response) {
        if (!response.ok) {
          // Not found -> back to the list, same as the PHP page
          window.location.href = 'submissions.html';
          throw new Error('Not found');
        }
        return response.json();
      })
      .then(function (data) {
        // Export PDF is restricted to Administrator/Reviewer
        if (isReviewer()) {
          var pdfLink = document.getElementById('exportPdfLink');
          pdfLink.href = '/api/exports/pdf/' + id;
          pdfLink.style.display = '';
        }
        renderDetails(data.application);
        wireStatusActions();
        wireUploadForm();
        wireCommentForm();
        wireCertForm();
        loadDocuments();
        loadComments();
        loadCertifications();
        loadHistory();
      })
      .catch(function (error) {
        console.error('Failed to load submission:', error);
      });
  });
})();
