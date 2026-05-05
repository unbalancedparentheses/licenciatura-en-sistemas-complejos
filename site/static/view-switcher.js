(function() {
  const LANGS = ['es', 'en'];
  const DEFAULT_LANG = 'es';

  const I18N = {
    es: { view: 'Vista', full: 'Completa', students: 'Estudiantes', faculty: 'Profesores', authorities: 'Autoridades' },
    en: { view: 'View', full: 'Full', students: 'Students', faculty: 'Faculty', authorities: 'Authorities' }
  };

  function applyLang(lang) {
    document.body.setAttribute('data-lang', lang);
    document.documentElement.setAttribute('lang', lang);
    document.querySelectorAll('.lang-switcher button').forEach(b => {
      b.classList.toggle('active', b.dataset.lang === lang);
    });
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.dataset.i18n;
      if (I18N[lang] && I18N[lang][key]) el.textContent = I18N[lang][key];
    });
    try { localStorage.setItem('lscLang', lang); } catch (e) {}
  }

  // Audience filtering on the full page (`/`). On audience-specific pages
  // content is already filtered server-side, so this loop is a no-op when
  // body[data-audience] is set.
  function applyView(view) {
    if (document.body.dataset.audience) return;
    const breaks = Array.from(document.querySelectorAll('.page-break'));
    const VIEWS = ['students', 'faculty', 'authorities'];
    for (let i = 0; i < breaks.length; i++) {
      const start = breaks[i];
      const end = breaks[i + 1] || null;
      const views = (start.dataset.views || VIEWS.join(',')).split(',').map(s => s.trim());
      const visible = view === 'full' || views.includes(view);
      let el = start;
      while (el && el !== end) {
        el.style.display = visible ? '' : 'none';
        el = el.nextElementSibling;
      }
    }
  }

  document.querySelectorAll('.lang-switcher button').forEach(b => {
    b.addEventListener('click', () => applyLang(b.dataset.lang));
  });

  let initialLang = DEFAULT_LANG;
  try {
    const sl = localStorage.getItem('lscLang');
    if (sl && LANGS.includes(sl)) initialLang = sl;
    // Allow ?lang=en URL parameter to override (used by PDF generation)
    const params = new URLSearchParams(window.location.search);
    const qpLang = params.get('lang');
    if (qpLang && LANGS.includes(qpLang)) initialLang = qpLang;
  } catch (e) {}
  applyLang(initialLang);

  // On the full page, default to showing everything ("full" view).
  applyView('full');
})();
