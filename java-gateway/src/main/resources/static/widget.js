/**
 * Rockey embeddable chat widget (constitution I.4b — Web Widget channel).
 *
 * Usage (embedded on a tenant's site):
 *   <script src="https://<gateway-host>/widget.js"
 *           data-tenant="vinted"
 *           data-position="bottom-right"></script>
 *
 * Talks to the Java Gateway's REST fallback endpoint (POST /api/v1/chat) so the
 * widget has no external dependency (no SockJS/STOMP client library to load).
 * The session id is kept in sessionStorage so a page reload within the same
 * browser tab resumes the conversation (spec US7 FR: session resumes on the
 * same channel); a new tab/session starts fresh.
 */
(function () {
  "use strict";

  var currentScript = document.currentScript;
  var tenantId = currentScript.getAttribute("data-tenant");
  var position = currentScript.getAttribute("data-position") || "bottom-right";
  var gatewayOrigin = new URL(currentScript.src).origin;
  var storageKey = "rockey-session-" + tenantId;

  if (!tenantId) {
    console.error("[rockey-widget] missing required data-tenant attribute");
    return;
  }

  var POSITION_STYLES = {
    "bottom-right": "bottom: 20px; right: 20px;",
    "bottom-left": "bottom: 20px; left: 20px;",
    "top-right": "top: 20px; right: 20px;",
    "top-left": "top: 20px; left: 20px;",
  };

  function injectStyles() {
    var style = document.createElement("style");
    style.textContent =
      "#rockey-widget-launcher { position: fixed; " +
      (POSITION_STYLES[position] || POSITION_STYLES["bottom-right"]) +
      " width: 56px; height: 56px; border-radius: 50%; background: #1a1a2e; color: #fff;" +
      " border: none; cursor: pointer; font-size: 24px; z-index: 2147483000; box-shadow: 0 2px 8px rgba(0,0,0,.3); }" +
      "#rockey-widget-panel { position: fixed; " +
      (POSITION_STYLES[position] || POSITION_STYLES["bottom-right"]) +
      " margin-bottom: 76px; width: 320px; max-height: 440px; display: none; flex-direction: column;" +
      " background: #fff; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,.25); overflow: hidden;" +
      " font-family: -apple-system, BlinkMacSystemFont, sans-serif; z-index: 2147483000; }" +
      "#rockey-widget-panel.open { display: flex; }" +
      "#rockey-widget-messages { flex: 1; overflow-y: auto; padding: 12px; font-size: 14px; }" +
      "#rockey-widget-messages .msg { margin-bottom: 8px; padding: 8px 10px; border-radius: 8px; max-width: 85%; }" +
      "#rockey-widget-messages .msg.user { background: #1a1a2e; color: #fff; margin-left: auto; }" +
      "#rockey-widget-messages .msg.agent { background: #f0f0f3; color: #1a1a2e; }" +
      "#rockey-widget-input-row { display: flex; border-top: 1px solid #eee; }" +
      "#rockey-widget-input { flex: 1; border: none; padding: 10px; font-size: 14px; outline: none; }" +
      "#rockey-widget-send { border: none; background: #1a1a2e; color: #fff; padding: 0 16px; cursor: pointer; }";
    document.head.appendChild(style);
  }

  function buildDom() {
    var launcher = document.createElement("button");
    launcher.id = "rockey-widget-launcher";
    launcher.setAttribute("aria-label", "Ouvrir le chat du service client");
    launcher.textContent = "💬";

    var panel = document.createElement("div");
    panel.id = "rockey-widget-panel";
    panel.innerHTML =
      '<div id="rockey-widget-messages"></div>' +
      '<div id="rockey-widget-input-row">' +
      '<input id="rockey-widget-input" type="text" placeholder="Écrivez un message..." />' +
      '<button id="rockey-widget-send">Envoyer</button>' +
      "</div>";

    document.body.appendChild(panel);
    document.body.appendChild(launcher);

    launcher.addEventListener("click", function () {
      panel.classList.toggle("open");
    });

    return panel;
  }

  function appendMessage(container, text, role) {
    var el = document.createElement("div");
    el.className = "msg " + role;
    el.textContent = text;
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
  }

  function sendMessage(panel, text) {
    var messages = panel.querySelector("#rockey-widget-messages");
    appendMessage(messages, text, "user");

    var sessionId = sessionStorage.getItem(storageKey);

    fetch(gatewayOrigin + "/api/v1/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Tenant-ID": tenantId,
      },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("request failed: " + response.status);
        }
        return response.json();
      })
      .then(function (data) {
        if (data.session_id) {
          sessionStorage.setItem(storageKey, data.session_id);
        }
        appendMessage(messages, data.reply, "agent");
      })
      .catch(function () {
        appendMessage(
          messages,
          "Désolée, une erreur est survenue. Merci de réessayer ou de nous contacter par email.",
          "agent"
        );
      });
  }

  function init() {
    injectStyles();
    var panel = buildDom();
    var input = panel.querySelector("#rockey-widget-input");
    var sendButton = panel.querySelector("#rockey-widget-send");

    function submit() {
      var text = input.value.trim();
      if (!text) {
        return;
      }
      input.value = "";
      sendMessage(panel, text);
    }

    sendButton.addEventListener("click", submit);
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        submit();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
