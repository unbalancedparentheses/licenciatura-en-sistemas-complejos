(function() {
  const VIEWS = ['students', 'faculty', 'authorities'];
  const LANGS = ['es', 'en'];
  const DEFAULT_VIEW = 'authorities';
  const DEFAULT_LANG = 'es';

  const I18N = {
    es: { view: 'Vista', students: 'Estudiantes', faculty: 'Profesores', authorities: 'Autoridades' },
    en: { view: 'View', students: 'Students', faculty: 'Faculty', authorities: 'Authorities' }
  };

  function applyView(view) {
    const breaks = Array.from(document.querySelectorAll('.page-break'));
    for (let i = 0; i < breaks.length; i++) {
      const start = breaks[i];
      const end = breaks[i + 1] || null;
      const views = (start.dataset.views || VIEWS.join(',')).split(',').map(s => s.trim());
      const visible = views.includes(view);
      let el = start;
      while (el && el !== end) {
        el.style.display = visible ? '' : 'none';
        el = el.nextElementSibling;
      }
    }
    document.querySelectorAll('.view-switcher button').forEach(b => {
      b.classList.toggle('active', b.dataset.view === view);
    });
    try { localStorage.setItem('lscView', view); } catch (e) {}
  }

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

  document.querySelectorAll('.view-switcher button').forEach(b => {
    b.addEventListener('click', () => applyView(b.dataset.view));
  });
  document.querySelectorAll('.lang-switcher button').forEach(b => {
    b.addEventListener('click', () => applyLang(b.dataset.lang));
  });

  let initialView = DEFAULT_VIEW;
  let initialLang = DEFAULT_LANG;
  try {
    const sv = localStorage.getItem('lscView');
    if (sv && VIEWS.includes(sv)) initialView = sv;
    const sl = localStorage.getItem('lscLang');
    if (sl && LANGS.includes(sl)) initialLang = sl;
  } catch (e) {}
  applyLang(initialLang);
  applyView(initialView);
})();
