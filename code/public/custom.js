/**
 * Braze SDK Demo — Chainlit UI overrides
 *
 * Injects styles via JS to guarantee they load after all other CSS
 * and bypass any browser caching of the external stylesheet.
 */
(function () {
  const css = `
    /* Welcome screen: Gemini-style layout */
    #welcome-screen {
      display: flex !important;
      flex-direction: column !important;
      justify-content: flex-end !important;
      align-items: center !important;
      padding-bottom: 16px !important;
    }

    /* Hide only the large centered logo, not the composer */
    #welcome-screen > :first-child {
      display: none !important;
    }

    /* Title line — text only, logo injected via JS */
    #welcome-screen::before {
      content: "Braze SDK Landing Page Generator";
      display: none !important;
    }

    /* JS-injected header row */
    .braze-header-row {
      display: flex !important;
      align-items: center;
      gap: 14px;
      width: 100%;
      max-width: 48rem;
      margin-bottom: 8px;
      box-sizing: border-box;
    }

    .braze-header-row img {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
      flex-shrink: 0;
    }

    .braze-header-row span {
      font-size: 18px;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.55);
      line-height: 1.3;
    }

    /* Subtitle */
    #welcome-screen::after {
      content: "Describe the landing page you want to build.";
      display: block !important;
      width: 100%;
      max-width: 48rem;
      text-align: left;
      padding-left: 62px;
      font-size: 28px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.9);
      line-height: 1.3;
      margin-bottom: 20px;
      box-sizing: border-box;
    }

    /* Logo in messages/steps */
    img[alt="logo"] {
      border-radius: 16px !important;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5) !important;
    }

    /* Step styling */
    .step .step-output {
      border-left: 3px solid #00bfa5;
    }

    /* Message links */
    .message-content a {
      color: #00bfa5;
    }

    /* File download */
    .inline-file {
      border: 1px solid #00bfa5;
      border-radius: 8px;
    }
  `;

  const style = document.createElement('style');
  style.setAttribute('data-braze-overrides', 'true');
  style.textContent = css;
  document.head.appendChild(style);

  // Inject the logo + title row into the welcome screen once it renders
  const observer = new MutationObserver(() => {
    const ws = document.getElementById('welcome-screen');
    if (ws && !ws.querySelector('.braze-header-row')) {
      const row = document.createElement('div');
      row.className = 'braze-header-row';
      row.innerHTML =
        '<img src="/public/braze-logo.webp" alt="Braze" />' +
        '<span>Braze SDK Landing Page Generator</span>';
      ws.prepend(row);
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
