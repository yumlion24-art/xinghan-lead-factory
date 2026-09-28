import { execFileSync } from "node:child_process";

export default function globalTeardown() {
  const script = [
    "$connections = Get-NetTCPConnection -LocalPort 8010,3010 -State Listen -ErrorAction SilentlyContinue;",
    "$connections | Select-Object -ExpandProperty OwningProcess -Unique |",
    "ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }",
  ].join(" ");
  execFileSync("powershell", ["-NoProfile", "-Command", script], { stdio: "ignore" });
}
