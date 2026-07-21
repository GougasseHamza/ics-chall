"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const sqlite3 = require("/usr/src/app/FUXA/server/node_modules/sqlite3").verbose();
const bcrypt = require("/usr/src/app/FUXA/server/node_modules/bcryptjs");

const serverRoot = "/usr/src/app/FUXA/server";
const workDir = path.join(serverRoot, "_appdata");
const sourceDir = "/opt/rivermark-fuxa";

fs.mkdirSync(workDir, { recursive: true, mode: 0o700 });

fs.writeFileSync(
  path.join(workDir, "settings.js"),
  "const defaults = require('/usr/src/app/FUXA/server/settings.default.js');\n" +
  "module.exports = { ...defaults, allowedOrigins: ['http://*', 'https://*'], daqEnabled: false };\n",
  { mode: 0o600 }
);

const project = JSON.parse(fs.readFileSync(path.join(sourceDir, "project.json"), "utf8"));
project.hmi.views[0].svgcontent = fs.readFileSync(path.join(sourceDir, "line4.svg"), "utf8");
delete project.hmi.views[0].svgfile;

fs.writeFileSync(
  path.join(workDir, "mysettings.json"),
  JSON.stringify({
    hideEditorOnboarding: true,
    secureEnabled: true,
    secureOnlyEditor: true,
    secretCode: crypto.randomBytes(48).toString("hex"),
    tokenExpiresIn: "30m",
    broadcastAll: false,
    logFull: true,
    nodeRedEnabled: false,
    swaggerEnabled: false,
    logs: { retention: "none" }
  }),
  { mode: 0o600 }
);

function openDatabase(file) {
  return new sqlite3.Database(file);
}

function run(db, sql, params = []) {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function done(error) {
      if (error) reject(error);
      else resolve(this);
    });
  });
}

function exec(db, sql) {
  return new Promise((resolve, reject) => {
    db.exec(sql, error => error ? reject(error) : resolve());
  });
}

function close(db) {
  return new Promise((resolve, reject) => {
    db.close(error => error ? reject(error) : resolve());
  });
}

async function seedProject() {
  const db = openDatabase(path.join(workDir, "project.fuxap.db"));
  await exec(db,
    "CREATE TABLE IF NOT EXISTS general (name TEXT PRIMARY KEY, value TEXT);" +
    "CREATE TABLE IF NOT EXISTS views (name TEXT PRIMARY KEY, value TEXT);" +
    "CREATE TABLE IF NOT EXISTS devices (name TEXT PRIMARY KEY, value TEXT, connection TEXT, cntid TEXT, cntpwd TEXT);" +
    "CREATE TABLE IF NOT EXISTS devicesSecurity (name TEXT PRIMARY KEY, value TEXT);" +
    "CREATE TABLE IF NOT EXISTS texts (name TEXT PRIMARY KEY, value TEXT);" +
    "CREATE TABLE IF NOT EXISTS alarms (name TEXT PRIMARY KEY, value TEXT);" +
    "CREATE TABLE IF NOT EXISTS notifications (name TEXT PRIMARY KEY, value TEXT);" +
    "CREATE TABLE IF NOT EXISTS scripts (name TEXT PRIMARY KEY, value TEXT);" +
    "CREATE TABLE IF NOT EXISTS reports (name TEXT PRIMARY KEY, value TEXT);" +
    "CREATE TABLE IF NOT EXISTS locations (name TEXT PRIMARY KEY, value TEXT);"
  );

  const rows = [];
  for (const [key, value] of Object.entries(project)) {
    if (key === "devices") {
      for (const device of Object.values(value)) rows.push(["devices", device.id, device]);
    } else if (key === "hmi") {
      for (const view of value.views || []) rows.push(["views", view.id, view]);
      for (const [name, section] of Object.entries(value)) {
        if (name !== "views") rows.push(["general", name, section]);
      }
    } else if (key === "server") {
      rows.push(["devices", "server", value]);
    } else {
      rows.push(["general", key, value]);
    }
  }

  await exec(db, "BEGIN TRANSACTION");
  try {
    for (const [table, name, value] of rows) {
      await run(db, `INSERT OR REPLACE INTO ${table} (name, value) VALUES (?, ?)`, [name, JSON.stringify(value)]);
    }
    await exec(db, "COMMIT");
  } catch (error) {
    await exec(db, "ROLLBACK");
    throw error;
  }
  await close(db);
}

async function seedUsers() {
  const db = openDatabase(path.join(workDir, "users.fuxap.db"));
  await exec(db,
    "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, fullname TEXT, password TEXT, groups INTEGER, info TEXT);" +
    "CREATE TABLE IF NOT EXISTS roles (name TEXT PRIMARY KEY, value TEXT);"
  );
  const inaccessiblePassword = crypto.randomBytes(48).toString("base64url");
  await run(
    db,
    "INSERT OR REPLACE INTO users (username, fullname, password, groups, info) VALUES (?, ?, ?, ?, ?)",
    ["admin", "Disabled Runtime Editor", bcrypt.hashSync(inaccessiblePassword, 10), -1, JSON.stringify({ note: "Project changes are made from source and redeployed" })]
  );
  await close(db);
}

Promise.all([seedProject(), seedUsers()]).catch(error => {
  console.error("FUXA seed failed:", error.message);
  process.exit(1);
});
