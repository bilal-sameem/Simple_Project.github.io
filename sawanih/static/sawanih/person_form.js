// Client-side validation + dynamic rows for the person form (create and edit).
// The server repeats every check, so these are only for fast feedback.
(function () {
  const form = document.getElementById('personForm');
  const summary = document.getElementById('summary');
  const saveBtn = document.getElementById('saveBtn');
  const J = window.Jalali, jToday = J.today();            // solar-calendar helpers (jalali.js)
  const edit = form.dataset.mode === 'edit';            // edit => PUT, create => POST
  const previewBox = document.getElementById('preview');
  const originalPreview = previewBox.innerHTML;         // current photo (edit) or placeholder
  const MAX_EDU = 10, MAX_DOCS = 5, MAX_DOC_SIZE = 5 * 1024 * 1024;

  const MSG = {
    required: 'دا ډګر اړین دی.',
    id: 'د تذکرې شمېره سمه نه ده (۵ تر ۳۰ توري، شمېرې یا - /).',
    phone: 'د تلیفون شمېره سمه نه ده. بېلګه: 0700123456',
    email: 'بریښنالیک سم نه دی.',
    dob: 'د زېږېدو نېټه سمه نه ده.',
    year: 'د فراغت کال سم نه دی.',
    start: 'د پیل نېټه نشي کولی راتلونکې وي.',
    date: 'نېټه سمه نه ده. بېلګه: ۱۴۰۵/۰۸/۲۰ (کال/میاشت/ورځ)',
    letterDate: 'د مکتوب نېټه نشي کولی راتلونکې وي.',
    letterPair: 'د مکتوب شمېره او نېټه دواړه باید ډک شي.',
    photoType: 'عکس باید JPG، PNG یا WEBP وي.',
    photoSize: 'د عکس اندازه باید له 2 MB څخه کمه وي.',
    eduMax: 'تر ۱۰ درجو زیات نشي ثبتېدلی.',
    docId: 'د تذکرې سند اړین دی.',
    docOne: 'د دندې تجربې یا د زده کړې له سندونو لږ تر لږه یو اړین دی.',
    docType: 'فایل باید JPG، PNG، WEBP یا PDF وي.',
    docSize: 'د هر فایل اندازه باید له 5 MB څخه کمه وي.',
    docCount: 'تر ۵ فایلونو زیات نشي پورته کېدی.',
    network: 'له سرور سره اړیکه نشته. بیا هڅه وکړئ.',
    server: 'یوه ستونزه رامنځته شوه. بیا هڅه وکړئ.',
    summary: 'مهرباني وکړئ په سور رنګ نښه شوي ډګرونه سم کړئ.'
  };

  // Accept Pashto/Persian digits too: ۰-۹ and ٠-٩ -> 0-9
  const latin = s => s.replace(/[۰-۹]/g, d => d.charCodeAt(0) - 1776)
                      .replace(/[٠-٩]/g, d => d.charCodeAt(0) - 1632);
  const pdigits = n => String(n).replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]);

  // ---------- error display
  const wrap = name => form.querySelector('.field[data-name="' + name + '"]');
  function markError(w, text) {
    if (!w) return;
    w.classList.toggle('invalid', !!text);
    const e = w.querySelector('.err'); if (e) e.textContent = text || '';
    const i = w.querySelector('input[type=file],input:not([type=checkbox]):not([type=hidden]),textarea');
    if (i) i.setAttribute('aria-invalid', text ? 'true' : 'false');
  }
  const setError = (name, text) => markError(wrap(name), text);

  // ---------- documents
  function docTotal(name) {
    const kept = wrap(name).querySelectorAll('.doc-list input[type=checkbox]:not(:checked)').length;
    return kept + form.elements[name].files.length;
  }
  function docProblem(name) {
    if (docTotal(name) > MAX_DOCS) return MSG.docCount;
    for (const f of form.elements[name].files) {
      if (!/^(image\/(jpeg|png|webp)|application\/pdf)$/.test(f.type)) return MSG.docType;
      if (f.size > MAX_DOC_SIZE) return MSG.docSize;
    }
    return false;
  }

  const rules = {
    full_name: v => !v.trim() && MSG.required,
    father_name: v => !v.trim() && MSG.required,
    date_of_birth: v => { if (!v.trim()) return MSG.required;
                          const d = J.parse(v);
                          if (!d) return MSG.date;
                          return (J.key(d) > J.key(jToday) || d.y < 1279) && MSG.dob; },
    id_number: v => !v.trim() ? MSG.required : !/^[0-9A-Za-z\/\-]{5,30}$/.test(latin(v.trim())) && MSG.id,
    phone: v => { if (!v.trim()) return MSG.required;
                  return !/^\+?\d{9,15}$/.test(latin(v).replace(/[\s\-()]/g, '')) && MSG.phone; },
    email: v => v.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim()) && MSG.email,
    start_date: v => { if (!v.trim()) return false;
                       const d = J.parse(v);
                       return !d ? MSG.date : J.key(d) > J.key(jToday) && MSG.start; },
    hire_letter_number: v => !v.trim() && form.elements.hire_letter_date.value.trim() && MSG.letterPair,
    hire_letter_date: v => { const num = form.elements.hire_letter_number.value.trim();
                             if (!v.trim()) return num && MSG.letterPair;
                             const d = J.parse(v);
                             return !d ? MSG.date : J.key(d) > J.key(jToday) && MSG.letterDate; },
    photo: () => { const f = document.getElementById('photo').files[0];
                   if (!f) return false;
                   if (!/^image\/(jpeg|png|webp)$/.test(f.type)) return MSG.photoType;
                   return f.size > 2 * 1024 * 1024 && MSG.photoSize; },
    id_card_files: () => docProblem('id_card_files') || (docTotal('id_card_files') < 1 && MSG.docId),
    experience_files: () => docProblem('experience_files'),
    education_files: () => docProblem('education_files'),
    docs_one_of: () => docTotal('experience_files') + docTotal('education_files') < 1 && MSG.docOne
  };

  function check(name) {
    const el = form.elements[name];
    const msg = rules[name](el ? (el.value || '') : '');
    setError(name, msg || '');
    return !msg;
  }
  const DOC_NAMES = ['id_card_files', 'experience_files', 'education_files'];
  const checkDocs = () => { DOC_NAMES.forEach(check); check('docs_one_of'); };

  // Validate a field when the user leaves it; clear its error while typing.
  Object.keys(rules).forEach(name => {
    const el = form.elements[name];
    if (!el || DOC_NAMES.includes(name) || name === 'photo') return;
    el.addEventListener('blur', () => check(name));
    el.addEventListener('input', () => { if (wrap(name).classList.contains('invalid')) check(name); });
  });
  ['hire_letter_number', 'hire_letter_date'].forEach(n =>
    form.elements[n].addEventListener('blur', () => { check('hire_letter_number'); check('hire_letter_date'); }));
  DOC_NAMES.forEach(n => form.elements[n].addEventListener('change', checkDocs));
  form.addEventListener('change', e => { if (e.target.name === 'remove_docs') checkDocs(); });

  // ---------- photo preview
  document.getElementById('photo').addEventListener('change', e => {
    const f = e.target.files[0];
    previewBox.innerHTML = originalPreview;
    if (f && /^image\//.test(f.type)) {
      const img = new Image(); img.alt = '';
      img.src = URL.createObjectURL(f); previewBox.textContent = ''; previewBox.append(img);
    }
    check('photo');
  });

  // ---------- education rows (add / remove many)
  const eduList = document.getElementById('eduList');
  const eduTpl = document.getElementById('eduTemplate');
  const rows = () => [...eduList.querySelectorAll('.edu-row')];

  function renumber() {
    rows().forEach((row, i) => { row.querySelector('.edu-title').textContent = 'درجه ' + pdigits(i + 1); });
    document.getElementById('addEdu').disabled = rows().length >= MAX_EDU;
  }
  document.getElementById('addEdu').addEventListener('click', () => {
    if (rows().length >= MAX_EDU) { setError('edu_list', MSG.eduMax); return; }
    setError('edu_list', '');
    eduList.append(eduTpl.content.cloneNode(true));
    renumber();
    const last = rows().pop(); last.querySelector('input[type=text]').focus();
  });
  eduList.addEventListener('click', e => {
    const btn = e.target.closest('.edu-remove'); if (!btn) return;
    const row = btn.closest('.edu-row');
    if (rows().length === 1) {                       // last row: just clear it
      row.querySelectorAll('input').forEach(i => { i.value = ''; });
      row.querySelectorAll('.field').forEach(w => markError(w, ''));
    } else { row.remove(); }
    renumber();
  });

  function eduRowCheck(row) {
    const v = n => row.querySelector('[name="' + n + '"]').value.trim();
    const degree = v('edu_degree'), inst = v('edu_institution'), year = latin(v('edu_year'));
    const used = degree || inst || year;
    const set = (n, m) => markError(row.querySelector('.field[data-name="' + n + '"]'), m);
    set('edu_degree', used && !degree ? MSG.required : '');
    set('edu_institution', used && !inst ? MSG.required : '');
    const yearBad = year && !(/^\d{4}$/.test(year) && +year >= 1300 && +year <= jToday.y + 6);
    set('edu_year', yearBad ? MSG.year : '');
    return !(used && (!degree || !inst)) && !yearBad;
  }

  // ---------- submit
  const showSummary = on => { summary.textContent = on ? MSG.summary : ''; summary.classList.toggle('show', on); };
  function focusFirstError() {
    const inv = form.querySelector('.field.invalid'); if (!inv) return;
    const t = inv.querySelector('input:not([type=checkbox]):not([type=hidden]),textarea');
    if (t) t.focus(); else inv.scrollIntoView({ block: 'center' });
  }

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const badFields = Object.keys(rules).filter(n => !check(n));
    const badRows = rows().map(eduRowCheck).filter(ok => !ok);
    const bad = badFields.length + badRows.length > 0;
    showSummary(bad);
    if (bad) { focusFirstError(); return; }

    saveBtn.disabled = true;
    try {
      const headers = { 'X-Requested-With': 'XMLHttpRequest' };
      if (edit) headers['X-CSRFToken'] = form.elements.csrfmiddlewaretoken.value;   // PUT: token goes in the header
      const r = await fetch(form.action, { method: edit ? 'PUT' : 'POST', body: new FormData(form), headers });
      if (r.status === (edit ? 200 : 201)) { window.location.href = form.dataset.redirect; return; }  // toast shows there
      if (r.status === 400) {
        const { errors } = await r.json();
        Object.entries(errors).forEach(([name, text]) => {
          const m = name.match(/^edu_(\d+)_(degree|institution|year)$/);   // e.g. edu_1_degree = 2nd education row
          if (m) { const row = rows()[+m[1]]; if (row) markError(row.querySelector('.field[data-name="edu_' + m[2] + '"]'), text); }
          else setError(name, text);
        });
        showSummary(true); focusFirstError();
      } else { summary.textContent = MSG.server; summary.classList.add('show'); }
    } catch (_) { summary.textContent = MSG.network; summary.classList.add('show'); }
    saveBtn.disabled = false;
  });

  renumber();
})();
