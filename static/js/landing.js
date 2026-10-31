/**
 * Interview.ai — Landing Page Interactions
 * Handles: navbar scroll, smooth anchors, reveal animations, journey animation, engine animation
 */
document.addEventListener('DOMContentLoaded', () => {
    const nav = document.getElementById('landingNav');
    const menu = document.getElementById('landingMenu');
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* ── Hide global floating theme toggle on landing ── */
    const floatingThemeToggle = document.getElementById('themeToggleFloating');
    if (floatingThemeToggle) floatingThemeToggle.classList.remove('is-visible');

    /* ── Navbar scroll state ── */
    const updateNav = () => nav?.classList.toggle('scrolled', window.scrollY > 24);
    updateNav();
    window.addEventListener('scroll', updateNav, { passive: true });

    /* ── Smooth scroll for anchor links ── */
    document.querySelectorAll('a[href^="#"]').forEach((link) => {
        link.addEventListener('click', (event) => {
            const selector = link.getAttribute('href');
            if (!selector || selector === '#') return;
            const target = document.querySelector(selector);
            if (!target) return;
            event.preventDefault();
            target.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
            if (menu?.classList.contains('show') && window.bootstrap?.Collapse) {
                window.bootstrap.Collapse.getOrCreateInstance(menu).hide();
            }
        });
    });

    /* ── Scroll Reveal (IntersectionObserver) ── */
    const revealElements = [...document.querySelectorAll('.reveal')];
    if (reducedMotion || !('IntersectionObserver' in window)) {
        revealElements.forEach((el) => el.classList.add('visible'));
    } else {
        const revealObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -36px' });
        revealElements.forEach((el) => revealObserver.observe(el));
    }

    /* ── Journey Track Animation ── */
    const journeyTrack = document.getElementById('journeyTrack');
    if (journeyTrack && !reducedMotion && 'IntersectionObserver' in window) {
        const journeyObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add('animated');
                observer.unobserve(entry.target);
            });
        }, { threshold: 0.25 });
        journeyObserver.observe(journeyTrack);
    } else if (journeyTrack) {
        journeyTrack.classList.add('animated');
    }

    /* ── AI Engine Diagram Animation ── */
    const engineDiagram = document.getElementById('engineDiagram');
    if (engineDiagram && !reducedMotion && 'IntersectionObserver' in window) {
        const engineObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add('animated');
                observer.unobserve(entry.target);
            });
        }, { threshold: 0.3 });
        engineObserver.observe(engineDiagram);
    } else if (engineDiagram) {
        engineDiagram.classList.add('animated');
    }

    /* ── Active nav link highlighting ── */
    const sectionLinks = [...document.querySelectorAll('.landing-nav-links a[href^="#"]')];
    const sections = sectionLinks.map((link) => document.querySelector(link.getAttribute('href'))).filter(Boolean);
    if ('IntersectionObserver' in window) {
        const sectionObserver = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                sectionLinks.forEach((link) =>
                    link.classList.toggle('active', link.getAttribute('href') === `#${entry.target.id}`)
                );
            });
        }, { rootMargin: '-35% 0px -55%', threshold: 0 });
        sections.forEach((section) => sectionObserver.observe(section));
    }
});
