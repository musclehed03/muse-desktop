const { app, BrowserWindow, dialog, Menu, session, shell } = require("electron");
const path = require("node:path");
const fs = require("node:fs");

const MUSE_URL = "https://muse.ai/";
const {
  isTrustedNavigation,
  isAllowedExternalUrl,
  isMuseOrigin,
  uniqueDownloadPath,
} = require("./utils.cjs");

function openExternalUrl(url) {
  if (isAllowedExternalUrl(url)) {
    void shell
      .openExternal(url)
      .catch(() => console.warn("Could not open external link"));
  }
}

function configureSession(ses) {
  // Electron uses this write-only permission for navigator.clipboard.writeText().
  // Do not grant clipboard-read: copying does not require reading the clipboard.
  const allowedPermissions = new Set([
    "notifications",
    "clipboard-sanitized-write",
  ]);
  ses.setPermissionCheckHandler(
    (_webContents, permission, requestingOrigin) => {
      return (
        allowedPermissions.has(permission) && isMuseOrigin(requestingOrigin)
      );
    },
  );

  ses.setPermissionRequestHandler(
    (_webContents, permission, callback, details) => {
      const requestingUrl = details?.requestingUrl ?? "";
      callback(
        allowedPermissions.has(permission) && isMuseOrigin(requestingUrl),
      );
    },
  );

  ses.on("will-download", (_event, item) => {
    let destination;
    const cleanup = () => {
      if (!destination) return;
      try {
        fs.rmSync(destination, { force: true });
      } catch {
        console.warn("Could not remove failed download destination");
      }
    };
    try {
      destination = uniqueDownloadPath(
        app.getPath("downloads"),
        item.getFilename(),
      );
      item.once("done", (_event, state) => {
        if (state !== "completed") cleanup();
      });
      item.setSavePath(destination);
    } catch {
      cleanup();
      item.cancel();
      console.warn("Could not reserve download destination");
    }
  });
}

// Let Chromium create the child so window.opener, postMessage, POST bodies,
// and window.open('') followed by an asynchronous location assignment survive.
// A manually-created window or an OS browser cannot preserve that relationship.
function configureWindowNavigation(window, isPopup = false) {
  const contents = window.webContents;
  contents.setWindowOpenHandler(({ url }) => {
    if (url !== "about:blank" && url !== "" && !isAllowedExternalUrl(url)) {
      return { action: "deny" };
    }
    return {
      action: "allow",
      overrideBrowserWindowOptions: {
        parent: window,
        width: 600,
        height: 760,
        show: true,
        webPreferences: {
          contextIsolation: true,
          nodeIntegration: false,
          nodeIntegrationInSubFrames: false,
          sandbox: true,
          webSecurity: true,
          partition: "persist:muse",
        },
      },
    };
  });
  contents.on("did-create-window", (child) => {
    configureWindowNavigation(child, true);
    // Do not leave authentication windows alive after their opener closes.
    const closeChild = () => {
      if (!child.isDestroyed()) child.destroy();
    };
    window.once("closed", closeChild);
    child.once("closed", () => window.removeListener("closed", closeChild));
  });

  const guardNavigation = (event, url, _isInPlace, isMainFrame = true) => {
    const allowed = isPopup
      ? url === "about:blank" || isAllowedExternalUrl(url)
      : isMainFrame
        ? isTrustedNavigation(url)
        : // Hosted apps can redirect to a separate content origin. Keep the
          // top-level allowlist without canceling safe iframe redirects.
          isAllowedExternalUrl(url);
    if (!allowed) {
      event.preventDefault();
      if (!isPopup && isMainFrame) openExternalUrl(url);
    }
  };
  contents.on("will-navigate", guardNavigation);
  contents.on("will-redirect", guardNavigation);
}

function createMuseWindow() {
  const window = new BrowserWindow({
    title: "Baxter - Our Deviant Muse",
    width: 1180,
    height: 820,
    minWidth: 760,
    minHeight: 540,
    backgroundColor: "#101117",
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      partition: "persist:muse",
    },
  });

  configureWindowNavigation(window);

  window.once("ready-to-show", () => {
    if (!window.isDestroyed()) window.show();
  });
  async function loadMuse() {
    while (!window.isDestroyed()) {
      try {
        await window.loadURL(MUSE_URL);
        return;
      } catch {
        if (window.isDestroyed()) return;
        // A failed first request may never emit ready-to-show.
        window.show();
        const { response } = await dialog.showMessageBox(window, {
          type: "error",
          title: "Could not load Baxter",
          message: "Muse could not be reached.",
          detail: "Check your internet connection, then try again.",
          buttons: ["Retry", "Close"],
          defaultId: 0,
          cancelId: 1,
        });
        if (window.isDestroyed()) return;
        if (response !== 0) {
          window.close();
          return;
        }
      }
    }
  }
  void loadMuse().catch(() =>
    console.warn("Could not show Muse load recovery"),
  );
  return window;
}

function showAbout() {
  void dialog.showMessageBox({
    type: "info",
    title: "About Baxter - Our Deviant Muse",
    message: `Baxter - Our Deviant Muse ${app.getVersion()}`,
    detail:
      "Unofficial desktop client for Muse (muse.ai).\n" +
      "Not affiliated with, endorsed by, or supported by Meta.\n" +
      "Built by Dollhouse Deviants.",
    buttons: ["Close"],
    defaultId: 0,
  });
}

function start() {
  // Align the running window with the installed Linux desktop entry so desktop
  // shells (GNOME, KDE) resolve the baxter-deviant-muse icon via WM_CLASS/app_id.
  if (process.platform === "linux") {
    app.setDesktopName("baxter-deviant-muse.desktop");
  }

  // Keep browser profile data in a predictable, product-specific directory.
  // NOTE: the directory stays "Muse" on purpose — renaming it would sign
  // the user out of muse.ai and clear the existing profile.
  app.setPath("userData", path.join(app.getPath("appData"), "Muse"));

  // Minimal application menu: About (with the unofficial-client notice) and
  // Quit. A standard menu bar only — no floating UI, nothing covering content.
  Menu.setApplicationMenu(
    Menu.buildFromTemplate([
      {
        label: "Baxter",
        submenu: [
          { label: "About Baxter - Our Deviant Muse", click: showAbout },
          { type: "separator" },
          { label: "Quit", accelerator: "CmdOrCtrl+Q", click: () => app.quit() },
        ],
      },
    ]),
  );

  app.whenReady().then(() => {
    configureSession(session.fromPartition("persist:muse"));
    createMuseWindow();
    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) createMuseWindow();
    });
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
  });
}

start();
