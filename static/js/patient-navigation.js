(() => {
  const nav = document.querySelector('.pw-navbar');
  if (!nav) return;
  const button = nav.querySelector('.pw-menu-toggle');
  const links = nav.querySelector('.pw-navigation');
  const menus = [...nav.querySelectorAll('.pw-dropdown')];
  nav.classList.add('has-js'); button.hidden = false;
  const closeMenus = except => menus.forEach(menu => { if (menu !== except) menu.open = false; });
  const closeNav = () => { links.classList.remove('is-open'); button.setAttribute('aria-expanded','false'); closeMenus(); };
  button.addEventListener('click', () => {
    const open = button.getAttribute('aria-expanded') !== 'true';
    links.classList.toggle('is-open', open); button.setAttribute('aria-expanded', String(open));
    if (!open) closeMenus();
  });
  menus.forEach(menu => menu.addEventListener('toggle', () => { if (menu.open) closeMenus(menu); }));
  document.addEventListener('click', event => { if (!nav.contains(event.target)) closeNav(); });
  nav.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const opened = menus.find(menu => menu.open && menu.contains(document.activeElement));
    if (opened) { opened.open = false; opened.querySelector('summary').focus(); }
    else if (button.getAttribute('aria-expanded') === 'true') { closeNav(); button.focus(); }
  });
  matchMedia('(min-width:961px)').addEventListener('change', closeNav);
})();
